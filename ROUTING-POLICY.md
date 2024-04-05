This page describes the Routing Policy for AS4242421080.

## Route Selection

This is a rough overview, when in doubt you can check my actual filter code: [`custom_filters.conf.j2`](roles/config-bird2/config/custom_filters.conf.j2)

1. Prefer the shortest AS path.
2. For routes containing the [dn42 region communities](https://dn42.dev/howto/Bird-communities), prefer routes originating in the same super-region (see below) as an edge node. This is effectively cold potato routing:
  - Routes with matching dn42 region to an edge node or no dn42 region community at all are assigned `bgp_med = 50`. Other routes are assigned `bgp_med = 100`.
3. Prefer routes received via eBGP over iBGP.
4. Prefer routes from edge routers closest to the current node (lowest internal distance). Internal costs are periodically recalculated from inter-node [latency](https://github.com/jlu5/ansible-dn42/tree/main/scripts/igpping).
5. When latency is tied, prefer the first received route (RFC 5004).

Routes with unusually large path lengths (> 12) are rejected as they usually signal ghost routes.

Some exceptions apply (see in `handle_special_cases`).

### AS4242421080 Super Regions

These are defined in `get_region_tag` of [`custom_filters.conf.j2`](roles/config-bird2/config/custom_filters.conf.j2):

- **1**: North America (West) - dn42 community `(64511, 44)`
- **2**: North America (East) - dn42 community `(64511, 42..43)`
- **3**: Europe - dn42 community `(64511, 41)`
- **4**: Asia-Pacific - dn42 community `(64511, 51..53)`
- **0**: Everything else (no presence in my AS)

## BGP Communities

The [standard dn42 BGP Communities](https://dn42.net/howto/Bird-communities) for max. inter-AS link latency, bandwidth, and encryption are supported. All of my nodes so far are marked as >= 10 Mbps bandwidth, as capacity varies and I cannot guarantee anything higher.

### Large communities

I currently export some informational large communities:

- (4242421080, 101, X) - Route learned in this [dn42 region](https://lists.nox.tf/pipermail/dn42/2015-December/001259.html)
- (4242421080, 103, Y) - Route learned on this node, where Y is the last octet of the node's dn42 IPv4 address.
  - e.g. (4242421080, 103, 117) for de-nbg01

## ROA (Route Origin Authorization)

Strict ROA checking is enabled - routes must be **ROA_VALID** in order to be accepted.
