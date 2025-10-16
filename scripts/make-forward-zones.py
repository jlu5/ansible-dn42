#!/usr/bin/env python3
"""
Generate forward-zones and dnssec config for pdns-recursor.
"""

import argparse
import collections
import dataclasses
import ipaddress
import logging
import pathlib

import yaml

_CLEARNET_DNS_SERVERS=['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4']
_SYSTEM_ROOT_DS = '/usr/share/dns/root.ds'

@dataclasses.dataclass
class RegistryDNSEntry:
    nameservers: list[str]
    trust_anchors: list[str]

_PTR_ZONES = [
    ('10.0.0.0/8', '10.in-addr.arpa'),
    ('172.20.0.0/16', '20.172.in-addr.arpa'),
    ('172.21.0.0/16', '21.172.in-addr.arpa'),
    ('172.22.0.0/16', '22.172.in-addr.arpa'),
    ('172.23.0.0/16', '20.172.in-addr.arpa'),
    ('172.31.0.0/16', '31.172.in-addr.arpa'),
    ('fd00::/8', 'd.f.ip6.arpa'),
]

class ForwardZonesGenerator():
    def __init__(self, registry_path: str):
        self.registry_path = pathlib.Path(registry_path)

        self._seen_nameservers = collections.defaultdict(set)

        # Populate _seen_nameservers with delegation-servers IPs
        dn42_delegation_servers = self._read_registry_dns_entry('delegation-servers.dn42',
            self.registry_path / 'data' / 'dns' / 'delegation-servers.dn42')
        assert dn42_delegation_servers.nameservers

        self.conf = {}

    @staticmethod
    def _read_system_ds() -> list[str]:
        """Return a list of DS records for the root zone (.)"""
        result = []
        prefix = '. IN DS '
        with open(_SYSTEM_ROOT_DS, encoding='utf8') as f:
            for line in f.readlines():
                line = line.strip()
                assert line.startswith(prefix), f'Invalid DS string {line}'
                result.append(line[len(prefix):])
        return result

    def _read_registry_dns_entry(self, zone: str, path: pathlib.Path) -> RegistryDNSEntry:
        """Return a list of nameservers and DS records (when available) from a dn42 registry DNS entry"""
        result = RegistryDNSEntry([], [])

        with open(path, encoding='utf-8') as f:
            for line in f.readlines():
                if line.startswith('nserver:'):
                    nserver_data = line.removeprefix('nserver:').strip()
                    if ' ' in nserver_data:  # nserver:    foo.bar.baz 1.2.3.4
                        nserver_name, nserver_ip = nserver_data.split(' ', 1)
                        try:
                            ipaddress.ip_address(nserver_ip)
                        except ValueError:
                            logging.warning('[%s] Could not parse nserver %r as IP, ignoring', zone, nserver_ip)
                            continue
                    else: # nserver:    just.a.name
                        nserver_name = nserver_data
                        nserver_ip = None
                        if nserver_name.endswith('.ipv4.registry-sync.dn42'):
                            # 4.3.2.1.ipv4.registry-sync.dn42 -> 1.2.3.4
                            nserver_ip = '.'.join(nserver_name.split('.')[3::-1])
                        elif nserver_name.endswith('.ipv6.registry-sync.dn42'):
                            nserver_chars = nserver_name.split('.')[-4::-1]
                            nserver_chunks = [''.join(nserver_chars[i:i+4]) for i in range(0, len(nserver_chars), 4)]
                            nserver_ip = ':'.join(nserver_chunks)
                        elif nserver_ips := self._seen_nameservers.get(nserver_name):
                            result.nameservers += sorted(nserver_ips)
                            logging.info('[%s] Using saved nservers %s -> %s', zone, nserver_name, nserver_ips)
                            continue
                        else:
                            logging.warning('[%s] Could not parse nserver %r', zone, nserver_data)
                            continue

                    ipaddress.ip_address(nserver_ip)
                    self._seen_nameservers[nserver_name].add(nserver_ip)
                    result.nameservers.append(nserver_ip)
                if line.startswith('ds-rdata'):
                    ta = line.split(None, 1)[-1].strip()
                    result.trust_anchors.append(ta)
        return result

    def populate_zone(self, zone: str, path: pathlib.Path):
        """Try to populate a forward or reverse DNS zone"""
        entry = self._read_registry_dns_entry(zone, path)
        if entry.nameservers:
            self.conf['recursor']['forward_zones'].append({
                'zone': zone,
                'forwarders': entry.nameservers
            })
            logging.info('[%s] forwarders=%s', zone, entry.nameservers)
        else:
            logging.warning('[%s] No valid forwarders found, skipping', zone)
            return

        if entry.trust_anchors:
            self.conf['dnssec']['trustanchors'].append({
                'name': zone,
                'dsrecords': entry.trust_anchors
            })
            logging.info('[%s] trustanchors=%s', zone, entry.trust_anchors)
        else:
            self.conf['dnssec']['negative_trustanchors'].append({
                'name': zone,
                'reason': 'no trust anchors found in dn42 registry'
            })
            logging.info('[%s] no trust anchors found', zone)

    def generate(self):
        self.conf = {
            'recursor': {
                'forward_zones_recurse': [
                    {
                        'zone': '.',
                        'forwarders': _CLEARNET_DNS_SERVERS
                    }
                ],
                'forward_zones': []
            },
            'dnssec': {
                'trustanchors': [
                    # Ideally we can import this from the system DS file directly, but
                    # https://github.com/PowerDNS/pdns/issues/14999 prevents this from working properly
                    {
                        'name': '.',
                        'dsrecords': self._read_system_ds()
                    }
                ],
                'negative_trustanchors': []
            }
        }

        # Fill in dn42 zones
        for dns_entry_path in self.registry_path.glob('data/dns/*'):
            zone = dns_entry_path.name
            if '.' in zone and not zone.endswith('.arpa'):  # not a TLD
                continue
            self.populate_zone(zone, dns_entry_path)

        # Fill in PTR zones
        for netblock, zone in _PTR_ZONES:
            path = self.registry_path / 'data' / ('inet6num' if ':' in netblock else 'inetnum') / \
                (netblock.replace('/', '_'))
            self.populate_zone(zone, path)

    def write(self, filename):
        with open(filename, 'w', encoding='utf8') as f:
            f.write('# Autogenerated, do not edit!\n')
            yaml.dump(self.conf, f, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", '--verbose', help="enable verbose logging", action='store_true')
    parser.add_argument("registry_path", help="path to dn42 registry Git repo", type=pathlib.Path)
    parser.add_argument("filename", help="path to write output files", type=pathlib.Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    g = ForwardZonesGenerator(args.registry_path)
    g.generate()
    g.write(args.filename)

if __name__ == '__main__':
    main()
