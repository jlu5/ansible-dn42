#!/usr/bin/env python3
import argparse
import re

import requests

LG_DEFAULT_URL = 'https://lg.highdef.network/api/'

class PingTestError(Exception):
    pass

class LookingGlassAPIError(PingTestError):
    pass

class LookingGlassTracerouteFailed(PingTestError):
    pass

_TRACE_RE = re.compile(r"(\d+\.\d+) ms")
def get_rtt(node, target, lg_api_url=LG_DEFAULT_URL, timeout=30):
    query = {
        "servers": [node],
        "type": "traceroute",
        "args": target
    }
    print(f"Checking RTT for {target} against {lg_api_url} ...")
    req = requests.post(lg_api_url, json=query, timeout=timeout)
    resp = req.json()
    if resp.get("error"):
        raise LookingGlassAPIError(f"Error from looking glass: {resp['error']}")
    traceroute_output = resp["result"][0]['data']
    print("Trace output:")
    print(traceroute_output)

    traceroute_last_line = traceroute_output.splitlines()[-1]
    latencies = _TRACE_RE.findall(traceroute_last_line)
    if not latencies:
        raise LookingGlassTracerouteFailed(
            "Trace timed out" if ' *' in traceroute_last_line else "Could not parse traceroute output")

    latencies = list(map(float, latencies))
    return sum(latencies) / len(latencies)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node', help='Node to try ping from', type=str)
    parser.add_argument('target', help='Target to ping', type=str)
    parser.add_argument('lg_api_url', help='bird-lg-go API URL', default=LG_DEFAULT_URL, nargs='?')
    parser.add_argument('-t', '--timeout', help='query timeout', default=30, nargs='?', type=float)
    args = parser.parse_args()

    latency = get_rtt(args.node, args.target, args.lg_api_url, timeout=args.timeout)
    print(f"Average latency from {args.node} to {args.target}: {latency} ms")
