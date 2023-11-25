from dataclasses import dataclass
import traceback

from utils import prompt_bool, prompt_float
from pingtest import get_rtt, PingTestError

@dataclass
class BirdOptions:
    mp_bgp: bool
    extended_next_hop: bool
    latency: float

def fill_bird_options(node, completed_config):
    mp_bgp = False
    extended_next_hop = False
    if completed_config['peer_v6']:
        # Dual stack. Check if we want mp_bgp and enh
        if completed_config['peer_v4']:
            mp_bgp = prompt_bool("Enable MP-BGP?")
        if mp_bgp or not completed_config['peer_v4']:
            extended_next_hop = prompt_bool("Enable extended next hop?")

    latency = None
    remote = completed_config['remote']
    # FIXME: unhardcode this
    api_url = f'https://{node}.peer.highdef.network/webtrace/'
    if remote and prompt_bool(f"Check latency to {remote}?"):
        try:
            latency = get_rtt(api_url, remote)
        except (OSError, ValueError, LookupError, PingTestError):
            traceback.print_exc()
    if latency is None:
        latency = prompt_float(f"Input latency value for remote {remote or '(unknown)'} (ms):")

    return BirdOptions(mp_bgp, extended_next_hop, latency)
