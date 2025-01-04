#!/usr/bin/env python3
"""Validates peering configs (WireGuard & BIRD)"""
import argparse
import collections
from enum import Enum
import ipaddress
import pathlib
import re

from _common import yaml_load, VaultEncryptedDummy

MAX_IFACE_LENGTH = 15
ALLOWED_IFACE_RE = re.compile(r'^(dn42(?:[0-9a-z]{3})?|cl|igp)-([0-9a-z-]+)')
# May be a hostname, IPv4 address, or IPv6 address (bracketed or not)
ALLOWED_REMOTE_RE = re.compile(r'([a-zA-Z0-9-.]+|\[[0-9a-fA-F:]+\]|[0-9a-fA-F:]+):\d{1,5}')
WGKEY_RE = re.compile(r'[0-9a-zA-Z+/]{43}=')
BIRD_NEIGHBOR_RE = re.compile(r'neighbor\s+([0-9a-fA-F:]+|[0-9.]+)\s+as\s+(\d+)')
BIRD_INTERFACE_RE = re.compile(r'interface\s+"(.*?)"')
BIRD_PASSIVE_RE = re.compile(r'passive\s+on')

ALLOWED_PEER_V4 = [
    # link-local v4
    ipaddress.IPv4Network('169.254.0.0/16'),
    # dn42 space
    ipaddress.IPv4Network('172.20.0.0/14'),
    # neonetwork space
    ipaddress.IPv4Network('10.127.0.0/16'),
]
ALLOWED_PEER_V6 = [
    ipaddress.IPv6Network('fd00::/8'),
    ipaddress.IPv6Network('fe80::/64'), # NOT fe80::/10
]
# These are legal but confusing because I use them as IGP tunnel IPs
DISALLOWED_PEER_V6 = [
    ipaddress.IPv6Network('fe80::1080'),
    ipaddress.IPv6Network('fe80::1080:0/112'),
]

class PeerType(Enum):
    GRE = 0
    WIREGUARD = 1

class ValidationError(Exception):
    def __init__(self, message, filename):
        if filename:
            message += f' ({filename})'
        super().__init__(message)
        self.filename = filename

def is_allowed_port(port):
    return (
        # new peerings
        (20000 <= port <= 29999) or
        # legacy peerings
        (50000 <= port <= 59999)
    ) and port != 21080 # reserved

def _check_peer_addr(peer_config, config_path, candidate):
    ifname = peer_config["name"]
    try:
        ipnet = ipaddress.ip_network(candidate, strict=False)
    except ValueError as e:
        raise ValidationError(
            f'Peer {ifname!r} has invalid tunnel IP {candidate!r}',
            config_path) from e
    allowed_ips = ALLOWED_PEER_V4 if ipnet.version == 4 else ALLOWED_PEER_V6
    if not any(ipnet.subnet_of(net) for net in allowed_ips):
        raise ValidationError(
            f'Peer {ifname!r} has out of range tunnel IP {ipnet}', config_path)

# pylint: disable=too-many-branches, too-many-locals
def _check_peer_config(config_path, peer_config, peer_type) -> str | None:
    """Checks a peer config block for validity"""
    ifname = peer_config['name']
    # Verify name
    if not ifname:
        raise ValidationError('Peer name cannot be empty', config_path)
    if len(ifname) > MAX_IFACE_LENGTH:
        raise ValidationError(
            f'Peer name {ifname!r} is too long (max {MAX_IFACE_LENGTH} chars)', config_path)
    ifname_match = ALLOWED_IFACE_RE.match(ifname)
    if not ifname_match:
        raise ValidationError(
            f'Peer name {ifname!r} does not match regex {ALLOWED_IFACE_RE} - '
            'only lowercase letters and digits are allowed',
            config_path
        )
    ext_peer = ifname.startswith('dn42')

    # Verify cleaned up hosts (remove: true)
    if peer_config.get('remove'):
        if len(peer_config.keys()) > 2:
            raise ValidationError(
                f'Peer {ifname!r} has stray options in addition to "remove: true"', config_path)
        return None  # Skip remaining checks

    wg_multi = False
    if peer_type == PeerType.WIREGUARD:
        # Verify port numbers
        if 'port' not in peer_config:
            raise ValidationError(
                f'Peer {ifname!r} has missing "port" option', config_path)
        if listen_port := peer_config.get('port'):
            if ext_peer and not is_allowed_port(listen_port):
                raise ValidationError(
                    f'Peer {ifname!r} has unacceptable listen port {listen_port} - '
                    'please use 20000 + <last 4 digits of your ASN>',
                    config_path)

        # Verify remote
        remote = peer_config.get('remote')
        if remote and not isinstance(remote, VaultEncryptedDummy) and not ALLOWED_REMOTE_RE.match(remote):
            raise ValidationError(
                f'Peer {ifname!r} has invalid remote (host:port) {remote!r}',
                config_path)

        # Verify wg_pubkey / multi
        wg_pubkey = peer_config.get('wg_pubkey')
        wg_multi = peer_config.get('multi', [])
        if not wg_pubkey and not wg_multi:
            raise ValidationError(
                f'Peer {ifname!r} is missing wg_pubkey field', config_path)
        if wg_pubkey and not WGKEY_RE.match(wg_pubkey):
            raise ValidationError(
                f'Peer {ifname!r} has invalid wg_pubkey {wg_pubkey!r}', config_path)
        for multi_peer in wg_multi:
            wg_pubkey = multi_peer['wg_pubkey']
            if not WGKEY_RE.match(wg_pubkey):
                raise ValidationError(
                    f'Peer {ifname!r} has invalid wg_pubkey {wg_pubkey!r}', config_path)
            wg_allowedips = multi_peer['wg_allowedips']
            for wg_allowedip in wg_allowedips.split(','):
                try:
                    ipaddress.ip_network(wg_allowedip)
                except ValueError as e:
                    raise ValidationError(
                        f'Peer {ifname!r} has invalid wg_allowedips {wg_allowedips!r}',
                        config_path) from e

    # Verify tunnel IPs
    peer_v4 = peer_config.get('peer_v4')
    peer_v6 = peer_config.get('peer_v6')
    local_v4 = peer_config.get('local_v4')
    local_v6 = peer_config.get('local_v6')
    if not any((peer_v4, peer_v6, local_v4, local_v6, wg_multi)):
        raise ValidationError(f'Peer {ifname!r} has no tunnel IPs configured', config_path)
    if peer_v4:
        _check_peer_addr(peer_config, config_path, peer_v4)
    if peer_v6:
        _check_peer_addr(peer_config, config_path, peer_v6)
    if local_v4:
        _check_peer_addr(peer_config, config_path, local_v4)
    if local_v6:
        _check_peer_addr(peer_config, config_path, local_v6)

    return ifname_match.group(2) if ext_peer else None

