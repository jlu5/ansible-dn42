#!/usr/bin/env python3
"""
Aggregate and export BIRD route stats
"""

import collections
import json
import subprocess
import re
import time

IBGP_SUFFIX = "ibgp_"
BIRD_ROUTE_RE = re.compile(r'^([0-9a-f.:/]+)\s+unicast \[(\w+) .*?\].*\[(AS\d+)i\]')
BIRD_ROUTE_BGP_PATH_RE = re.compile(r'^\s+BGP.as_path: ((?:\d+ ?)+)')

def get_stats(table):
    # number of prefixes each BGP session sends preferred paths for
    prefixes_by_session = collections.defaultdict(int)
    total_prefixes = 0
    # number of ASNs each BGP session sends preferred paths for
    target_asns_by_session = collections.defaultdict(set)
    # how many paths have AS path len X
    bgp_path_len_count = collections.defaultdict(int)

    cmd = ["/usr/sbin/birdc", "show r primary all where source = RTS_BGP table " + table]

    bird_output = subprocess.check_output(cmd).decode('utf-8')
    for line in bird_output.splitlines():
        if match := BIRD_ROUTE_RE.match(line):
            _prefix, session_name, origin_asn = match.groups()
            target_asns_by_session[session_name].add(origin_asn)
            prefixes_by_session[session_name] += 1
            total_prefixes += 1
        elif match := BIRD_ROUTE_BGP_PATH_RE.match(line):
            as_path, = match.groups()
            as_path = as_path.split()
            bgp_path_len_count[len(as_path)] += 1

    return total_prefixes, prefixes_by_session, target_asns_by_session, bgp_path_len_count

def _sort(d):
    return sorted(d, key=lambda pair: pair[1], reverse=True)

def _get_igp_links(d):
    return [i for i, x in enumerate(d) if x[0].startswith(IBGP_SUFFIX)]

def main():
    n_prefixes4, prefixes_by_session4, asns_by_session4, bgp_path_len_count4 = get_stats(table="master4")
    n_prefixes6, prefixes_by_session6, asns_by_session6, bgp_path_len_count6 = get_stats(table="master6")
    prefixes_by_session4 = _sort(prefixes_by_session4.items())
    prefixes_by_session6 = _sort(prefixes_by_session6.items())
    asns_by_session4 = _sort([(k, len(v)) for k, v in asns_by_session4.items()])
    asns_by_session6 = _sort([(k, len(v)) for k, v in asns_by_session6.items()])
    bgp_path_len_count4 = {f'len={k}': v for k, v in sorted(bgp_path_len_count4.items())}
    bgp_path_len_count6 = {f'len={k}': v for k, v in sorted(bgp_path_len_count6.items())}

    out = json.dumps({
        "ipv4": prefixes_by_session4,
        "ipv4_igp_links": _get_igp_links(prefixes_by_session4),
        "ipv4_total": n_prefixes4,
        "ipv4_path_len_for_prefix": list(bgp_path_len_count4.items()),

        "ipv4_asns": asns_by_session4,
        "ipv4_asns_igp_links": _get_igp_links(asns_by_session4),

        "ipv6": prefixes_by_session6,
        "ipv6_igp_links": _get_igp_links(prefixes_by_session6),
        "ipv6_total": n_prefixes6,
        "ipv6_path_len_for_prefix": list(bgp_path_len_count6.items()),

        "ipv6_asns": asns_by_session6,
        "ipv6_asns_igp_links": _get_igp_links(asns_by_session6),

        "ts": int(time.time())
    })

    print(out)

if __name__ == '__main__':
    main()
