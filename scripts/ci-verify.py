#!/usr/bin/env python3
"""Validates peering configs (WireGuard & BIRD)"""
import argparse
import ipaddress
import pathlib
import re

from _common import yaml_load, VaultEncryptedDummy

MAX_IFACE_LENGTH = 15
ALLOWED_IFACE_RE = re.compile(r'^(dn42(?:[0-9a-z]{3})?|cl|igp)-([0-9a-z-]+)')
# May be a hostname, IPv4 address, or bracketed IPv6 address
ALLOWED_REMOTE_RE = re.compile(r'([a-zA-Z0-9-.]+|\[[0-9a-fA-F:]+\]):\d{1,5}')
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

def _ci_verify_peer_addr(wg_peer_config, wg_config_path, candidate):
    ifname = wg_peer_config["name"]
    try:
        candidate = ipaddress.ip_network(candidate, strict=False)
    except ValueError as e:
        raise ValidationError(
            f'Peer {ifname!r} has invalid tunnel IP {candidate!r}',
            wg_config_path) from e
    allowed_ips = ALLOWED_PEER_V4 if candidate.version == 4 else ALLOWED_PEER_V6
    if not any(candidate.subnet_of(net) for net in allowed_ips):
        raise ValidationError(
            f'Peer {ifname!r} has out of range tunnel IP {candidate}', wg_config_path)

# pylint: disable=too-many-branches, too-many-locals
def _ci_verify_wg_peer(wg_config_path, peer_config) -> str | None:
    ifname = peer_config['name']
    # Verify name
    if not ifname:
        raise ValidationError('Peer name cannot be empty', wg_config_path)
    if len(ifname) > MAX_IFACE_LENGTH:
        raise ValidationError(
            f'Peer name {ifname!r} is too long (max {MAX_IFACE_LENGTH} chars)', wg_config_path)
    ifname_match = ALLOWED_IFACE_RE.match(ifname)
    if not ifname_match:
        raise ValidationError(
            f'Peer name {ifname!r} does not match regex {ALLOWED_IFACE_RE} - '
            'only lowercase letters and digits are allowed',
            wg_config_path
        )
    ext_peer = ifname.startswith('dn42')

    # Verify cleaned up hosts (remove: true)
    if peer_config.get('remove'):
        if len(peer_config.keys()) > 2:
            raise ValidationError(
                f'Peer {ifname!r} has stray options in addition to "remove: true"', wg_config_path)
        return None

    # Verify port numbers
    if listen_port := peer_config.get('port'):
        if ext_peer and not is_allowed_port(listen_port):
            raise ValidationError(
                f'Peer {ifname!r} has unacceptable listen port {listen_port} - '
                'please use 20000 + <last 4 digits of your ASN>',
                wg_config_path)

    # Verify remote
    remote = peer_config.get('remote')
    if remote and not isinstance(remote, VaultEncryptedDummy) and not ALLOWED_REMOTE_RE.match(remote):
        raise ValidationError(
            f'Peer {ifname!r} has invalid remote (host:port) {remote!r}',
            wg_config_path)

    # Verify wg_pubkey / multi
    wg_pubkey = peer_config.get('wg_pubkey')
    wg_multi = peer_config.get('multi', [])
    if not wg_pubkey and not wg_multi:
        raise ValidationError(
            f'Peer {ifname!r} is missing wg_pubkey field', wg_config_path)
    if wg_pubkey and not WGKEY_RE.match(wg_pubkey):
        raise ValidationError(
            f'Peer {ifname!r} has invalid wg_pubkey {wg_pubkey!r}', wg_config_path)
    for multi_peer in wg_multi:
        wg_pubkey = multi_peer['wg_pubkey']
        if not WGKEY_RE.match(wg_pubkey):
            raise ValidationError(
                f'Peer {ifname!r} has invalid wg_pubkey {wg_pubkey!r}', wg_config_path)
        wg_allowedips = multi_peer['wg_allowedips']
        for wg_allowedip in wg_allowedips.split(','):
            try:
                ipaddress.ip_network(wg_allowedip)
            except ValueError as e:
                raise ValidationError(
                    f'Peer {ifname!r} has invalid wg_allowedips {wg_allowedips!r}',
                    wg_config_path) from e

    # Verify tunnel IPs
    peer_v4 = peer_config.get('peer_v4')
    peer_v6 = peer_config.get('peer_v6')
    if not peer_v4 and not peer_v6 and not wg_multi:
        raise ValidationError(
            f'Peer {ifname!r} has neither peer_v4 nor peer_v6 configured', wg_config_path)
    if peer_v4:
        _ci_verify_peer_addr(peer_config, wg_config_path, peer_v4)
    if peer_v6:
        _ci_verify_peer_addr(peer_config, wg_config_path, peer_v6)
    if local_v4 := peer_config.get('local_v4'):
        _ci_verify_peer_addr(peer_config, wg_config_path, local_v4)
    if local_v6 := peer_config.get('local_v6'):
        _ci_verify_peer_addr(peer_config, wg_config_path, local_v6)

    return ifname_match.group(2) if ext_peer else None

