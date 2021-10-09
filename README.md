# ansible-dn42

This repository contains the configs for AS4242421080 / HIGHDEF-AS on [dn42](https://dn42.dev/Home). For more details, see https://highdef.network/

## Network topology

This iteration of the network uses the Babel IGP and a full mesh of iBGP sessions over WireGuard. Internal costs between nodes are [periodically generated](scripts/igpping/) based off latency and packet loss.

[Routing Policy](ROUTING-POLICY.md)

## Config structure

Here I use Ansible to configure the following components:

- Wireguard ([roles/config-wireguard/](roles/config-wireguard/)) via ifupdown
- OpenVPN 2.x
- BIRD 2 ([roles/config-bird2/](roles/config-bird2/))
- [BIRD Looking Glass](https://github.com/sesa-me/bird-lg)
- [dn42 Peerfinder](https://dn42.us/peers)
- Anycast DNS via PowerDNS:
  - Authoritative server for jlu5.dn42 and PTR zones
  - Public recursive resolver (dn42, clearnet, and interconnected networks) @ **dns.highdef.dn42** / 172.23.0.53 / fd42:d42:d42:53::1
  - For this I also use a [custom DNS zone generator](scripts/make-dns-zones.py) that reads from [YAML](global-config/dns-entries.yml) and the Ansible inventory
- iptables firewall rules for dn42

## Network history

![History of my network](history.svg)
