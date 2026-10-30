//! Bounded per-client admission for the public OAuth start route.
//!
//! Cloudflare's zone rule is the primary start limit; this in-process token bucket is defense in depth for the
//! broker's shared authorization capacity and its Neuron calls. Only a peer inside an explicitly trusted proxy network
//! (the tunnel connector's two-member edge network) may name the client, with exactly one `CF-Connecting-IP`; every
//! other peer is keyed by its own socket address, so no header lets a direct peer choose its key.

use std::{
    collections::{BTreeMap, HashMap},
    net::{IpAddr, Ipv4Addr, Ipv6Addr},
    sync::{Arc, Mutex, PoisonError},
};

use http::HeaderMap;

use crate::clock::Clock;

/// The environment variable naming the trusted proxy networks.
pub const TRUSTED_PROXY_CIDRS: &str = "SHIMPZ_STORE_TRUSTED_PROXY_CIDRS";
/// The same budget as Cloudflare's zone rule: ten starts per client per minute.
pub const START_CAPACITY: f64 = 10.0;
/// The period in which a client's whole budget refills, in seconds.
pub const START_PERIOD: f64 = 60.0;
/// The most clients whose buckets are kept.
pub const START_MAX_CLIENTS: usize = 4096;

/// One trusted network: an address with its host bits zero and a prefix length.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Network {
    /// An IPv4 network.
    V4(u32, u32),
    /// An IPv6 network.
    V6(u128, u32),
}

impl Network {
    /// Whether `address` lies inside this network; an address of the other family never does.
    #[must_use]
    pub fn contains(self, address: IpAddr) -> bool {
        match (self, address) {
            (Self::V4(network, length), IpAddr::V4(address)) => {
                u32::from(address).checked_shr(32 - length).unwrap_or(0)
                    == network.checked_shr(32 - length).unwrap_or(0)
            }
            (Self::V6(network, length), IpAddr::V6(address)) => {
                u128::from(address).checked_shr(128 - length).unwrap_or(0)
                    == network.checked_shr(128 - length).unwrap_or(0)
            }
            _ => false,
        }
    }
}

/// The trusted proxy configuration is not a list of exact networks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InvalidProxies;

/// Parse the comma-separated trusted proxy networks; absent means none.
///
/// Every item is exactly one network with its prefix length and no surrounding space: an IPv4 dotted quad without
/// leading zeros or an IPv6 address without a zone, then `/` and a length without leading zeros, with the host bits
/// zero. An empty value or item, a bare address, a netmask or hostmask, or anything else refuses the whole value.
///
/// # Errors
///
/// Any item is not such a network, or the value is not UTF-8.
pub fn trusted_proxies(value: Option<&std::ffi::OsStr>) -> Result<Vec<Network>, InvalidProxies> {
    let Some(value) = value else {
        return Ok(Vec::new());
    };
    value
        .to_str()
        .ok_or(InvalidProxies)?
        .split(',')
        .map(network)
        .collect()
}

fn network(item: &str) -> Result<Network, InvalidProxies> {
    let (address, length) = item.split_once('/').ok_or(InvalidProxies)?;
    let candidate = if address.contains(':') {
        let parsed = address.parse::<Ipv6Addr>().or(Err(InvalidProxies))?;
        Network::V6(u128::from(parsed), prefix_length(length, 128)?)
    } else {
        let parsed = address.parse::<Ipv4Addr>().or(Err(InvalidProxies))?;
        Network::V4(u32::from(parsed), prefix_length(length, 32)?)
    };
    let host_bits_zero = match candidate {
        Network::V4(network, length) => network.checked_shl(length).unwrap_or(0) == 0,
        Network::V6(network, length) => network.checked_shl(length).unwrap_or(0) == 0,
    };
    host_bits_zero.then_some(candidate).ok_or(InvalidProxies)
}

/// A decimal prefix length up to `longest`, without a sign or a leading zero.
fn prefix_length(text: &str, longest: u32) -> Result<u32, InvalidProxies> {
    let canonical = !text.is_empty()
        && text.bytes().all(|byte| byte.is_ascii_digit())
        && (text == "0" || !text.starts_with('0'));
    let length = text
        .parse::<u32>()
        .ok()
        .filter(|length| canonical && *length <= longest);
    length.ok_or(InvalidProxies)
}

/// The admission key of one client: an IPv4 address, or the /64 an IPv6 subscriber usually holds whole, so that
/// per-address IPv6 keys cannot let one client mint unbounded keys.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum ClientKey {
    /// An IPv4 client.
    V4(u32),
    /// The first 64 bits of an IPv6 client.
    V6Prefix(u64),
}

/// A trusted proxy omitted, repeated, or malformed the client address.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ClientAddressError;

/// An IPv4-mapped IPv6 address as its IPv4 address; any other address as it is.
fn canonical(address: IpAddr) -> IpAddr {
    match address {
        IpAddr::V6(v6) => v6.to_ipv4_mapped().map_or(address, IpAddr::V4),
        IpAddr::V4(_) => address,
    }
}

fn key(address: IpAddr) -> ClientKey {
    match canonical(address) {
        IpAddr::V4(v4) => ClientKey::V4(u32::from(v4)),
        IpAddr::V6(v6) => {
            ClientKey::V6Prefix(u64::try_from(v6.to_bits() >> 64).unwrap_or_default())
        }
    }
}

