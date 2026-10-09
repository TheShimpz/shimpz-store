"""Bounded per-client admission for the public OAuth start route.

Cloudflare's zone rule is the primary start limit; this in-process token bucket is defense in depth for the broker's
shared authorization capacity and its Neuron calls. Only a peer inside an explicitly trusted proxy network (the tunnel
connector's two-member edge network) may name the client, with exactly one canonical `CF-Connecting-IP`; every other
peer is keyed by its own socket address, so no header lets a direct peer choose its key.
"""

import ipaddress
import math
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence

type Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class ClientAddressError(ValueError):
    """A trusted proxy omitted, repeated, or malformed the client address."""


def trusted_proxies(value: str | None) -> tuple[Network, ...]:
    """Parse the comma-separated trusted proxy networks; absent means none, and an empty item is refused."""
    if value is None:
        return ()
    items = [item.strip() for item in value.split(",")]
    if not all(items):
        raise ValueError("trusted proxy configuration is invalid")
    return tuple(ipaddress.ip_network(item) for item in items)


def _canonical(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    parsed = ipaddress.ip_address(address)
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        return parsed.ipv4_mapped
    return parsed


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
        return _key(_canonical(forwarded[0]))
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

    def __len__(self) -> int:
        return len(self._buckets)

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
