#!/usr/bin/env python3
import argparse
import pathlib
from collections import defaultdict

from _common import yaml_load

_WG_PEERS_DIR = pathlib.Path(__file__).parent.parent / 'roles' / 'config-wireguard' / 'config'

def get_depeered_asns(nodes_to_remove=None):
    """Get a list of which ASNs would be depeered if a node gets shut down"""
    asn_mapping = defaultdict(set)

    if nodes_to_remove is not None:
        nodes_to_remove = set(nodes_to_remove)

    # Loop through all YAML files in the directory
    for filename in _WG_PEERS_DIR.iterdir():
        if filename.suffix == ".yml":
            # Load the YAML content
            data = yaml_load(filename)

            # Check for the 'wg_peers' key and process each entry
            if 'wg_peers' in data:
                server = filename.stem
                for peer in data['wg_peers']:
                    name = peer.get('name')
                    asn = peer.get('bgp', {}).get('asn')

                    # Ensure name and ASN are valid before adding to mapping
                    if name and asn:
                        asn_mapping[asn].add(server)

    affected_links = defaultdict(set)
    for asn, servers in asn_mapping.items():
        if nodes_to_remove:
            if not (servers - nodes_to_remove):
                affected_links[tuple(nodes_to_remove)].add(asn)
        else:
            if len(servers) == 1:
                affected_links[next(iter(servers))].add(asn)
    return dict(affected_links)

def main():
    parser = argparse.ArgumentParser(description=get_depeered_asns.__doc__)
    parser.add_argument('nodes', nargs='*')
    args = parser.parse_args()

    depeered_asns = get_depeered_asns(nodes_to_remove=args.nodes)
    depeered_asns_sorted = sorted(depeered_asns.items(), key=lambda pair: len(pair[1]))
    for server, affected_asns in depeered_asns_sorted:
        print(f'Removing {server} would disconnect {len(affected_asns)} ASNs: {affected_asns}')

if __name__ == '__main__':
    main()
