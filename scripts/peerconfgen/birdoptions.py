from dataclasses import dataclass
import math
import subprocess
import traceback

from utils import prompt_bool, prompt_float
from pingtest import remote_ping, parse_ping

@dataclass
class BirdOptions:
    mp_bgp: bool
    extended_next_hop: bool
    latency: float

def get_dn42_latency_value(latency):
    for x in range(1, 10):
        if latency < (math.e ** x):
            return x
    return x

def fill_bird_options(node, completed_config):
    mp_bgp = False
    extended_next_hop = False
    if completed_config['peer_v4'] and completed_config['peer_v6']:
        # Dual stack. Check if we want mp_bgp and enh
        mp_bgp = prompt_bool("Enable MP-BGP?")
        extended_next_hop = prompt_bool("Enable extended next hop?")

    latency = None
    remote = completed_config['remote']
    if remote and prompt_bool(f"Check latency to {remote}?"):
        try:
            ping_raw = remote_ping(node, remote)
            ping_parsed = parse_ping(ping_raw)
            latency = float(ping_parsed['avg'])
        except (subprocess.SubprocessError, ValueError, LookupError):
            traceback.print_exc()
    if latency is None:
        latency = prompt_float(f"Input latency value for remote {remote or '(unknown)'} (ms):")

    return BirdOptions(mp_bgp, extended_next_hop, latency)
