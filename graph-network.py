#!/usr/bin/env python3
"""
Generates a network graph for AS42421080.
"""

import argparse
import collections

import graphviz
import yaml
# Add a stub handler to ignore Ansible specific values like !vault
# See https://github.com/yaml/pyyaml/issues/86
yaml.add_multi_constructor('', lambda *args: None)

REGIONS = {
    41: 'Europe',
    42: 'North America',
    43: 'North America',
    44: 'North America',
}

def _yaml_load(filename):
    with open(filename) as f:
        return yaml.full_load(f.read())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--outfile", help="output path", default="AS4242421080.gv")
    parser.add_argument("-H", "--hosts", help="path to hosts configuration / inventory file",
                        type=str, default='hosts.yml')
    parser.add_argument("-c", "--costs", help="path to internal costs configuration",
                        type=str, default='roles/config-bird2/config/internal_costs.yml')
    parser.add_argument("-t", "--tunnels", help="path to IGP tunnels configuration",
                        type=str, default='igp-tunnels.yml')
    parser.add_argument("-f", "--format", help="output format",
                        type=str, default='svg')
    args = parser.parse_args()

    hosts = _yaml_load(args.hosts)
    costs = _yaml_load(args.costs)
    tunnels = _yaml_load(args.tunnels)

    dot = graphviz.Digraph(comment='AS4242421080 network graph', format=args.format, engine='dot')
    dot.attr(ratio='0.8')

    short_names = {}
    # Group nodes by region using cluster subgraphs
    node_region_map = collections.defaultdict(set)
    for node, nodedata in hosts['dn42routers']['hosts'].items():
        short_names[node] = sn = nodedata['shortname']
        region_text = REGIONS[nodedata['dn42_region']]
        node_region_map[region_text].add(sn)

    for region, nodes_in_region in node_region_map.items():
        # "cluster" prefix has a special meaning in dot language and makes the subgraph treated as a cluster
        with dot.subgraph(name=f'cluster_{region}') as cluster:
            cluster.attr(label=region, fontname='bold')
            for node in nodes_in_region:
                cluster.node(node, node)

    seen = set()
    # Draw edges to represent IGP connections
    for node, neighbours in tunnels['igp_neighbours'].items():
        if node not in short_names:
            continue
        node = short_names[node]
        for neighbour in neighbours:
            neighbour = short_names[neighbour]
            if f'{neighbour},{node}' not in seen:
                datapair = f'{node},{neighbour}'
                seen.add(datapair)
                cost = costs['internal_costs'].get(datapair) or costs['internal_costs'].get(f'{neighbour},{node}') or costs['default_cost']
                dot.edge(neighbour, node, label=str(cost), dir='both', color='grey')

    dot.render(args.outfile)
    print(f"Wrote graph to {args.outfile}.{args.format}")

if __name__ == "__main__":
    main()
