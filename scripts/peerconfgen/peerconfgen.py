#!/usr/bin/env python3
"""
Interactively generate peering configs (WireGuard+BIRD) by scraping plain text node info and autofilling as many fields as possible.
"""

import argparse
import io
import os
import pathlib
import re
import yaml

from birdoptions import fill_bird_options
from exporters import gen_wg_config, gen_bird_peer_config
from utils import *
from validators import *

WGKEY_RE = re.compile(r'[0-9a-zA-Z+/]{43}=')
ASN_RE = re.compile(r'(?:424242\d{4}|420127\d{4})\b')
_IPV4_RE_STR = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
_IPV6_RE_STR = r'\b(?:[0-9a-f]{1,4}[:]{1,2})+[0-9a-f]{1,4}\b'
TUNNEL4_RE = re.compile(_IPV4_RE_STR, flags=re.I)
TUNNEL6_RE = re.compile(_IPV6_RE_STR, flags=re.I)

# This guesses ports in a high range (>= 20000) that are not multiples of 10000
# (commonly listed on peering pages are strings like "20000 + last 4 ASN digits")
# The left word boundary may be whitespace or a ":"
WG_PORT_RE = re.compile(r'(?<=:|\s)[2-5](?!0000)[0-9]{4}\b')

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
    def __init__(self, name, desc, regex=None, validator=None, optional=False):
        self.name = name
        self.optional = optional
        self.desc = desc
        self.regex = regex
        self.validator = validator

    def validate(self, candidate):
        if self.validator:
            return self.validator(candidate)
        elif self.regex:
            return self.regex.match(candidate)
        else:
            raise ValueError(f"No validator specified for config field {self.name}")

_ATTR_MAP = {
    'asn': PeerConfigField('asn', 'Peer ASN', ASN_RE, is_int),
    'remote': PeerConfigField('remote', 'Remote endpoint (IP/host only)', ENDPOINT_RE, is_valid_endpoint, optional=True),
    # No regex for port: it's always filled in manually
    'port': PeerConfigField('port', 'Remote VPN port', WG_PORT_RE, is_port),
    'wg_pubkey': PeerConfigField('wg_pubkey', 'WireGuard public key', WGKEY_RE),
    'peer_v4': PeerConfigField('peer_v4', 'Tunnel IPv4 address', TUNNEL4_RE, is_valid_peer_v4, optional=True),
    'peer_v6': PeerConfigField('peer_v6', 'Tunnel IPv6 address', TUNNEL6_RE, is_valid_peer_v6, optional=True),
}

def scrape_peer_config(text):
    result = {}
    for attr, config_field in _ATTR_MAP.items():
        if not config_field.regex:  # Manual only fields
            continue
        candidates = re.findall(config_field.regex, text)
        if config_field.validator:
            candidates = list(filter(config_field.validator, candidates))

        if attr == 'peer_v6':
            # Sort link-local v6 before ULA, since I use the former more often in peerings
            candidates.sort(key=lambda ip: not ip.lower().startswith('fe80::'))

        result[attr] = candidates
    return result

def _confirm_scrape_results(scrape_results, config_field):
    for attr_candidate in scrape_results.get(config_field.name, []):
        tries = 0
        while tries < MAX_PROMPT_TRIES:
            accepted = prompt_bool(f"Guess for {config_field.desc} [{config_field.name}]: {attr_candidate}\tAccept?")
            if accepted is True:
                print(f"Set {config_field.desc} [{config_field.name}] to {attr_candidate}")
                return attr_candidate
            elif accepted is False:
                break  # break out of the while, move to next loop elem
            else:
                print("Bad input:")
                tries += 1
    return None

def complete_peer_config(scrape_results):
    result = {}
    for attr, config_field in _ATTR_MAP.items():
        # Special case: (remote) port is only relevant if remote is set
        if attr == 'port' and not result.get('remote'):
            result['port'] = None
            continue
        prompt = f"Please input the {config_field.desc} [{config_field.name}]"
        if config_field.optional:
            prompt += ", or leave blank to skip: "
        else:
            prompt += ": "

        value = _confirm_scrape_results(scrape_results, config_field)
        if not value:  # Out of guesses
            tries = 0
            while True:
                if tries >= MAX_PROMPT_TRIES:  # So tests don't crash here
                    raise ValueError(f"Too many failed tries for field {config_field.name}, aborting")
                tries += 1
                value = input(prompt)
                if value == '':
                    value = None  # Save empty values as null for YAML export
                if (value is None and config_field.optional) or (value and config_field.validate(value)):
                    print(f"Set {config_field.desc} [{config_field.name}] to {value}")
                    break
                print(f"Invalid input: {value}")
        result[attr] = value
    if not (result['peer_v4'] or result['peer_v6']):
        raise ValueError("Need either peer_v4 or peer_v6 for peers")
    return result

def main(args):
    wg_config_path = pathlib.Path("roles", "config-wireguard", "config", f"dn42-{args.node}.jlu5.com.yml")
    bird_config_dir = pathlib.Path("roles", "config-bird2", "config", "peers", f"dn42-{args.node}.jlu5.com")
    if not os.path.exists(wg_config_path):
        raise ValueError(f"Missing WireGuard config file {wg_config_path}")
    if not os.path.isdir(bird_config_dir):
        raise ValueError(f"Missing BIRD config dir {bird_config_dir}")

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

    scrape_results = scrape_peer_config(text.getvalue())
    completed_config = complete_peer_config(scrape_results)
    print("Config so far:", completed_config)
    bird_options = fill_bird_options(args.node, completed_config)
    print("BIRD peering options:", bird_options)

    wg_config = gen_wg_config(args.peername, completed_config)
    bird_peer_config = gen_bird_peer_config(args.peername, completed_config, bird_options)

    yaml_str = yaml.dump({'wg_peers': [wg_config]}, indent=2)
    # Chop off the first line for appending to the file. PyYAML doesn't support loading comments
    # so a round trip is lossy, and I don't want to depend on multiple yaml libs in one project
    yaml_str = '\n'.join(yaml_str.splitlines()[1:])
    print()
    print("WireGuard config:")
    print(yaml_str)
    print()
    if not args.dry_run:
        with open(wg_config_path, 'a') as f:
            count = 0
            count += f.write('\n')
            count += f.write(yaml_str)
            count += f.write('\n')
            print(f"Wrote {count} bytes to {wg_config_path}")

    bird_config_path = bird_config_dir / f'{args.peername}.conf'
    print()
    print("BIRD peer config:")
    print(bird_peer_config)
    print()
    if not args.dry_run:
        with open(bird_config_path, 'w') as f:
            count = f.write(bird_peer_config)
            print(f"Wrote {count} bytes to {bird_config_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', help='Only print generated output; do not write it to disk', action='store_true')
    parser.add_argument('node', help='Node to generate config for', type=str)
    parser.add_argument('peername', help='Short name / identifier for peer', type=str)
    args = parser.parse_args()

    # cd to repo root
    rootdir = pathlib.Path(os.path.dirname(__file__)) / ".." / ".."
    #print('cd to', rootdir)
    os.chdir(rootdir)
    main(args)
