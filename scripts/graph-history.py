#!/usr/bin/env python3
# Graph the growth of my my network over time!

import itertools
import os
import logging

import git
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Make svg output deterministic, https://stackoverflow.com/questions/48107855/
plt.rcParams['svg.hashsalt'] = "424242"

def graph(times, n_ebgp_routers, n_ebgp_peerings, n_ebgp_unique, output="history.svg"):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(times, n_ebgp_routers, label="eBGP routers", alpha=0.8)
    ax.plot(times, n_ebgp_peerings, label="total eBGP sessions", alpha=0.8)
    ax.plot(times, n_ebgp_unique, label="unique eBGP peers", alpha=0.8)
    for col in (n_ebgp_routers, n_ebgp_peerings, n_ebgp_unique):
        # Annotate the current value for each point (first in the results lists)
        print(f"Annotating point ({times[0]}, {col[0]})")
        plt.annotate(col[0], (times[0], col[0]))
    plt.title("Peers over time")
    plt.xlabel("Date")
    plt.grid(alpha=0.6)

    #ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    fig.autofmt_xdate()

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

def _read_git():
    repo = git.Repo('.')
    assert not repo.bare

    times = []
    n_ebgp_routers = []
    n_ebgp_peerings = []
    n_ebgp_unique = []
    # For each commit in the repo(!), count the number of eBGP routers & links that were defined there
    for commit in repo.iter_commits():
        # In my repo, I store peer info in the following format:
        # roles/config-bird2/config/peers/<eBGP router name>/<peer name>.conf
        try:
            peers_dir = commit.tree / 'roles' / 'config-bird2' / 'config' / 'peers'
        except KeyError:
            logging.info(f"Skipping commit {commit} that has no peers folder")
            continue
        all_blobs = itertools.chain.from_iterable(t.blobs for t in peers_dir.trees)
        all_filenames = [file.name for file in all_blobs]

        times.append(commit.authored_datetime)
        ebgp_routers = list(filter(lambda subtree: subtree.name.startswith('dn42-'), peers_dir))
        n_ebgp_routers.append(len(ebgp_routers))
        n_ebgp_peerings.append(len(all_filenames))
        # Number of unique filenames = number of unique peers
        n_ebgp_unique.append(len(set(all_filenames)))

    return (times, n_ebgp_routers, n_ebgp_peerings, n_ebgp_unique)

if __name__ == '__main__':
    logging.basicConfig()

    data = _read_git()
    graph(*data)

