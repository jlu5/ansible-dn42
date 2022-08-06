#!/usr/bin/env python3
"""
Routestats: count BIRD route stats
"""

import collections
import json
import subprocess
import re
import sys
import time

IBGP_SUFFIX = "ibgp_"
BIRD_ROUTE_RE = re.compile(r'^([0-9a-f.:/]+)\s+unicast \[(\w+) .*?\].*\[(AS\d+)i\]')

def get_stats(table):
    n_prefixes_by_session = collections.defaultdict(int)
    total_prefixes = 0
    target_asns_by_session = collections.defaultdict(set)

    cmd = ["/usr/sbin/birdc", "show r primary table " + table]

    bird_output = subprocess.check_output(cmd).decode('utf-8')
    for line in bird_output.splitlines():
        if match := BIRD_ROUTE_RE.match(line):
            prefix, session_name, origin_asn = match.groups()
            target_asns_by_session[session_name].add(origin_asn)
            n_prefixes_by_session[session_name] += 1
            total_prefixes += 1

    return total_prefixes, n_prefixes_by_session, target_asns_by_session

def _sort(d):
    return sorted(d, key=lambda pair: pair[1], reverse=True)

def _get_igp_links(d):
    return [i for i, x in enumerate(d) if x[0].startswith(IBGP_SUFFIX)]

def main():
    n_prefixes4, stats_by_prefix4, asns4 = get_stats(table="master4")
    n_prefixes6, stats_by_prefix6, asns6 = get_stats(table="master6")
    stats_by_prefix4 = _sort(stats_by_prefix4.items())
    stats_by_prefix6 = _sort(stats_by_prefix6.items())
    asns4 = _sort([(k, len(v)) for k, v in asns4.items()])
    asns6 = _sort([(k, len(v)) for k, v in asns6.items()])

    out = json.dumps({
        "ipv4": stats_by_prefix4,
        "ipv4_igp_links": _get_igp_links(stats_by_prefix4),
        "ipv4_total": n_prefixes4,

        "ipv4_asns": asns4,
        "ipv4_asns_igp_links": _get_igp_links(stats_by_prefix4),

        "ipv6": stats_by_prefix6,
        "ipv6_igp_links": _get_igp_links(asns4),
        "ipv6_total": n_prefixes6,

        "ipv6_asns": asns6,
        "ipv6_asns_igp_links": _get_igp_links(asns6),

        "ts": int(time.time())
    })

    print(out)

if __name__ == '__main__':
    main()
