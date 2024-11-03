from utils import get_iface_name

def _format_short_asn(asn):
    if int(asn) >= 4200000000:
        return asn[-4:]
    return asn

def gen_peer_config(peername, completed_config, bird_options):
    """
    Generates a YAML wg_peers config entry.
    """
    if completed_config['remote']:
        remote = completed_config['remote'] + ':' + completed_config['port']
    else:
        remote = None

    peer_v4 = completed_config['peer_v4']
    peer_v6 = completed_config['peer_v6']
    result = {
        # Opting not to include the location code anymore
        'name': get_iface_name(peername),
        # 20000 + last 4 digits of ASN
        'port': 20000 + int(completed_config['asn']) % 10000,
        'remote': remote,
        'wg_pubkey': completed_config['wg_pubkey'],
        'peer_v4': peer_v4,
        'peer_v6': peer_v6,
        'bgp': {
            'asn': int(completed_config['asn']),
            'ipv4': bool(peer_v4) or bird_options.extended_next_hop,
            'ipv6': bool(peer_v6),
            'mp_bgp': bird_options.mp_bgp or bird_options.extended_next_hop,
            'extended_next_hop': bird_options.extended_next_hop,
        }
    }
    return result
