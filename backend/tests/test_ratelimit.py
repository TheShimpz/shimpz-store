import ipaddress

import pytest

from app.ratelimit import ClientAddressError, TokenBuckets, client_key, trusted_proxies


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_trusted_proxies_are_explicit_networks_or_none() -> None:
    assert trusted_proxies(None) == ()
    assert trusted_proxies("10.0.0.0/24, 2001:db8::/32") == (
        ipaddress.ip_network("10.0.0.0/24"),
        ipaddress.ip_network("2001:db8::/32"),
    )
    for invalid in ("", "10.0.0.0/24,", "10.0.0.1/24", "tunnel"):
        with pytest.raises(ValueError):
            trusted_proxies(invalid)


def test_client_key_trusts_a_forwarded_address_only_from_a_trusted_peer() -> None:
    proxies = trusted_proxies("10.0.0.0/24")

    assert client_key("192.0.2.10", ["203.0.113.5"], proxies) == "192.0.2.10"
    assert client_key("10.0.0.9", ["203.0.113.5"], proxies) == "203.0.113.5"
    assert client_key("::ffff:10.0.0.9", ["::ffff:203.0.113.5"], proxies) == "203.0.113.5"
    assert client_key("10.0.0.9", ["2001:db8:1:2:3:4:5:6"], proxies) == "2001:db8:1:2::/64"
    assert client_key("2001:db8:1:2::9", [], ()) == "2001:db8:1:2::/64"
    assert client_key("testclient", ["203.0.113.5"], proxies) == "testclient"
    assert client_key(None, [], proxies) == ""
    for forwarded in ([], ["203.0.113.5", "203.0.113.6"], ["203.0.113.5, 198.51.100.1"]):
        with pytest.raises(ClientAddressError):
            client_key("10.0.0.9", forwarded, proxies)


def test_token_buckets_refill_and_report_the_wait() -> None:
    clock = _Clock()
    buckets = TokenBuckets(capacity=2, period=60.0, max_keys=8, clock=clock)

    assert [buckets.take("a"), buckets.take("a")] == [0, 0]
    assert buckets.take("a") == 30
    assert buckets.take("b") == 0
    clock.now += 30.0
    assert buckets.take("a") == 0
    assert buckets.take("a") == 30


def test_token_buckets_bound_their_lifetime_and_count() -> None:
    clock = _Clock()
    buckets = TokenBuckets(capacity=1, period=60.0, max_keys=2, clock=clock)

    assert buckets.take("a") == 0
    clock.now += 30.0
    assert buckets.take("b") == 0
    clock.now += 30.0
    assert buckets.take("c") == 0
    assert len(buckets) == 2
    assert buckets.take("b") == 30
    assert buckets.take("d") == 0
    assert len(buckets) == 2
    assert buckets.take("c") == 0
