This page describes the Routing Policy for AS4242421080.

## Route Selection

This is a rough overview, when in doubt you can check my actual filter code: [custom_filters.conf](roles/config-bird2/config/custom_filters.conf.j2)

1. Prefer routes originating from the same dn42 region, as marked by the [dn42 BGP community `(64511, 41..53)`](https://dn42.dev/howto/Bird-communities). This is essentially cold potato routing:
  - Routes with no region community or the same origin value as a PoP are given `bgp_local_pref = 500 + 200/bgp_path.len`
  - Other routes are left with a default local preference of 500
2. Prefer routes with low (<= 20ms) inter-AS latency.
  - Specifically this adds a penalty of `3*x` to `bgp_local_pref` for routes that have community `(64511, x)`, for all `4 <= x <= 9`
3. When bgp_local_pref ties, prefer routes with shortest AS path
4. Prefer routes with the lowest BGP MED.
5. Prefer routes received via eBGP over iBGP.
6. Prefer routes from edge routers closest to the current node (lowest internal distance)
7. When latency is tied, prefer the first received route (RFC 5004)

## BGP Communities

The [standard dn42 BGP Communities](https://dn42.net/howto/Bird-communities) for max. inter-AS link latency, bandwidth, and encryption are supported. All of my nodes so far are marked as >= 100 Mbps bandwidth, as capacity varies and I cannot guarantee anything higher.

### Large communities

I currently export some informational large communities:

- (4242421080, 101, X) - Route learned in this [dn42 region](https://lists.nox.tf/pipermail/dn42/2015-December/001259.html)
- (4242421080, 103, Y) - Route learned on this node, where Y is the last octet of the node's dn42 IPv4 address.
  - e.g. (4242421080, 103, 117) for de-nbg01

## ROA (Route Origin Authorization)

Strict ROA checking is enabled - routes must be **ROA_VALID** in order to be accepted.
