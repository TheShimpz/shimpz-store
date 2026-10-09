# Store egress

This Store-owned boundary is the hosted OAuth broker's only route to private Neuron. The Store process and
`shimpz-store-egress` share one internal network; only the proxy joins an outbound network.

The proxy accepts exactly `CONNECT neuron.shimpz.com:443`, resolves only public addresses and connects one of them,
and records a bounded decision before any upstream connection attempt. TLS and Cloudflare Access authentication
remain end to end from Store, so this process receives no Access credential, OAuth request, response, code, client
secret, or token.

The implementation is packaged only by the root `ghcr.io/theshimpz/shimpz-egress` assembly under its closed
`store` profile. It is not part of the Store web image and does not share policy, identity, audit, networks, or
lifecycle with another egress profile.

The resolution, record, connect, ClientHello admission, and splice are the image's neutral CONNECT transport
(`.egress/connect.py`, ADR-0104), shipped as this profile's own copy; this directory owns the exact request, the
audit record, and the resource envelope. After the `200`, the tunnel relays nothing until Store's TLS ClientHello
names exactly `neuron.shimpz.com` (one RFC 6066 host name, no ECH). A different, missing, or non-TLS first flight
closes both sides and is recorded as a `denied` event with code `403` and a stable reason; that code classifies the
refusal and is not sent, because the `200` already was.
