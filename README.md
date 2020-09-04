# AS4242421080 / JLU5-AS config

This repository contains the configs for AS4242421080/JLU5-AS on [dn42](https://dn42.net/Home). For peering details, see https://jlu5.com/dn42

## Network topology

![AS4242421080 Network Map](AS4242421080.svg)

This iteration of the network uses Babel as IGP and a full mesh of iBGP connections. [Costs between links](roles/config-bird2/config/internal_costs.yml) are manually configured to roughly match the link latency.

[Routing Policy](https://jlu5.com/dn42/routing-policy)

## Config structure

Here I use Ansible to configure the following components:

- Wireguard ([roles/config-wireguard/](roles/config-wireguard/))
- BIRD 2 ([roles/config-bird2/](roles/config-bird2/))
- [BIRD Looking Glass](https://github.com/sesa-me/bird-lg)
- [dn42 Peerfinder](https://dn42.us/peers)
- Anycast DNS via PowerDNS:
  - Authoritative server for jlu5.dn42 and PTR zones
  - Recursive server (localhost-only for now)

Things not included:

- Firewall (Managed elsewhere)
