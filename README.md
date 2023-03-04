# ansible-dn42

This repository contains the configs for **AS4242421080 / HIGHDEF-AS** on [dn42](https://dn42.dev/Home). For more details, see https://highdef.network/

## Network topology

This iteration of the network uses OSPF (v2 + v3) and a full mesh of iBGP sessions over WireGuard. Internal costs between nodes are [periodically generated](scripts/igpping/) based off latency and packet loss.

[Routing Policy](ROUTING-POLICY.md)

## Config structure

Here I use Ansible to configure the following components:

### Peering tunnels

- Wireguard via ifupdown: [roles/config-wireguard/](roles/config-wireguard/)
- OpenVPN (2.5.x): [roles/config-openvpn/](roles/config-openvpn/)
- GRE (plain) via ifupdown: [roles/config-gre-plain/](roles/config-gre-plain/)

### Services and daemons

- BIRD 2: [roles/config-bird2/](roles/config-bird2/)
- bird-lg-go looking glass: [roles/setup-bird-lg-go/](roles/setup-bird-lg-go/)
- nginx - frontend reverse proxy to services + a dn42 splash site
- PowerDNS (authoritative server + recursor):
  - Anycast authoritative server for dn42 zones: [roles/config-powerdns/](roles/config-powerdns/)
    - **ns.highdef.dn42** / l.delegation-servers.dn42
  - Anycast recursor for dn42, clearnet, and interconnected networks: [roles/config-powerdns-recursor/](roles/config-powerdns-recursor/)
    - **dns.highdef.dn42** / l.recursive-servers.dn42 / 172.23.0.53 / fd42:d42:d42:53::1

### Statistics and monitoring

- Netdata: [roles/setup-netdata-v2/](roles/setup-netdata-v2/)
- Smokeping @ [ping.highdef.dn42](http://ping.highdef.dn42): [roles/setup-smokeping/](roles/setup-smokeping/)

---

Some components (Bird backports, etc.) pull from my personal APT repository @ https://deb.utopia-repository.org/

## Network growth over time

Note that these values represent configured peers, which may or may not be up at any particular time.

![History of my network](history.svg)