def _ci_verify_bird(root, rtr_name, peer_name, wg_peer_config):
    bird_config_paths = (root / 'roles' / 'config-bird2' / 'config' / 'peers' / rtr_name).glob(f'{peer_name}*.conf')
    bird_config_paths = sorted(bird_config_paths, key=lambda path: len(path.stem))
    ifname = wg_peer_config["name"]
    if not bird_config_paths:
        return False

    bird_config_path = bird_config_paths[0]
    try:
        with open(bird_config_path, encoding='utf-8') as f:
            bird_config = f.read()
    except OSError as e:
        raise ValidationError(f'Could not read BIRD peer config for {bird_config_path!r}', bird_config_path) from e

    print(f'Checking {bird_config_path}')
    neighbor_matches = BIRD_NEIGHBOR_RE.findall(bird_config)
    if not neighbor_matches:
        raise ValidationError('Could not parse any neighbor IPs from BIRD config', bird_config_path)

    allowed_peer_nets = []
    disallowed_peer_ips = []
    if peer_v4 := wg_peer_config.get('peer_v4'):
        allowed_peer_nets.append(ipaddress.ip_network(peer_v4, strict=False))
    if peer_v6 := wg_peer_config.get('peer_v6'):
        allowed_peer_nets.append(ipaddress.ip_network(peer_v6, strict=False))
    if local_v4 := wg_peer_config.get('local_v4'):
        allowed_peer_nets.append(ipaddress.ip_network(local_v4, strict=False))
        disallowed_peer_ips.append(ipaddress.ip_address(local_v4.split('/')[0]))
    if local_v6 := wg_peer_config.get('local_v6'):
        allowed_peer_nets.append(ipaddress.ip_network(local_v6, strict=False))
        disallowed_peer_ips.append(ipaddress.ip_address(local_v6.split('/')[0]))

    peer_has_llv6 = False
    for neighbor_ip, _asn in neighbor_matches:
        try:
            neighbor_ip = ipaddress.ip_address(neighbor_ip)
        except ValueError as e:
            raise ValidationError(f'BIRD config has invalid neighbor IP {neighbor_ip!r}', bird_config_path) from e
        if not any(neighbor_ip in net for net in allowed_peer_nets):
            raise ValidationError(f'BIRD neighbor IP {neighbor_ip!r} is not configured on interface (expected one of '
                                  f'{allowed_peer_nets})', bird_config_path)
        if neighbor_ip in disallowed_peer_ips:
            raise ValidationError(f'BIRD neighbor IP {neighbor_ip} is a local address {disallowed_peer_ips})',
                                  bird_config_path)
        peer_has_llv6 |= neighbor_ip in ipaddress.ip_network('fe80::/64')

    interface_matches = BIRD_INTERFACE_RE.findall(bird_config)
    if peer_has_llv6 and not interface_matches:
        raise ValidationError('BIRD config uses link-local IPv6 but no "interface" directive found', bird_config_path)
    for bird_interface in interface_matches:
        if bird_interface != ifname:
            raise ValidationError(f'BIRD config has mismatched "interface" directive {bird_interface!r}, '
                                  f'expected {ifname!r}', bird_config_path)

    is_passive_mode = BIRD_PASSIVE_RE.search(bird_config)
    if wg_peer_config['remote'] and is_passive_mode:
        raise ValidationError('When "remote" is set, passive mode should be disabled', bird_config_path)
    if not wg_peer_config['remote'] and not is_passive_mode:
        raise ValidationError('When "remote" is unset, passive mode should be enabled', bird_config_path)
    return True

def _ci_verify_bgp_auto_config(peer_config, wg_config_path):
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

    if ipv4_enabled and not (peer_config['peer_v4'] or extended_next_hop):
        raise ValidationError(f'Peer {name!r} has IPv4 enabled for BGP but no IPv4 next hop', wg_config_path)

    if ipv6_enabled and not peer_config['peer_v6']:
        raise ValidationError(f'Peer {name!r} has IPv6 enabled for BGP but no IPv6 next hop', wg_config_path)

    return True

def ci_verify(root):
    root = pathlib.Path(root)
    wg_config_dir = root / 'roles' / 'config-wireguard' / 'config'
    for wg_config_path in wg_config_dir.glob('*.yml'):
        print(f'Checking {wg_config_path}')
        wg_config = yaml_load(wg_config_path)
        for peer_config in wg_config['wg_peers']:
            external_peer_name = _ci_verify_wg_peer(wg_config_path, peer_config)

            # For external peers, verify that matching BIRD config exists
            if external_peer_name:
                rtr_name = wg_config_path.stem
                bird_config = _ci_verify_bird(root, rtr_name, external_peer_name, peer_config)
                bgp_auto_config = _ci_verify_bgp_auto_config(peer_config, wg_config_path)
                if not bird_config and not bgp_auto_config:
                    raise ValidationError(
                        f'BGP config missing for peer {external_peer_name!r}', wg_config_path)
    print('OK')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', help='root path of repository')
    args = parser.parse_args()

    ci_verify(args.root)

if __name__ == '__main__':
    main()
