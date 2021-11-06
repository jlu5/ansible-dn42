import ipaddress
import string

def is_valid_endpoint(candidate):
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        # not an IP address. Drop the candidate if it ends with a number
        # (.dn42 or malformed IPv4), or has a : in it (malformed IPv6)
        return not candidate.endswith(tuple(string.digits)) and ":" not in candidate
    else:
        # Accept only globally routable addresses
        return ip.is_global

def is_valid_peer_v4(candidate):
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    else:
        return ip.version == 4 and (ip.is_link_local or ip.is_private) and not ip.is_loopback

def is_valid_peer_v6(candidate):
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    else:
        return ip.version == 6 and (ip.is_link_local or ip.is_private) and not ip.is_loopback

def is_int(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

def is_port(value):
    if is_int(value):
        return 1 <= int(value) < 65536
    return False
