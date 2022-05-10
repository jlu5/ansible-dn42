import string
from utils import get_iface_name, get_dn42_latency_value

def _format_bool_bird(value):
    return 'on' if value else 'off'

def _format_short_asn(asn):
    if int(asn) >= 4200000000:
        return asn[-4:]
    return asn

def gen_wg_config(peername, completed_config):
    """
    Generates a YAML wg_peers config entry.
    """
    if completed_config['remote']:
        remote = completed_config['remote'] + ':' + completed_config['port']
    else:
        remote = None

    result = {
        # Opting not to include the location code anymore
        'name': get_iface_name(peername),
        # 20000 + last 4 digits of ASN
        'port': int('2' + _format_short_asn(completed_config['asn'])),
        'remote': remote,
        'wg_pubkey': completed_config['wg_pubkey'],
        'peer_v4': completed_config['peer_v4'],
        'peer_v6': completed_config['peer_v6'],
    }
    return result

def gen_bird_peer_config(peername, completed_config, bird_options):
    """
    Generates a BIRD BGP session.
    """
    latency_community = get_dn42_latency_value(bird_options.latency)
    iface_name = get_iface_name(peername)

    if peername.startswith(tuple(string.digits)):
        peername = "_" + peername
    asn = completed_config['asn']
    short_asn = _format_short_asn(asn)

    v4_channel = f"""ipv4 {{
        import where dn42_import_filter({latency_community},24,34);
        export where dn42_export_filter({latency_community},24,34);
        extended next hop {_format_bool_bird(bird_options.extended_next_hop)};
    }};"""
    v6_channel = f"""ipv6 {{
        import where dn42_import_filter({latency_community},24,34);
        export where dn42_export_filter({latency_community},24,34);
    }};"""
    if bird_options.mp_bgp or bird_options.extended_next_hop:
        # MP-BGP over v6
        return f"""protocol bgp {peername}_{short_asn} from dnpeers {{
    neighbor {completed_config['peer_v6']} as {asn};
    interface "{iface_name}";
    passive { _format_bool_bird(not completed_config.get('remote')) };

    { v4_channel }
    { v6_channel }
}}
"""

    s = ""
    if completed_config['peer_v4']:
        # Create a v4 session
        s += f"""
protocol bgp {peername}_{short_asn} from dnpeers {{
    neighbor {completed_config['peer_v4']} as {asn};
    passive { _format_bool_bird(not completed_config.get('remote')) };

    { v4_channel }
}}
"""
    if completed_config['peer_v6']:
        # Create a v6 session
        s += f"""
protocol bgp {peername}_{short_asn}_v6 from dnpeers {{
    neighbor {completed_config['peer_v6']} as {asn};
    interface "{iface_name}";
    passive { _format_bool_bird(not completed_config.get('remote')) };

    { v6_channel }
}}
"""
    return s
