# Deploy notes

## Host-level variables

Most settings in [`hosts.yml`](hosts.yml) should be self documenting. Here are some of the lesser used variables:

- `public_host`: public facing hostname for services like webtrace; defaults to `ansible_host`
   - `public_host_v4` and `public_host_v6` set this for a specific address family
- `export_ownnets`: determines whether static routes for aggregated dn42 prefixes should be configured (default `true`)
- `v6_only`: specifies that the node is IPv6 only; this disables certain components that require GitHub access for installation (default `false`).
- `v4_only`: specifies that the node is IPv4 only
- `auto_iptables`: configures whether `iptables` rules should be managed by the playbooks in this repo (default `true`).
- `auto_tunnels`: determines whether WireGuard tunnels should be automatically created to connect to IGP (default `true`).
- `import_roa`: for private nodes, determines whether the node should import dn42 ROA (must be true for eBGP routers, default `false`)
- `igp_upstreams`: specifies (bidirectional) direct neighbours for the node, to connect using an IGP.
  - I use a convention of writing nodes that appear earlier in `hosts.yml` (US > EU > APAC > private) as *upstreams* for nodes that appear later, but doing so is not required.
  - These tunnels are enumerated with [`scripts/enumerate-igp-tunnels.py`](scripts/enumerate-igp-tunnels.py) and templated in the [`config-wireguard` role](roles/config-wireguard/tasks).
- `ibgp_rr_upstreams`: for private nodes, configures iBGP route reflector upstreams.
    - These sessions are needed to broadcast parts of the network that are not distributed in an IGP, such as Anycast DNS
    - Not supported for regular nodes in the `dn42routers` group, as these use a full mesh iBGP.
- `igpping_base_cost`/`igpping_fallback_cost`: sets base and default (unreachable) weights for igpping (defaults in [`igpping.conf.j2`](scripts/igpping/))
- `igpping_override`: a map of IGP node name to IGP metric; used to override igpping on specific links
- `stub_ifnames_append`: extra interfaces to import as device routes in the IGP. See also `stub_ifnames` in [`general.yml`](global-config/general.yml)

### Runtime flags (extra variables)

These flags can be enabled using `-e <flagname>=true` on the Ansible CLI.

- `skip_wg_restart`: skip restarting all changed WireGuard tunnels
   - This can reduce noise if insignificant changes are made to the WireGuard config template
- `skip_wg_dn42_peers`: skip templating interfaces for dn42 peers
- `igpping_force`: force [`igpping`](scripts/igpping/) to recalculate latencies for configured neighbours
