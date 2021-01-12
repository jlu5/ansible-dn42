# AS4242421080 / JLU5-AS config

This repository contains the configs for AS4242421080 / JLU5-AS on [dn42](https://dn42.net/Home). For peering details, see https://jlu5.com/dn42

## Network topology

This iteration of the network uses Babel as IGP and a full mesh of iBGP connections. [Costs between links](global-config/internal_costs.yml) are manually configured to roughly match the link latency.

[Routing Policy](routing-policy.md)

## Config structure

Here I use Ansible to configure the following components:

- Wireguard ([roles/config-wireguard/](roles/config-wireguard/)) via ifupdown (i.e. `/etc/network/interfaces.d`)
- BIRD 2 ([roles/config-bird2/](roles/config-bird2/))
- [BIRD Looking Glass](https://github.com/sesa-me/bird-lg)
- [dn42 Peerfinder](https://dn42.us/peers)
- Anycast DNS via PowerDNS:
  - Authoritative server for jlu5.dn42 and PTR zones
  - Public recursive resolver (dn42, NeoNetwork, clearnet) @ **dns.jlu5.dn42**
  - For this I also use a [custom DNS zone generator](scripts/make-dns-zones.py) that reads from [YAML](global-config/dns-entries.yml) and the Ansible inventory
- iptables firewall rules for dn42

## Network history

![History of my network](history.svg)
