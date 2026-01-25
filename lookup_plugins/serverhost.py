"""Lookup plugin to find the hostname of each server."""

import socket
from typing import Literal

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

AfType = Literal[4, 6, None]

class LookupModule(LookupBase):

    @staticmethod
    def get_first_ip(hostname: str, aftype: AfType = None) -> str | None:
        """
        Look up the first IP address for a hostname.
        :param hostname: The domain name (e.g., 'google.com')
        :param aftype: 4 for IPv4, 6 for IPv6, or None for system default
        :return: The first matching IP string, or None if not found
        """
        af_map = {
            4: socket.AF_INET,
            6: socket.AF_INET6,
            None: socket.AF_UNSPEC
        }
        family = af_map[aftype]

        try:
            # getaddrinfo returns a list of 5-tuples:
            # (family, type, proto, canonname, sockaddr)
            results = socket.getaddrinfo(hostname, None, family=family)

            if results:
                # sockaddr is the 5th element; its first element is the IP address
                return results[0][4][0]

        except socket.gaierror:
            return None

        return None

    def run(self, terms: list[str], variables=None, aftype: AfType = None, resolve=True, **kwargs):
        assert variables
        hostvars = variables.get('hostvars')

        if hostvars is None:
            raise AnsibleError('hostvars not available')

        results = []
        for server in terms:
            if server not in hostvars:
                raise AnsibleError(f'Server {server} not found in inventory')
            if aftype is None:
                aftype = variables.get('igp_wg_aftype', {}).get(server)

            endpoint = None
            if aftype == 6:
                endpoint = hostvars[server].get('public_host_v6')
            elif aftype == 4:
                endpoint = hostvars[server].get('public_host_v4')

            if not endpoint:
                endpoint = hostvars[server].get('public_host') or hostvars[server]['ansible_host']

            assert endpoint, f"Could not find endpoint for server {server!r}"
            if aftype is None or not resolve:
                results.append(endpoint)
            else:
                # Resolve the IP if resolve=True and aftype override is specified
                results.append(self.get_first_ip(endpoint, aftype=aftype))

        return results
