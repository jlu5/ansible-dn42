#!/usr/bin/env python3
"""
Fetch BGP peer counts (up and total configured) from the bird-lg-go API.
"""
import argparse

import requests

DEFAULT_IGNORE_PREFIXES = ('ibgp_', 'burble_grc')
TIMEOUT = 5
def get_stats(api_url, ignore_prefixes=DEFAULT_IGNORE_PREFIXES):
    servers_req = requests.post(api_url, json={
        "type": "server_list",
    }, timeout=TIMEOUT).json()
    servers = [entry['server'] for entry in servers_req['result']]
    print('Got servers:', servers)

    summary_req = requests.post(api_url, json={
        "servers": servers,
        "type": "summary",
        "args": "",
    }, timeout=TIMEOUT).json()
    counts = {}
    for entry in summary_req['result']:
        count_up = count_total = 0
        server = entry['server']
        for protocol_entry in entry['data']:
            protocol_name = protocol_entry['name']
            if protocol_entry['proto'] == 'BGP' and not protocol_name.startswith(ignore_prefixes):
                count_total += 1
                if protocol_entry['state'] == 'up':
                    count_up += 1
                else:
                    print(f'{server}: peer {protocol_name} is DOWN since {protocol_entry["since"]}')
        counts[server] = (count_up, count_total)
    return counts

DEFAULT_API_URL = 'http://lg.highdef.dn42/api/'
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('api_url', help='bird-lg-go API URL', nargs='?', default=DEFAULT_API_URL)
    # TODO add ignore_prefixes as a CLI option
    args = parser.parse_args()

    stats = get_stats(args.api_url)
    print('\nAggregate stats:')
    for server, (count_up, count_total) in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        try:
            pct = count_up / count_total
        except ZeroDivisionError:
            pct = 0
        print(f'{server}: {count_up}/{count_total} peers up ({pct:.2%})')

if __name__ == '__main__':
    main()
