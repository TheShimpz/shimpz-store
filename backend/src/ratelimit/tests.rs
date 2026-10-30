use std::{
    ffi::{OsStr, OsString},
    net::IpAddr,
    os::unix::ffi::OsStringExt,
    sync::Arc,
    time::Duration,
};

use http::{HeaderMap, HeaderValue};

use super::{
    ClientAddressError, ClientKey, InvalidProxies, Network, StartLimit, StartRefusal, TokenBuckets,
    client_key, trusted_proxies, whole_seconds,
};
use crate::clock::ManualClock;

fn parsed(value: &str) -> Result<Vec<Network>, InvalidProxies> {
    trusted_proxies(Some(OsStr::new(value)))
}

fn ip(text: &str) -> IpAddr {
    text.parse().unwrap()
}

fn forwarded(values: &[&[u8]]) -> HeaderMap {
    let mut headers = HeaderMap::new();
    for value in values {
        headers.append("cf-connecting-ip", HeaderValue::from_bytes(value).unwrap());
    }
    headers
}

#[test]
fn trusted_proxies_are_explicit_networks_or_none() {
    assert_eq!(trusted_proxies(None), Ok(Vec::new()));
    assert_eq!(
        parsed("10.0.0.0/24,2001:db8::/32,0.0.0.0/0,::ffff:10.0.0.0/120,255.255.255.255/32,::/0"),
        Ok(vec![
            Network::V4(0x0a00_0000, 24),
            Network::V6(0x2001_0db8 << 96, 32),
            Network::V4(0, 0),
            Network::V6(0xffff_0a00_0000, 120),
            Network::V4(u32::MAX, 32),
            Network::V6(0, 0),
        ])
    );
}

#[test]
fn trusted_proxies_refuse_every_other_network_form() {
    let invalid = [
        "",
        "10.0.0.0/24,",
        ",10.0.0.0/24",
        "10.0.0.1/24",
        "tunnel",
        "10.0.0.0/24, 2001:db8::/32",
        " 10.0.0.0/24",
        "10.0.0.0/24\n",
        "\u{a0}10.0.0.0/24",
        "10.0.0.1",
        "2001:db8::",
        "10.0.0.0/255.255.255.0",
        "10.0.0.0/0.0.0.255",
        "010.0.0.0/24",
        "10.0.0.0/024",
        "10.0.0.0/33",
        "10.0.0.0/",
        "10.0.0.0/+8",
        "10.0.0.0/99999999999",
        "2001:db8::/129",
        "2001:db8::/032",
        "fe80::%eth0/64",
        "\u{661}\u{660}.0.0.0/24",
        "10.0.0.0/\u{662}\u{664}",
        "2001:db8::1/64",
        "::1/0",
    ];
    for value in invalid {
        assert_eq!(parsed(value), Err(InvalidProxies), "{value:?}");
    }
    let not_utf8 = OsString::from_vec(b"10.0.0.0/8\xff".to_vec());
    assert_eq!(trusted_proxies(Some(&not_utf8)), Err(InvalidProxies));
}

#[test]
fn a_network_holds_only_addresses_of_its_family_and_prefix() {
    let networks = parsed("10.0.0.0/24,2001:db8::/32,0.0.0.0/0,::/0,192.0.2.7/32").unwrap();
    let cases = [
        (0, "10.0.0.255", true),
        (0, "10.0.1.0", false),
        (0, "::ffff:10.0.0.1", false),
        (1, "2001:db8:ffff::1", true),
        (1, "2001:db9::", false),
        (1, "10.0.0.1", false),
        (2, "255.255.255.255", true),
        (3, "ffff::", true),
        (4, "192.0.2.7", true),
        (4, "192.0.2.6", false),
    ];
    for (network, address, inside) in cases {
        assert_eq!(networks[network].contains(ip(address)), inside, "{address}");
    }
}

