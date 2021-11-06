from dataclasses import dataclass
import subprocess
import traceback

from utils import prompt_bool, prompt_float
from pingtest import remote_ping, parse_ping

@dataclass
class BirdOptions:
    mp_bgp: bool
    extended_next_hop: bool
    latency: float

def fill_bird_options(node, completed_config):
    mp_bgp = False
    extended_next_hop = False
    if completed_config['peer_v4'] and completed_config['peer_v6']:
        # Dual stack. Check if we want mp_bgp and enh
        mp_bgp = prompt_bool("Enable MP-BGP?")
        if mp_bgp:
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
