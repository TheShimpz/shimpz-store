"""Bounded per-client admission for the public OAuth start route.

Cloudflare's zone rule is the primary start limit; this in-process token bucket is defense in depth for the broker's
shared authorization capacity and its Neuron calls. Only a peer inside an explicitly trusted proxy network (the tunnel
connector's two-member edge network) may name the client, with exactly one canonical `CF-Connecting-IP`; every other
peer is keyed by its own socket address, so no header lets a direct peer choose its key.
"""

import ipaddress
import math
import re
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence

type Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class ClientAddressError(ValueError):
    """A trusted proxy omitted, repeated, or malformed the client address."""


_IPV4 = r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}"
_IPV4_NETWORK = re.compile(rf"{_IPV4}/(?:3[0-2]|[12][0-9]|[0-9])")
_IPV6_NETWORK = re.compile(r"[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*/(?:12[0-8]|1[01][0-9]|[1-9][0-9]|[0-9])")


def _network(item: str) -> Network:
    """One network written `address/length` with its host bits zero: a dotted quad without leading zeros, or IPv6."""
    if _IPV4_NETWORK.fullmatch(item) is not None:
        return ipaddress.IPv4Network(item)
    if _IPV6_NETWORK.fullmatch(item) is not None:
        return ipaddress.IPv6Network(item)
    raise ValueError("trusted proxy configuration is invalid")


def trusted_proxies(value: str | None) -> tuple[Network, ...]:
    """Parse the comma-separated trusted proxy networks; absent means none.

    Every item is exactly one network with its prefix length and no surrounding space: an empty value or item, a bare
    address, a netmask or hostmask, set host bits, or an IPv6 zone refuses the whole configuration.
    """
    if value is None:
        return ()
    return tuple(_network(item) for item in value.split(","))


def _canonical(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    parsed = ipaddress.ip_address(address)
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        return parsed.ipv4_mapped
    return parsed


def _client(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """A proxy-asserted client: a plain address, never an IPv6 address with a zone."""
    if "%" in address:
        raise ValueError("a client address has no zone")
    return _canonical(address)


def _key(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    # One IPv6 subscriber usually holds a whole /64, so per-address IPv6 keys would let one client mint unbounded keys.
    if isinstance(address, ipaddress.IPv6Address):
        return str(ipaddress.IPv6Network((address, 64), strict=False))
    return str(address)


def client_key(peer: str | None, forwarded: Sequence[str], proxies: Sequence[Network]) -> str:
    """The admission key of one request: the trusted proxy's asserted client, or the socket peer itself."""
    try:
        peer_address = _canonical(peer or "")
    except ValueError:
        return peer or ""
    if not any(peer_address in network for network in proxies):
        return _key(peer_address)
    if len(forwarded) != 1:
        raise ClientAddressError("trusted proxy client address is missing or ambiguous")
    try:
        return _key(_client(forwarded[0]))
    except ValueError as exc:
        raise ClientAddressError("trusted proxy client address is invalid") from exc


class TokenBuckets:
    """Per-key token buckets with a bounded key count and a bounded idle lifetime.

    A bucket idle for one full period has refilled, so it is dropped as equivalent to a new one; beyond `max_keys` the
    least recently used bucket is dropped. Calls run on the event loop thread and never await, so they are atomic.
    """

    def __init__(
        self, *, capacity: int, period: float, max_keys: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._capacity = float(capacity)
        self._period = period
        self._rate = capacity / period
        self._max_keys = max_keys
        self._clock = clock
        self._buckets: OrderedDict[str, tuple[float, float]] = OrderedDict()

    def take(self, key: str) -> int:
        """Spend one token for `key`: 0 when admitted, otherwise the whole seconds until a token is available."""
        now = self._clock()
        while self._buckets:
            oldest, (_tokens, updated) = next(iter(self._buckets.items()))
            if now - updated < self._period:
                break
            del self._buckets[oldest]
        tokens, updated = self._buckets.pop(key, (self._capacity, now))
        tokens = min(self._capacity, tokens + (now - updated) * self._rate)
        retry_after = 0
        if tokens >= 1:
            tokens -= 1
        else:
            retry_after = max(1, math.ceil((1 - tokens) / self._rate))
        self._buckets[key] = (tokens, now)
        if len(self._buckets) > self._max_keys:
            self._buckets.popitem(last=False)
        return retry_after
