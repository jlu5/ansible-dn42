import argparse
import re
import shlex
import subprocess

PING_COUNT = 5

def remote_ping(node, target):
    output = subprocess.check_output([
        # shlex.quote here should be safe, right? Don't see any obvious way to disable starting a shell
        # when running remote ssh commands
        'ssh', node, 'ping', f'-c{PING_COUNT}', '-q', '-n', shlex.quote(target)
    ], encoding='utf-8')
    print("Ping output:")
    print(output)
    return output

RTT_RE = re.compile(r'rtt min\/avg\/max\/mdev = (?P<min>[0-9.]+)\/(?P<avg>[0-9.]+)\/(?P<max>[0-9.]+)\/(?P<mdev>[0-9.]+) ms')
def parse_ping(text):
    lines = text.strip().splitlines()
    match = RTT_RE.match(lines[-1])
    if not match or not match.group('avg'):
        raise ValueError(f"Failed to parse text: {lines[-1]}")
    return match.groupdict()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node', help='Node to try ping from', type=str)
    parser.add_argument('target', help='Target to ping', type=str)
    args = parser.parse_args()

    text = remote_ping(args.node, args.target)
    print(parse_ping(text))