def _find_bird_config(root, rtr_name, peer_name):
    bird_config_paths = (root / 'roles' / 'config-bird2' / 'config' / 'peers' / rtr_name).glob(f'{peer_name}*.conf')
    bird_config_paths = sorted(bird_config_paths, key=lambda path: len(path.stem))
    if not bird_config_paths:
        return False

    return bird_config_paths[0]

def _check_bgp_auto_config(peer_config, wg_config_path):
    """Checks a peer BGP config block for validity"""
    bgp_config = peer_config.get('bgp')
    name = peer_config['name']
    if not bgp_config:
        return False
    asn = bgp_config.get('asn')
    if not isinstance(asn, int):
        raise ValidationError(f'Peer {name!r} has invalid ASN {asn!r}', wg_config_path)

    if 'ipv4' not in bgp_config:
        raise ValidationError(f'Peer {name!r} is missing required "bgp.ipv4" attribute', wg_config_path)
    if 'ipv6' not in bgp_config:
        raise ValidationError(f'Peer {name!r} is missing required "bgp.ipv6" attribute', wg_config_path)
    ipv4_enabled = bgp_config['ipv4']
    ipv6_enabled = bgp_config['ipv6']
    if not ipv4_enabled and not ipv6_enabled:
        raise ValidationError(f'Peer {name!r} has neither IPv4 nor IPv6 enabled', wg_config_path)

    mp_bgp = bgp_config.get('mp_bgp')
    extended_next_hop = bgp_config.get('extended_next_hop')

    if extended_next_hop and not mp_bgp:
        raise ValidationError(f'Peer {name!r} has extended next hop enabled but MP-BGP disabled', wg_config_path)

    if mp_bgp and not (ipv4_enabled and ipv6_enabled):
        raise ValidationError(f'Peer {name!r} has MP-BGP enabled but either IPv4 or IPv6 is disabled', wg_config_path)

    if ipv4_enabled and not (peer_config.get('peer_v4') or extended_next_hop or peer_config.get('local_v4')):
        raise ValidationError(f'Peer {name!r} has IPv4 enabled for BGP but no IPv4 next hop', wg_config_path)

    if ipv6_enabled and not (peer_config.get('peer_v6') or peer_config.get('local_v6')):
        raise ValidationError(f'Peer {name!r} has IPv6 enabled for BGP but no IPv6 next hop', wg_config_path)

    return True

def _check_peer(root, config_path, peer_config, peer_type, seen_peers):
    external_peer_name = _check_peer_config(config_path, peer_config, peer_type)
    # For external peers, verify that matching BIRD config exists
    if external_peer_name:
        if external_peer_name in seen_peers:
            raise ValidationError(f'Duplicate peer configuration for {external_peer_name!r}', config_path)
        seen_peers.add(external_peer_name)
        rtr_name = config_path.stem
        bird_config = _find_bird_config(root, rtr_name, external_peer_name)
        bgp_auto_config = _check_bgp_auto_config(peer_config, config_path)
        if not bird_config and not bgp_auto_config:
            raise ValidationError(
                f'BGP config missing for peer {external_peer_name!r}', config_path)
        if bird_config and bgp_auto_config:
            raise ValidationError(
                f'Duplicate BGP config for peer {external_peer_name!r}', bird_config)

def ci_verify(root):
    root = pathlib.Path(root)
    wg_config_dir = root / 'roles' / 'config-wireguard' / 'config'
    seen_peers = collections.defaultdict(set)
    for wg_config_path in wg_config_dir.glob('*.yml'):
        print(f'Checking {wg_config_path}')
        wg_config = yaml_load(wg_config_path)
        for peer_config in wg_config['wg_peers']:
            _check_peer(root, wg_config_path, peer_config, PeerType.WIREGUARD, seen_peers[wg_config_path.stem])

    gre_config_dir = root / 'roles' / 'config-gre-plain' / 'config'
    for gre_config_path in gre_config_dir.glob('*.yml'):
        print(f'Checking {gre_config_path}')
        gre_config = yaml_load(gre_config_path)
        for peer_config in gre_config['gre_peers']:
            _check_peer(root, gre_config_path, peer_config, PeerType.GRE, seen_peers[gre_config_path.stem])

    print('OK')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', help='root path of repository')
    args = parser.parse_args()

    ci_verify(args.root)

if __name__ == '__main__':
    main()
