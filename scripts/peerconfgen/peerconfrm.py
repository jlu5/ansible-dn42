#!/usr/bin/env python3
"""
Script to remove old peerings.
"""

import argparse
import os
import pathlib
import re

import ruamel.yaml

from peerconfgen import get_config_paths, get_yaml

def remove_peer(node, peernames):
    wg_config_path = get_config_paths(node)
    peernames_set = set(peernames)
    yaml = get_yaml()
    # Peer names are in the form dn42XXX-peername or dn42-peername, truncated to 15 chars
    # pylint: disable=consider-using-f-string
    wg_peername_res = [r'(^dn42(-%s|[a-zA-Z]{3}-%s)$)' % (peername[:15-5], peername[:15-8])
                       for peername in peernames]
    wg_peername_re = re.compile('|'.join(wg_peername_res))

    with open(wg_config_path, 'r+', encoding='utf-8') as f:
        wg_config = yaml.load(f)

        wg_peers = ruamel.yaml.comments.CommentedSeq(wg_config.get('wg_peers', []))
        found = 0
        for idx, wg_peer in enumerate(wg_peers):
            bgp_asn = wg_peer.get('bgp', {}).get('asn')
            # Match either by name field or ASN
            if wg_peername_re.match(wg_peer['name']) or \
                    (bgp_asn and peernames_set.intersection({str(bgp_asn), f'as{bgp_asn}', f'AS{bgp_asn}'})):
                wg_peers[idx] = {'name': wg_peer['name'], 'remove': True}
                wg_peers.yaml_set_comment_before_after_key(idx+1, before='\n')
                print(f'Disabled peer {wg_peer["name"]!r} (AS{bgp_asn}) in WireGuard config {wg_config_path}')
                found += 1
        if not found:
            print(f'No matching peers found in WireGuard config {wg_config_path}')

        wg_config['wg_peers'] = wg_peers
        f.seek(0)
        yaml.dump(wg_config, f)
        f.truncate()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node', help='Node to generate config for', type=str)
    parser.add_argument('peernames', help='Short name / identifier or ASN for peer', type=str, nargs='+')
    args = parser.parse_args()

    # cd to repo root
    rootdir = pathlib.Path(os.path.dirname(__file__)) / ".." / ".."
    os.chdir(rootdir)
    return remove_peer(args.node, args.peernames)

if __name__ == '__main__':
    main()
