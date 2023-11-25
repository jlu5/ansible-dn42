#!/usr/bin/env python3
import argparse
import re
import urllib.parse

import requests

class PingTestError(Exception):
    pass

_PING_RE = re.compile(r"rtt min/avg/max/mdev = (?P<minrtt>[0-9.]+)/(?P<avgrtt>[0-9.]+)/(?P<maxrtt>[0-9.]+)/(?P<mdev>[0-9.]+) ms")
def get_rtt(api_url, target, timeout=30):
    """Get RTT from a webtrace instance"""
    url = f'{api_url}/ping?' + urllib.parse.urlencode({'target': target})
    print(f"Checking RTT for {target} using URL {url} ...")
    session = requests.Session()
    lastline = None
    with session.get(url, stream=True, timeout=timeout) as resp:
        for line in resp.iter_lines(decode_unicode=True):
            if line:
                print(line)
                lastline = line
    if not lastline:
        raise PingTestError("No data received from remote")
    match = _PING_RE.match(lastline)
    if not match:
        raise PingTestError(f"Could not read latency from {lastline!r}")
    return match.group('avgrtt')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('api_url', help='webtrace API URL (e.g. https://sea.peer.highdef.network/webtrace/)')
    parser.add_argument('target', help='Target to ping', type=str)
    parser.add_argument('-t', '--timeout', help='query timeout', default=30, nargs='?', type=float)
    args = parser.parse_args()

    latency = get_rtt(args.api_url, args.target, timeout=args.timeout)
    print(f"\nAverage latency from {args.api_url} to {args.target}: {latency} ms")
