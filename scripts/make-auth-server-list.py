#!/usr/bin/env python3
"""
Generate a list of auth DNS servers for the delegation-servers.dn42 pool
"""

import os
import pathlib

from _common import get_hosts, get_hosts_group, yaml_load

def main():
    hosts = yaml_load('hosts.yml')
    global_config = yaml_load('global-config/general.yml')
    dns_suffix = global_config['dns_auto_host_record_suffix'] + '.' + global_config['dns_domain']
    for host, hostdata in get_hosts(hosts).items():
        if host in get_hosts_group(hosts['anycast_auth_dns']):
            dns_ip = hostdata['ownip6'].replace('::1', '::5353')
            print(f'{dns_ip} auth-dns.{host}{dns_suffix}')

if __name__ == '__main__':
    rootdir = pathlib.Path(os.path.dirname(__file__)) / ".."
    os.chdir(rootdir)
    main()
