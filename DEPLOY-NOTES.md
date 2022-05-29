# Deploy notes

## Host-level variables

Most settings in [`hosts.yml`](hosts.yml) should be self documenting. Here are some of the lesser used variables:

- `v6_only`: specifies that the node is IPv6 only; this disables certain components that require GitHub access for installation (default `false`).
- `serve_clearnet_dns`: serve GeoDNS addresses for clearnet (PowerDNS auth server), as defined in [`geodns.yml`](geodns.yml) (default `false`).
- `auto_iptables`: configures whether `iptables` rules should be managed by the playbooks in this repo (default `true`).
- `auto_tunnels`: for private nodes, determines whether WireGuard tunnels should be automatically managed by playbooks in this repo (default `false`).
- `igp_upstreams`: specifies (bidirectional) direct neighbours for the node, to connect using an IGP. May not be used for nodes in the `meshrouters` group.
  - I use a convention of writing nodes that appear earlier in `hosts.yml` (US > EU > APAC > private) as *upstreams* for nodes that appear later, but doing so is not required.
  - These tunnels are enumerated with [`scripts/enumerate-igp-tunnels.py`](scripts/enumerate-igp-tunnels.py) and templated in the [`config-wireguard` role](roles/config-wireguard/tasks).
- `ibgp_rr_upstreams`: for private nodes, configures iBGP route reflector upstreams.
    - These sessions are needed to broadcast parts of the network that are not distributed in Babel, such as Anycast DNS
    - Not supported for regular nodes in the `dn42routers` group, as these use a full mesh iBGP.
- `igpping_base_cost`/`igpping_fallback_cost`: sets base and default (unreachable) weights for igpping (defaults in [`igpping.conf.j2`](scripts/igpping/))
- `stub_ifnames_append`: extra interfaces to import as device routes for Babel (exact name match). See also `stub_ifnames` in [`general.yml`](global-config/general.yml)

### Runtime flags (extra variables)

These flags can be enabled using `-e <flagname>=true` on the Ansible CLI.

- `skip_wg_restart`: skip restarting all changed WireGuard tunnels
   - This can reduce noise if insignificant changes are made to the WireGuard config template
- `igpping_force`: force [`igpping`](scripts/igpping/) to recalculate latencies for configured neighbour nodes
