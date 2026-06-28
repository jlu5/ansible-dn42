import ipaddress

def get_ptr_zone(cidr_str: str, rfc2317_separator: str = '/') -> str:
    """
    Returns the PTR zone name for the CIDR, if one is possible.
    """
    network = ipaddress.ip_network(cidr_str, strict=False)
    prefixlen = network.prefixlen

    if network.version == 4:
        if prefixlen % 8 and prefixlen < 24:
            raise ValueError(f"IPv4 prefix length {prefixlen} cannot be used for PTR records")

        octets = str(network.network_address).split(".")
        keep_octets = octets[:prefixlen // 8]
        ptr = f"{'.'.join(reversed(keep_octets))}.in-addr.arpa"
        if prefixlen > 24:
            last_octet = octets[-1]
            ptr = f"{last_octet}{rfc2317_separator}{prefixlen}.{ptr}"
        return ptr
    else:
        if prefixlen % 4:
            raise ValueError(f"IPv6 prefix length {prefixlen} cannot be used for PTR records")
        exploded_net = network.network_address.exploded.replace(":", "")
        prefix_nibbles = list(exploded_net[:prefixlen // 4])

        return f"{'.'.join(reversed(prefix_nibbles))}.ip6.arpa"
