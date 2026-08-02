# Store egress

This Store-owned boundary is the hosted OAuth broker's only route to private Neuron. The Store process and
`shimpz-store-egress` share one internal network; only the proxy joins an outbound network.

The proxy accepts exactly `CONNECT neuron.shimpz.com:443`, resolves and connects one verified public address, and
records a bounded decision before it opens the tunnel. TLS and Cloudflare Access authentication remain end to end
from Store, so this process receives no Access credential, OAuth request, response, code, client secret, or token.

The implementation is packaged only by the root `ghcr.io/theshimpz/shimpz-egress` assembly under its closed
`store` profile. It is not part of the Store web image and does not share policy, identity, audit, networks, or
lifecycle with another egress profile.
