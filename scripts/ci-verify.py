#!/usr/bin/env python3
"""Validates peering configs (WireGuard, GRE)"""
# pylint: disable=too-few-public-methods,too-many-branches
import argparse
import collections
from enum import Enum
import ipaddress
import pathlib
import re

from _common import yaml_load, VaultEncryptedDummy

MAX_IFACE_LENGTH = 15
ALLOWED_IFACE_RE = re.compile(r'^(dn42|cl|igp)-([0-9a-z-]+)')
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

class PeerVerifier():
    def __init__(self):
        self.seen_ifnames = collections.defaultdict(set)
        self.seen_ports = collections.defaultdict(set)

    def _check_peer_addr(self, peer_config, config_path, key, min_size=None):
        ifname = peer_config["name"]
        candidate = peer_config[key]
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
        if min_size is not None and ipnet.num_addresses < min_size:
            raise ValidationError(
                f'Peer {ifname!r} has too small {key!r}', config_path)

    def _check_peer_wg(self, config_path: pathlib.Path, peer_config, is_ext_peer: bool):
        ifname = peer_config['name']
        # Verify port numbers
        if 'port' not in peer_config:
            raise ValidationError(
                f'Peer {ifname!r} has missing "port" option', config_path)
        rtrname = config_path.stem
        if listen_port := peer_config.get('port'):
            if is_ext_peer and not is_allowed_port(listen_port):
                raise ValidationError(
                    f'Peer {ifname!r} has unacceptable listen port {listen_port} - '
                    'please use 20000 + <last 4 digits of your ASN>',
                    config_path)
            if listen_port in self.seen_ports[rtrname]:
                raise ValidationError(f'Peer {ifname!r} local port {listen_port} is already in use', config_path)
            self.seen_ports[rtrname].add(listen_port)

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

        # Verify MTU
        if wg_mtu := peer_config.get('wg_mtu'):
            if wg_mtu < 1280:
                raise ValidationError(
                    f'Peer {ifname!r} has invalid wg_mtu {wg_mtu!r}', config_path)

    def _check_peer_config(self, config_path: pathlib.Path, peer_config, peer_type: PeerType):
        """Checks a peer config block for validity."""
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
                config_path)

        rtrname = config_path.stem
        if ifname in self.seen_ifnames[rtrname]:
            raise ValidationError(f'Duplicate interface name {ifname!r}', config_path)
        self.seen_ifnames[rtrname].add(ifname)

        if peer_config.get('remove'):
            raise ValidationError(
                f'Peer {ifname!r} has deprecated "remove: true". Remove the YAML config block instead', config_path)

        wg_multi = False
        # Verify WireGuard configuration
        is_ext_peer = ifname.startswith('dn42')
        if peer_type == PeerType.WIREGUARD:
            self._check_peer_wg(config_path, peer_config, is_ext_peer)
            wg_multi = peer_config.get('multi', [])

        # Verify tunnel IPs
        peer_v4 = peer_config.get('peer_v4')
        peer_v6 = peer_config.get('peer_v6')
        local_v4 = peer_config.get('local_v4')
        local_v6 = peer_config.get('local_v6')
        if not any((peer_v4, peer_v6, local_v4, local_v6, wg_multi)):
            raise ValidationError(f'Peer {ifname!r} has no tunnel IPs configured', config_path)
        if peer_v4:
            self._check_peer_addr(peer_config, config_path, 'peer_v4')
        if peer_v6:
            self._check_peer_addr(peer_config, config_path, 'peer_v6')
        if local_v4:
            self._check_peer_addr(peer_config, config_path, 'local_v4', min_size=1 if peer_v4 else 2)
        if local_v6:
            self._check_peer_addr(peer_config, config_path, 'local_v6', min_size=1 if peer_v6 else 2)

        bgp_auto_config = self._check_bgp_auto_config(peer_config, config_path)
        if is_ext_peer and not bgp_auto_config:
            raise ValidationError(
                f'BGP config missing for peer {is_ext_peer!r}', config_path)

    def _check_bgp_auto_config(self, peer_config, wg_config_path):
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

    def run(self, root):
        root = pathlib.Path(root)
        wg_config_dir = root / 'roles' / 'config-wireguard' / 'config'
        for wg_config_path in wg_config_dir.glob('*.yml'):
            print(f'Checking {wg_config_path}')
            wg_config = yaml_load(wg_config_path)
            for peer_config in wg_config['wg_peers']:
                self._check_peer_config(wg_config_path, peer_config, PeerType.WIREGUARD)

        gre_config_dir = root / 'roles' / 'config-gre-plain' / 'config'
        for gre_config_path in gre_config_dir.glob('*.yml'):
            print(f'Checking {gre_config_path}')
            gre_config = yaml_load(gre_config_path)
            for peer_config in gre_config['gre_peers']:
                self._check_peer_config(gre_config_path, peer_config, PeerType.GRE)

        print('OK')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', help='root path of repository')
    args = parser.parse_args()

    verifier = PeerVerifier()
    verifier.run(args.root)

if __name__ == '__main__':
    main()
