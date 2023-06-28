#!/usr/bin/env python3
"""
Script to automate removing old peerings.
"""

import argparse
import os
import pathlib
import re

import ruamel.yaml

from peerconfgen import get_config_paths, get_yaml

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node', help='Node to generate config for', type=str)
    parser.add_argument('peername', help='Short name / identifier for peer', type=str)
    args = parser.parse_args()

    # cd to repo root
    rootdir = pathlib.Path(os.path.dirname(__file__)) / ".." / ".."
    os.chdir(rootdir)

    wg_config_path, bird_config_path = get_config_paths(args.node, args.peername, replace=True)
    yaml = get_yaml()

    with open(wg_config_path, 'r+', encoding='utf-8') as f:
        wg_config = yaml.load(f)

        wg_peers = ruamel.yaml.comments.CommentedSeq(wg_config.get('wg_peers', []))
        found = False
        for idx, wg_peer in enumerate(wg_peers):
            # Peer names are in the form dn42XXX-peername or dn42-peername,
            # truncated to 15 chars
            # pylint: disable=consider-using-f-string
            wg_peername_re = re.compile(r'^dn42(-%s|[a-zA-Z]{3}-%s)$' % (args.peername[:15-5], args.peername[:15-8]))
            if wg_peername_re.match(wg_peer['name']):
                wg_peers[idx] = {'name': wg_peer['name'], 'remove': True}
                wg_peers.yaml_set_comment_before_after_key(idx+1, before='\n')
                print(f'Disabled peer {args.peername!r} (iface {wg_peer["name"]!r}) in WireGuard config {wg_config_path}')
                found = True
        if not found:
            print(f'Peer {args.peername!r} not found in WireGuard config {wg_config_path}')

        wg_config['wg_peers'] = wg_peers
        f.seek(0)
        yaml.dump(wg_config, f)
        f.truncate()

    try:
        os.remove(bird_config_path)
    except OSError as exc:
        print(f'Could not delete {bird_config_path}: {exc}')

if __name__ == '__main__':
    main()
