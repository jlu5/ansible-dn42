This page describes the Routing Policy for AS4242421080.

## Route Selection

Last updated 2021-01-11:

1. Prefer routes originating from the same dn42 region, as marked by the [dn42 BGP community `(64511, 41..53)`](https://dn42.dev/howto/Bird-communities). This is essentially cold potato routing:
  - Routes with no region community or the same origin value as a PoP are given `bgp_local_pref = 100 + 200/bgp_path.len`
  - Other routes are left with the default local preference (100)
2. When bgp_local_pref ties, prefer routes with shortest AS path
3. Prefer routes with the lowest BGP MED.
4. Prefer routes received via eBGP over iBGP.
5. Prefer routes from edge routers closest to the current node (lowest internal distance)
6. When latency is tied, prefer the first received route (RFC 5004)

## BGP Communities

The [standard dn42 BGP Communities](https://dn42.net/howto/Bird-communities) for max. inter-AS link latency, bandwidth, and encryption are supported. All of my nodes so far are marked as >=100Mbps bandwidth, as capacity varies and I cannot guarantee anything higher.

### Large communities

I currently export some informational large communities:

- (4242421080, 101, X) - Route learned in this [dn42 region](https://lists.nox.tf/pipermail/dn42/2015-December/001259.html)
- (4242421080, 103, Y) - Route learned on this node, where Y is the last octet of the node's dn42 IPv4 address.
  - e.g. (4242421080, 103, 117) for de-nbg01

## ROA (Route Origin Authorization)

Strict ROA checking is enabled - routes must be **ROA_VALID** in order to be accepted.
