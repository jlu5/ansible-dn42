#!/usr/bin/env python3
"""
Make a website entry for a server on https://jlu5.com/dn42
"""
import sys

from _common import *

def main():
    hosts = yaml_load('hosts.yml')
    hosts = hosts['dn42routers']['hosts']
    servers_by_name = {serverdata['shortname']: server for server, serverdata in hosts.items()}

    try:
        server = sys.argv[1]
    except IndexError:
        print(f"Usage: {sys.argv[0]} <shortname>")
        print(__doc__.strip())
        sys.exit(1)

    servername = servers_by_name[server]
    serverdata = hosts[servername]

    # too lazy to do the flag code now
    print(f"""
#### {serverdata['location']}

- **Hostname**: {servername}
- **Wireguard port**: 50000 + last 4 digits of your ASN
- **Wireguard pubkey**: {serverdata['wg_pubkey']}
- **Tunneled IPv4 address**: {serverdata['ownip']}
- **Tunneled IPv6 address**: {serverdata['link_local_ip6']} (link-local) OR {serverdata['ownip6']}
""")

if __name__ == '__main__':
    main()
