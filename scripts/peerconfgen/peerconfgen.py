#!/usr/bin/env python3
"""
Interactively generate peering configs (WireGuard+BIRD) by scraping plain text node info and autofilling as many fields as possible.
"""

import argparse
import io
import os
import pathlib
import re
import ruamel.yaml

from birdoptions import fill_bird_options
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
    # DNS domain (as a rough heuristic, require the TLD to have >= 2 characters and begin with a letter)
    r'(?:[0-9a-z-_]+\.)+[a-z][0-9a-z]+|(?:'
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

def get_config_paths(node, create=False):
    wg_config_path = pathlib.Path("roles", "config-wireguard", "config", f"{node}.yml")

    if not os.path.exists(wg_config_path):
        if not create:
            raise OSError(f"Unknown node {node}: {wg_config_path} does not exist")
        print(f'Creating new WireGuard config {wg_config_path}')
        with open(wg_config_path, 'w', encoding='utf8') as _:
            pass  # write an empty file

    return wg_config_path

def _run_interactive(node):
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
    bird_options = fill_bird_options(node, completed_config)
    print("BIRD peering options:", bird_options)
    return completed_config, bird_options

def _get_yaml_loader():
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    # preserve explicit null values https://stackoverflow.com/a/44314840
    yaml.representer.add_representer(type(None), lambda self, data: self.represent_scalar('tag:yaml.org,2002:null', 'null'))
    return yaml

def get_iface_name(peername):
    return f'dn42-{peername[:10]}'

def gen_peer_config(peername, completed_config, bird_options, mtu=None):
    """
    Generates a YAML wg_peers config entry.
    """
    if completed_config['remote']:
        remote = completed_config['remote'] + ':' + completed_config['port']
    else:
        remote = None

    peer_v4 = completed_config['peer_v4']
    peer_v6 = completed_config['peer_v6']
    result = {
        'name': get_iface_name(peername),
        # 20000 + last 4 digits of ASN
        'port': 20000 + int(completed_config['asn']) % 10000,
        'remote': remote,
        'wg_pubkey': completed_config['wg_pubkey'],
        'peer_v4': peer_v4,
        'peer_v6': peer_v6,
        'bgp': {
            'asn': int(completed_config['asn']),
            'ipv4': bool(peer_v4) or bird_options.extended_next_hop,
            'ipv6': bool(peer_v6),
            'mp_bgp': bird_options.mp_bgp or bird_options.extended_next_hop,
            'extended_next_hop': bird_options.extended_next_hop,
        }
    }
    if mtu:
        result['wg_mtu'] = int(mtu)
    return result

_PEERNAME_RE = re.compile(r'^[a-z0-9]+$')
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', '-n', help='Only print generated output; do not write it to disk', action='store_true')
    parser.add_argument('--replace', '-r', help='Overwrite existing config blocks', action='store_true')
    parser.add_argument('--create', '-c', help="Create WireGuard config file if it doesn't exist", action='store_true')
    parser.add_argument('--mtu', '-m', help="Override WireGuard tunnel MTU", type=int, default=None)
    parser.add_argument('node', help='Node to generate config for', type=str)
    parser.add_argument('peername', help='Short name / identifier for peer', type=str)
    args = parser.parse_args()

    # cd to repo root
    rootdir = pathlib.Path(os.path.dirname(__file__)) / ".." / ".."
    os.chdir(rootdir)

    peername = args.peername.lower()
    if not _PEERNAME_RE.match(peername):
        raise ValueError(f"Peer name {peername!r} should only contain ASCII letters and numbers")

    wg_config_path = get_config_paths(args.node, create=args.create)

    yaml = _get_yaml_loader()
    with open(wg_config_path, 'r+', encoding='utf-8') as f:
        wg_config = yaml.load(f) or {}

        wg_peers = ruamel.yaml.comments.CommentedSeq(wg_config.get('wg_peers', []))
        iface_name = get_iface_name(peername)
        for iface_idx, wg_peer in enumerate(wg_peers):
            if wg_peer['name'] == iface_name:
                if not args.replace:
                    raise ValueError(f"A WireGuard config block for {iface_name!r} already exists")
                print(f"Overwriting existing WireGuard config for {iface_name!r}")
                break
        else:
            iface_idx = -1

        completed_config, bird_options = _run_interactive(args.node)
        wg_config_snippet = gen_peer_config(peername, completed_config, bird_options, mtu=args.mtu)
        if iface_idx < 0:
            wg_peers.append(wg_config_snippet)
            # Add an extra newline before the config block for readability
            # https://stackoverflow.com/questions/69376943/how-can-i-insert-linebreak-in-yaml-with-ruamel-yaml
            wg_peers.yaml_set_comment_before_after_key(len(wg_peers)-1, before='\n')
        else:
            wg_peers[iface_idx] = wg_config_snippet
            wg_peers.yaml_set_comment_before_after_key(iface_idx+1, before='\n')
        wg_config['wg_peers'] = wg_peers

        print()
        print("WireGuard config:")
        print(wg_config_snippet)
        print()
        if not args.dry_run:
            f.seek(0)
            yaml.dump(wg_config, f)
            f.truncate()

    print()

if __name__ == '__main__':
    main()
