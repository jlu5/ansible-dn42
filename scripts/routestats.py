#!/usr/bin/env python3
"""
Routestats: count BIRD route stats
"""

import json
import subprocess
import re
import sys
import time

BIRD_PROTO_RE = re.compile(r'^(\w+?)\s+(\w+)')
BIRD_ROUTE_COUNT_RE = re.compile(r'\s+Routes:\s+(\d+) imported, (\d+) exported, (\d+) preferred')
IBGP_SUFFIX = "ibgp_"

def get_stats():
    stats4 = {}
    stats6 = {}
    total4 = total6 = 0

    cmd = ["/usr/sbin/birdc", "show pr all"]

    bird_output = subprocess.check_output(cmd).decode('utf-8')

    curr_session = None
    found_v4_header = found_v6_header = False
    for line in bird_output.splitlines():
        if match := BIRD_PROTO_RE.match(line):
            curr_session, protocol = match.groups()
            found_v4_header = found_v6_header = False
            if protocol != 'BGP':
                curr_session = None
                continue
            print(f"Checking session {curr_session}, type {protocol}", file=sys.stderr)

        if curr_session:
            if line.lstrip() == 'Channel ipv4':
                found_v4_header = True
                continue
            if line.lstrip() == 'Channel ipv6':
                found_v4_header = False  # ipv6 always comes after
                found_v6_header = True
                continue
            if match := BIRD_ROUTE_COUNT_RE.match(line):
                n_imported, n_exported, n_preferred = map(int, match.groups())
                assert found_v4_header ^ found_v6_header
                if found_v4_header:
                    total4 += n_preferred
                    stats4[curr_session] = n_preferred
                    found_v4_header = False
                    print(f"  Using {n_preferred}/{n_imported} IPv4 routes from {curr_session}", file=sys.stderr)
                elif found_v6_header:
                    total6 += n_preferred
                    stats6[curr_session] = n_preferred
                    found_v6_header = False
                    print(f"  Using {n_preferred}/{n_imported} IPv6 routes from {curr_session}", file=sys.stderr)

    return total4, stats4, total6, stats6

total4, stats4, total6, stats6 = get_stats()
stats4 = sorted(stats4.items(), key=lambda pair: pair[1], reverse=True)
stats6 = sorted(stats6.items(), key=lambda pair: pair[1], reverse=True)

out = json.dumps({
    "ipv4": stats4,
    "ipv4_igp_links": [i for i, x in enumerate(stats4) if x[0].startswith(IBGP_SUFFIX)],
    "ipv4_total": total4,
    "ipv6": stats6,
    "ipv6_igp_links": [i for i, x in enumerate(stats6) if x[0].startswith(IBGP_SUFFIX)],
    "ipv6_total": total6,
    "ts": int(time.time())
})

print(out)
