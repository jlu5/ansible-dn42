#!/usr/bin/env python3
"""
Generate DNS records from my Ansible config.

This scripts looks at the following files:
- global-config/dns-entries.yml for custom DNS entries
- group_vars/all.yml for general AS settings; specifically the following options:
  "ownnets4", "ownnets6", "dns_*"
- The inventory file (hosts.yml) to create host records for routers, unless --no-host-records is set
-
"""

import argparse
import ipaddress
import os

import jinja2

from _common import *

# Global state stuff
args = None
global_vars = {}
hosts = None

ptr_records = {}  # Mapping of IPs to PTR records
namedconf_entries = set()  # Set of files to include in named.conf

def get_zone_file(zonename):
    """
    Create a new zone file, and add it to the list of zones to be included in named.conf.
    The caller should close the returned file descriptor when finished with it.
    """
    fname = zonename.replace('/', '_') + '.zone'
    namedconf_entries.add(fname)
    local_path = os.path.join(args.out_dir, fname)
    fd = open(local_path, 'w')
    # FIXME: make these options configurable
    fd.write(f"""$ORIGIN {zonename}
$TTL {global_vars['dns_ttl']}
@   IN  SOA     {global_vars['dns_nameserver_prefix']}.{global_vars['dns_domain']} placeholder-see-registry.{global_vars['dns_domain']} (
        1           ; serial
        7200        ; refresh period
        2400        ; retry period
        86400       ; expiration
        3600        ; minimum TTL
)
""")
    return fd

def _write_entry(fd, name, rtype, data):
    """
    Write a DNS entry into the given file descriptor.
    """
    fd.write(f"{name} IN {rtype.upper()} {data}\n")

def write_forward_zone(domain, records):
    """
    Write the data for a forward DNS zone.
    """
    fd = get_zone_file(domain)
    for record_name, data in records.items():
        if data['type'] == 'ansible_host_alias':
            hostdata = hosts[data['target']]
            _write_entry(fd, record_name, 'A',    hostdata['ownip'])
            _write_entry(fd, record_name, 'AAAA', hostdata['ownip'])
        else:
            _write_entry(fd, record_name, data['type'], data['target'])
    fd.close()

def _load_config():
    global hosts
    hosts = yaml_load(args.hosts)['dn42routers']['hosts']
    group_vars = yaml_load(args.group_vars)

    # Follow Ansible templating for dns-entries.yml
    with open(args.dns_entries) as f:
        dns_entries_raw = f.read()
    dns_entries_tmpl = jinja2.Template(dns_entries_raw)
    dns_entries = yaml.full_load(dns_entries_tmpl.render(group_vars))

    global_vars.update(group_vars)
    global_vars.update(dns_entries)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out-dir", help="output directory", default="global-config/dns-entries/")
    parser.add_argument("-H", "--hosts", help="path to hosts configuration / inventory file",
                        type=str, default='hosts.yml')
    parser.add_argument("-D", "--dns-entries", help="path to DNS entries configuration",
                        type=str, default='global-config/dns-entries.yml')
    parser.add_argument("-G", "--group-vars", help="path to group vars configuration",
                        type=str, default='group_vars/all.yml')
    parser.add_argument("--no-host-records", help="disable creating host records (DNS & PTR) for routers",
                        action='store_true')
    global args
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    _load_config()

    for domain, records in global_vars['dns_records'].items():
        print(domain, records)
        write_forward_zone(domain, records)

    # For each domain in dns_domains: create a DNS zone file
    # In the domain matching dns_domain, generate host records unless --no-host-records is given

    # Save a mapping of IP addresses to reverse DNS, and then iterate through them to generate PTR zones?
    # Need to search through the list of networks and find which zone they fit under
    #print(global_vars)

if __name__ == '__main__':
    main()