/// The admission key of one request: the trusted proxy's asserted client, or the socket peer itself.
///
/// The asserted client is a plain IPv4 address or an IPv6 address; the standard parser admits no zone.
///
/// # Errors
///
/// The peer is a trusted proxy and the request carries no, several, or an invalid `CF-Connecting-IP`.
pub fn client_key(
    peer: IpAddr,
    headers: &HeaderMap,
    proxies: &[Network],
) -> Result<ClientKey, ClientAddressError> {
    let peer = canonical(peer);
    if !proxies.iter().any(|network| network.contains(peer)) {
        return Ok(key(peer));
    }
    let mut forwarded = headers.get_all("cf-connecting-ip").iter();
    let (Some(client), None) = (forwarded.next(), forwarded.next()) else {
        return Err(ClientAddressError);
    };
    let address = std::str::from_utf8(client.as_bytes())
        .ok()
        .and_then(|text| text.parse::<IpAddr>().ok())
        .ok_or(ClientAddressError)?;
    Ok(key(address))
}

#[derive(Clone, Copy, Debug)]
struct Bucket {
    tokens: f64,
    updated: f64,
}

/// Per-key token buckets with a bounded key count and a bounded idle lifetime.
///
/// A bucket idle for one full period has refilled, so it is dropped as equivalent to a new one; beyond `max_keys` the
/// least recently used bucket is dropped. Every operation is the Python Store's, in the same floating-point order.
#[derive(Debug)]
pub struct TokenBuckets {
    capacity: f64,
    period: f64,
    rate: f64,
    max_keys: usize,
    /// Buckets from least to most recently used.
    order: BTreeMap<u64, (ClientKey, Bucket)>,
    index: HashMap<ClientKey, u64>,
    next: u64,
}

impl TokenBuckets {
    /// Buckets of `capacity` tokens refilling over `period` seconds, for at most `max_keys` keys.
    #[must_use]
    pub fn new(capacity: f64, period: f64, max_keys: usize) -> Self {
        Self {
            capacity,
            period,
            rate: capacity / period,
            max_keys,
            order: BTreeMap::new(),
            index: HashMap::new(),
            next: 0,
        }
    }

    /// Spend one token for `key` at monotonic second `now`: 0 when admitted, otherwise the whole seconds until a
    /// token is available.
    pub fn take(&mut self, key: ClientKey, now: f64) -> u64 {
        while let Some((_, (oldest, bucket))) = self.order.first_key_value() {
            if now - bucket.updated < self.period {
                break;
            }
            let oldest = *oldest;
            self.order.pop_first();
            self.index.remove(&oldest);
        }
        let kept = self
            .index
            .remove(&key)
            .and_then(|sequence| self.order.remove(&sequence));
        let bucket = kept.map_or(
            Bucket {
                tokens: self.capacity,
                updated: now,
            },
            |(_, bucket)| bucket,
        );
        let mut tokens = self
            .capacity
            .min(bucket.tokens + (now - bucket.updated) * self.rate);
        let mut retry_after = 0;
        if tokens >= 1.0 {
            tokens -= 1.0;
        } else {
            retry_after = whole_seconds((1.0 - tokens) / self.rate);
        }
        self.order.insert(
            self.next,
            (
                key,
                Bucket {
                    tokens,
                    updated: now,
                },
            ),
        );
        self.index.insert(key, self.next);
        self.next += 1;
        let over = self.order.len() > self.max_keys;
        if let Some((_, (evicted, _))) = over.then(|| self.order.pop_first()).flatten() {
            self.index.remove(&evicted);
        }
        retry_after
    }

    /// How many keys hold a bucket.
    #[must_use]
    pub fn len(&self) -> usize {
        self.order.len()
    }

    /// Whether no key holds a bucket.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.order.is_empty()
    }
}

/// `max(1, ceil(seconds))` for a positive wait, without a float-to-integer cast.
fn whole_seconds(seconds: f64) -> u64 {
    let mut whole = 1_u32;
    while f64::from(whole) < seconds {
        whole += 1;
    }
    u64::from(whole)
}

/// Why a start was refused before any broker work.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StartRefusal {
    /// A trusted proxy omitted, repeated, or malformed the client address.
    ClientAddress,
    /// The client spent its budget; it may retry after this many seconds.
    Limited(u64),
}

/// The start route's admission: the trusted proxies and one bucket per client, on the Store's clock.
pub struct StartLimit {
    proxies: Vec<Network>,
    buckets: Mutex<TokenBuckets>,
    clock: Arc<dyn Clock>,
}

impl StartLimit {
    /// The production budget behind these trusted proxies.
    #[must_use]
    pub fn new(proxies: Vec<Network>, clock: Arc<dyn Clock>) -> Self {
        Self {
            proxies,
            buckets: Mutex::new(TokenBuckets::new(
                START_CAPACITY,
                START_PERIOD,
                START_MAX_CLIENTS,
            )),
            clock,
        }
    }

    /// Count one start, malformed or not, against its client before any broker or Neuron work.
    ///
    /// # Errors
    ///
    /// The client address is unusable, or the client has no token left.
    pub fn admit(&self, peer: IpAddr, headers: &HeaderMap) -> Result<(), StartRefusal> {
        let key = client_key(peer, headers, &self.proxies).or(Err(StartRefusal::ClientAddress))?;
        let now = self.clock.monotonic().as_secs_f64();
        let mut buckets = self.buckets.lock().unwrap_or_else(PoisonError::into_inner);
        match buckets.take(key, now) {
            0 => Ok(()),
            retry_after => Err(StartRefusal::Limited(retry_after)),
        }
    }
}

#[cfg(test)]
mod tests;