#[test]
fn client_key_trusts_a_forwarded_address_only_from_a_trusted_peer() {
    let proxies = parsed("10.0.0.0/24").unwrap();
    let client = forwarded(&[b"203.0.113.5"]);
    let v4 = ClientKey::V4(0xcb00_7105);
    assert_eq!(
        client_key(ip("192.0.2.10"), &client, &proxies),
        Ok(ClientKey::V4(0xc000_020a))
    );
    assert_eq!(client_key(ip("10.0.0.9"), &client, &proxies), Ok(v4));
    assert_eq!(
        client_key(
            ip("::ffff:10.0.0.9"),
            &forwarded(&[b"::ffff:203.0.113.5"]),
            &proxies
        ),
        Ok(v4)
    );
    let prefix = ClientKey::V6Prefix(0x2001_0db8_0001_0002);
    assert_eq!(
        client_key(
            ip("10.0.0.9"),
            &forwarded(&[b"2001:db8:1:2:3:4:5:6"]),
            &proxies
        ),
        Ok(prefix)
    );
    assert_eq!(
        client_key(ip("2001:db8:1:2::9"), &HeaderMap::new(), &[]),
        Ok(prefix)
    );
    let refusals: [&[&[u8]]; 8] = [
        &[],
        &[b"203.0.113.5", b"203.0.113.6"],
        &[b"203.0.113.5, 198.51.100.1"],
        &[b"fe80::1%eth0"],
        &[b"2001:db8::1%1"],
        &[b"203.0.113.05"],
        &[b"\xcb.0.113.5"],
        &[b"tunnel"],
    ];
    for values in refusals {
        assert_eq!(
            client_key(ip("10.0.0.9"), &forwarded(values), &proxies),
            Err(ClientAddressError),
            "{values:?}"
        );
    }
}

#[test]
fn token_buckets_refill_and_report_the_wait() {
    let mut buckets = TokenBuckets::new(2.0, 60.0, 8);
    let (a, b) = (ClientKey::V4(1), ClientKey::V4(2));
    assert_eq!([buckets.take(a, 1000.0), buckets.take(a, 1000.0)], [0, 0]);
    assert_eq!(buckets.take(a, 1000.0), 30);
    assert_eq!(buckets.take(b, 1000.0), 0);
    assert_eq!(buckets.take(a, 1030.0), 0);
    assert_eq!(buckets.take(a, 1030.0), 30);
}

#[test]
fn token_buckets_bound_their_lifetime_and_count() {
    let mut buckets = TokenBuckets::new(1.0, 60.0, 2);
    let [a, b, c, d] = [1, 2, 3, 4].map(ClientKey::V4);
    assert!(buckets.is_empty());
    assert_eq!(buckets.take(a, 1000.0), 0);
    assert_eq!(buckets.take(b, 1030.0), 0);
    assert_eq!(buckets.take(c, 1060.0), 0);
    assert_eq!(buckets.len(), 2);
    assert_eq!(buckets.take(b, 1060.0), 30);
    assert_eq!(buckets.take(d, 1060.0), 0);
    assert_eq!(buckets.take(c, 1060.0), 0);
    assert_eq!(buckets.len(), 2);
}

#[test]
fn a_wait_is_at_least_one_whole_second_rounded_up() {
    assert_eq!(whole_seconds(0.01), 1);
    assert_eq!(whole_seconds(1.0), 1);
    assert_eq!(whole_seconds(1.000_001), 2);
    assert_eq!(whole_seconds(6.0), 6);
}

#[test]
fn the_start_limit_spends_ten_tokens_a_minute_per_client_and_refuses_unusable_addresses() {
    let clock = Arc::new(ManualClock::at(0));
    let limit = StartLimit::new(parsed("10.0.0.0/24").unwrap(), clock.clone());
    let peer = ip("192.0.2.1");
    for _ in 0..10 {
        assert_eq!(limit.admit(peer, &HeaderMap::new()), Ok(()));
    }
    assert_eq!(
        limit.admit(peer, &HeaderMap::new()),
        Err(StartRefusal::Limited(6))
    );
    clock.step(Duration::from_secs(6));
    assert_eq!(limit.admit(peer, &HeaderMap::new()), Ok(()));
    assert_eq!(limit.admit(ip("192.0.2.2"), &HeaderMap::new()), Ok(()));
    assert_eq!(
        limit.admit(ip("10.0.0.1"), &HeaderMap::new()),
        Err(StartRefusal::ClientAddress)
    );
}
