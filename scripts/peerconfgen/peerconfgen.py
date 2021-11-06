#!/usr/bin/env python3
"""
Generates peer config by scraping some plain text.
"""

import argparse
import io
import ipaddress
import os
import pathlib
import re
import string

from validators import *

WGKEY_RE = re.compile(r'[0-9a-zA-Z+=/]{43}=')
ASN_RE = re.compile(r'(?:424242\d{4}|420127\d{4})\b')
#TUNNEL4_RE = re.compile(r'\b172\.2[0-9]\.[0-9]{1,3}\.[0-9]{1,3}\b')
#TUNNEL6_RE = re.compile(r'\b(fe80::[0-9a-f:]+|fd[0-9a-f]{2}:[0-9a-f:]+)\b', flags=re.I)
_IPV4_RE_STR = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
_IPV6_RE_STR = r'\b(?:[0-9a-f]{1,4}[:]{1,2})+[0-9a-f]{1,4}\b'
TUNNEL4_RE = re.compile(_IPV4_RE_STR, flags=re.I)
TUNNEL6_RE = re.compile(_IPV6_RE_STR, flags=re.I)
ENDPOINT_RE = re.compile(
    # Very loose matches for:
    r'(?:'
    # DNS domain
    r'(?:[0-9a-z-_]+\.)+[0-9a-z]+|(?:'
    # IPv4 address
    + _IPV4_RE_STR + r')|(?:'
    # IPv6 address
    + _IPV6_RE_STR + r'))'
, flags=re.I)

class PeerConfigField():
    def __init__(self, regex, validator=None):
        self.regex = regex
        self.validator = validator

    def validate(self, candidate):
        if self.validator:
            return self.validator(candidate)
        else:
            return self.regex.match(self.regex)

_ATTR_MAP = {
    'asn': PeerConfigField(ASN_RE, is_int),
    'remote': PeerConfigField(ENDPOINT_RE, is_valid_endpoint),
    'wg_pubkey': PeerConfigField(WGKEY_RE),
    'peer_v4': PeerConfigField(TUNNEL4_RE, is_valid_peer_ip),
    'peer_v6': PeerConfigField(TUNNEL6_RE, is_valid_peer_ip),
}

def scrape_peer_config(text):
    result = {}
    for attr, config_field in _ATTR_MAP.items():
        candidates = re.findall(config_field.regex, text)
        if config_field.validator:
            candidates = list(filter(config_field.validator, candidates))

        if attr == 'peer_v6':
            # Sort link-local v6 before ULA, since I use the former more often in peerings
            candidates.sort(key=lambda ip: not ip.lower().startswith('fe80::'))

        result[attr] = candidates
    return result

def main(args):
    wg_config_path = pathlib.Path("roles", "config-wireguard", "config", f"dn42-{args.node}.jlu5.com.yml")
    if not os.path.exists(wg_config_path):
        raise ValueError(f"Missing WireGuard config file {wg_config_path}")

    print("Enter peer config info followed by EOF. Copy paste some text, and I'll try to guess")
    # Read string to guess from stdin
    text = io.StringIO()
    while True:
        try:
            line = input()
            text.write(line)
            text.write("\n")
        except EOFError:
            break

    print(scrape_peer_config(text.getvalue()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node', help='Node to generate config for', type=str)
    parser.add_argument('peername', help='Short name / identifier for peer', type=str)
    parser.add_argument('port', help='Port number for remote endpoint', type=int)
    args = parser.parse_args()

    # cd to repo root
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    main(args)
