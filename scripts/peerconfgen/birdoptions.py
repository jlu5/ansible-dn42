from dataclasses import dataclass
import traceback

from exceptions import AbortError
from utils import prompt_bool, prompt_float
from pingtest import get_rtt, PingTestError

@dataclass
class BirdOptions:
    mp_bgp: bool
    extended_next_hop: bool

_PREFERRED_LATENCY = 50
def fill_bird_options(node, completed_config):
    mp_bgp = False
    extended_next_hop = False
    if completed_config['peer_v6']:
        # Dual stack. Check if we want mp_bgp and enh
        if completed_config['peer_v4']:
            mp_bgp = prompt_bool("Enable MP-BGP?")
        if mp_bgp or not completed_config['peer_v4']:
            extended_next_hop = prompt_bool("Enable extended next hop?")

    remote = completed_config['remote']
    # FIXME: unhardcode this
    api_url = f'https://{node}.peer.highdef.network/webtrace/'

    latency_warning = (
        "Please check that this is the closest node to you "
        f"(<{_PREFERRED_LATENCY} ms preferred). Continue anyways?"
    )
    if remote:
        try:
            latency = get_rtt(api_url, remote)
        except (OSError, ValueError, LookupError, PingTestError):
            traceback.print_exc()
            if not prompt_bool(f"Could not ping {remote}. {latency_warning}"):
                raise AbortError()
        else:
            if latency > _PREFERRED_LATENCY and not prompt_bool(
                f"This peering has high latency. {latency_warning}"
            ):
                raise AbortError()

    elif not prompt_bool(f"No remote specified. {latency_warning}"):
        raise AbortError()

    return BirdOptions(mp_bgp, extended_next_hop)
