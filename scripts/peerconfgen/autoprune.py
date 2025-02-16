#!/usr/bin/env python3
"""
Script to automate removing stale / down peerings.
"""

import argparse
import collections
import datetime
import os
import pathlib

import git
import requests

from peerconfgen import get_yaml
from peerconfrm import remove_peer

def query_prometheus(prometheus_url, query):
    """
    Queries Prometheus and returns the results as a JSON object.
    """
    url = prometheus_url + "/api/v1/query"
    params = {'query': query}
    print(f'Querying {url} ...')
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    assert data['status'] == 'success'
    assert data['data']['resultType'] == 'vector'
    return data['data']

class Autoprune():
    def __init__(self, root, threshold=40):
        self.repo = git.Repo(root)
        self.asn_to_conf_lines = {}
        self.line_to_mod_time = {}

        # A peer is considered inactive if it was NEVER up within the last X days
        self.query = '''max by (loc, name)(max_over_time(bird_protocol_up{name=~"AS.+"}[%dd])) == 0''' % threshold

        self._read_configs()

    def expand_blame_mod_times(self, fname: str, rev='HEAD'):
        """
        Return a dict of (line number -> last commit modified time) for all lines in fname
        """
        result = {}
        linenum = 1
        for commit, lines in self.repo.blame(rev, fname):
            for _ in lines:
                result[linenum] = commit.committed_date
                linenum += 1
        return result

    def _read_configs(self):
        yaml_loader = get_yaml()
        for conffile in pathlib.Path('roles/config-wireguard/config').glob('*.yml'):
            node = conffile.stem

            print('Reading', conffile)
            self.line_to_mod_time[node] = self.expand_blame_mod_times(conffile)
            with open(conffile, encoding='utf-8') as f:
                yaml_data = yaml_loader.load(f)
                end_pos = f.tell()

            # Fetch the YAML line positions for each peering definition
            # This will be compared to the Git blame info to find the last time each peering was modified
            # Iterate in reverse as ruamel.yaml tells us the start position of a collection entry
            for wg_peer in reversed(yaml_data['wg_peers']):
                bgp_asn = wg_peer.get('bgp', {}).get('asn')
                curr_pos = wg_peer.lc.line
                if bgp_asn:
                    self.asn_to_conf_lines[(node, bgp_asn)] = range(curr_pos, end_pos)
                end_pos = curr_pos

    def get_lost_peers(self, prometheus_url, ignore_new_days=30):
        time_threshold = datetime.timedelta(days=ignore_new_days)

        prom_data = query_prometheus(prometheus_url, self.query)
        lost_peers = collections.defaultdict(set)

        for result in prom_data['result']:
            node = result['metric']['loc']
            # Convert "AS4242421080", "AS4242421081_v6" etc. to the int
            asn = int(result['metric']['name'][2:].split('_', 1)[0])

            peer_last_mod_time = max(self.line_to_mod_time[node].get(line, 0) for line in self.asn_to_conf_lines[(node, asn)])
            timestamp_datetime = datetime.datetime.fromtimestamp(peer_last_mod_time)
            time_difference = datetime.datetime.now() - timestamp_datetime
            if time_difference < time_threshold:
                print(f'  Ignoring peer {node}/{asn} added in last {ignore_new_days} days ({time_difference})')
                continue
            print(f'  Adding {node}/{asn} to the removal list')

            lost_peers[node].add(asn)
        return lost_peers

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='Prometheus URL')
    parser.add_argument('--dry-run', '-n', help='Dry run', action='store_true')
    parser.add_argument('--ignore-new-days', '-d', help='Ignore peers modified in the last X days',
                        type=int, default=30)
    parser.add_argument('--threshold', '-t', help='Threshold of inactivity for pruning peers (days)',
                        type=int, default=40)
    args = parser.parse_args()

    # cd to repo root
    rootdir = pathlib.Path(os.path.dirname(__file__)) / ".." / ".."
    os.chdir(rootdir)

    ap = Autoprune('.', threshold=args.threshold)
    lost_peers = ap.get_lost_peers(args.url, ignore_new_days=args.ignore_new_days)

    if not args.dry_run:
        for node, asns in lost_peers.items():
            remove_peer(node, [str(asn) for asn in asns])

if __name__ == '__main__':
    main()
