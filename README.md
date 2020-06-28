# AS4242421080 / JLU5-AS config

This repository contains the configs for AS4242421080/JLU5-AS on [dn42](https://dn42.net/Home). For peering details, see https://jlu5.com/dn42

## Network topology

Currently the network uses bare iBGP, with [tunnels between all routers](roles/config-wireguard/tasks) and [manually configured costs](roles/config-bird2/config/ibgp_costs.yml) between nodes.

## Config structure

Here I use Ansible to configure the following components:

- Wireguard ([roles/config-wireguard/](roles/config-wireguard/))
- BIRD 2 ([roles/config-bird2/](roles/config-bird2/))
- [BIRD Looking Glass](https://github.com/sesa-me/bird-lg)
- [dn42 Peerfinder](https://dn42.us/peers)

Things not included:

- DNS master (TODO)
- Firewall (Managed elsewhere)
