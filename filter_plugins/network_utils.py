import ipaddress

def get_dn42_remote_ip(peer_config, af_type):
    """Guess the target IP address for a dn42 peer"""
    if bgp_neighbor := peer_config.get('bgp', {}).get('neighbor'):
        # Prefer explicitly configured hosts
        return bgp_neighbor
    if peer_ip := peer_config.get(f'peer_v{af_type}'):
        return peer_ip.split('/', 1)[0]
    if local_addr := peer_config.get(f'local_v{af_type}'):
        ipnet = ipaddress.ip_network(local_addr, strict=False)
        ip = local_addr.split('/', 1)[0]
        ip = ipaddress.ip_address(ip)
        if ipnet.num_addresses not in (2, 4):
            raise ValueError(
                f"Ambiguous local_v{af_type} {ipnet}, please set bgp.neighbor explicitly")
        if ipnet.num_addresses == 4 and ip in (ipnet.network_address, ipnet.broadcast_address):
            raise ValueError(
                f"local_v{af_type} {ip}, should not use the network or broadcast address")

        new_ip = int(ip) ^ (ipnet.num_addresses - 1)
        return str(ipaddress.ip_address(new_ip))
    raise ValueError(f"No IPv{af_type} nexthop found")

class FilterModule():
    def filters(self):
        return {
            'get_dn42_remote_ip': get_dn42_remote_ip
        }
