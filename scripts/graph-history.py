#!/usr/bin/env python3
# Graph the growth of my network over time!
import json
import os
import logging
import pathlib

import git
import matplotlib.pyplot as plt
import yaml

# Stub to ignore ansible-vault values
yaml.SafeLoader.add_multi_constructor('!vault', lambda *args: None)

# Make svg output deterministic, https://stackoverflow.com/questions/48107855/
plt.rcParams['svg.hashsalt'] = "424242"

def graph(times, n_ebgp_routers, n_ebgp_peerings, output="history.svg"):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(times, n_ebgp_routers, label="# routers", alpha=0.8)
    ax.plot(times, n_ebgp_peerings, label="# BGP sessions", alpha=0.8)
    for col in (n_ebgp_routers, n_ebgp_peerings):
        # Annotate the current value for each point (first in the results lists)
        print(f"Annotating point ({times[0]}, {col[0]})")
        plt.annotate(col[0], (times[0], col[0]))
    plt.title("WireGuard peers over time")
    plt.xlabel("Date")
    plt.grid(alpha=0.6)

    plt.ylabel("Count")
    plt.legend()
    plt.savefig(
        output,
        # Use smaller margins
        bbox_inches='tight',
        # Disable date embed for deterministic file output
        metadata={'Date': None}
    )
    print(f"Saved to {output}")

class HistoryFetcher():
    def __init__(self):
        self.history_cache = {}
        repo_path = pathlib.Path(__file__).resolve().parent.parent

        self.history_cache_path = repo_path / 'history.db'
        if os.path.exists(self.history_cache_path):
            with open(self.history_cache_path, 'r', encoding='utf-8') as f:
                self.history_cache = json.load(f)

        self.repo = git.Repo(repo_path)
        self.stats = None

    def _count_peers(self, commit, router_config):
        key = f'{commit}:{router_config.path}'
        if key in self.history_cache:
            return self.history_cache[key]
        router_config_data = self.repo.git.show(key)

        data = yaml.safe_load(router_config_data)
        n_peers = len([peer for peer in data.get('wg_peers', [])
                       if peer.get('name', '').startswith('dn42') and not
                       peer.get('remove')])
        logging.debug("Read %d peers from %s", n_peers, key)
        self.history_cache[key] = n_peers
        return n_peers

    def read_stats(self):
        assert not self.repo.bare

        times = []
        timeline_ebgp_routers = []
        timeline_ebgp_peerings = []
        # For each commit in the repo(!), count the number of routers &peer  interfaces that were defined there
        for commit in self.repo.iter_commits():
            try:
                wg_config_dir = commit.tree / 'roles' / 'config-wireguard' / 'config'
            except KeyError:
                logging.info("Skipping commit %s that has no peers folder", commit)
                continue
            router_configs = [blob for blob in wg_config_dir.blobs if os.path.splitext(blob.name)[1].lower() == '.yml']
            timeline_ebgp_routers.append(len(router_configs))
            n_ebgp_peerings = 0
            for router_config in router_configs:
                n_ebgp_peerings += self._count_peers(commit, router_config)
            timeline_ebgp_peerings.append(n_ebgp_peerings)

            times.append(commit.authored_datetime)
        return (times, timeline_ebgp_routers, timeline_ebgp_peerings)

    def save_cache(self):
        tmp_path =  self.history_cache_path.parent / (self.history_cache_path.name + '.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.history_cache, f)
        os.rename(tmp_path, self.history_cache_path)

def main():
    logging.basicConfig(level=logging.DEBUG)

    hist = HistoryFetcher()
    data = hist.read_stats()
    hist.save_cache()
    graph(*data)

if __name__ == '__main__':
    main()

