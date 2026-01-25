#!/usr/bin/env python3

# igpping: Generate IGP costs based on ping results
#
# Copyright (C) 2021 James Lu <james@overdrivenetworks.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import configparser
import os
import os.path
import shutil
import subprocess
import sys

CONFIG = configparser.ConfigParser()

def write_costs(hosts, results, overwrite):
    output_path_format = CONFIG.get(CONFIG.default_section, 'OutputPathFormat')
    # mkdir the output folder if it doesn't already exist
    os.makedirs(os.path.dirname(output_path_format), exist_ok=True)

    for host in hosts:
        cost = results.get(host, CONFIG.getint(CONFIG.default_section, 'FallbackCost'))
        format_args = {
            "cost": cost, "host": host
        }

        output_path = output_path_format.format_map(format_args)

        if os.path.exists(output_path) and not overwrite:
            continue  # already exists

        # This used to support custom output text formats but it seems that is not needed, as Bird supports
        # nesting includes in arbitrary positions: https://bird.network.cz/?get_doc&v=20&f=bird-3.html#ss3.2
        output_text = str(cost)
        print(f"{output_text} => {output_path}")
        with open(output_path, 'w') as f:
            f.write(output_text)
            if not output_text.endswith('\n'):
                f.write("\n")

_MIN_RTT = 1
_MAX_RTT = 65535
def calc_costs(fping_output) -> dict[str, int]:
    results = {}
    # fping aggregate lines look like this:
    # "192.168.1.102 : 0.316 0.281 - 132 0.242 0.403 0.319 0.336 0.290 0.457"
    # '-' means timeout, everything else is RTT in milliseconds
    for line in fping_output.decode('utf-8').splitlines():
        print(line)
        host, rtt_entries = line.rsplit(": ", 1)
        host = host.strip()  # This can be right padded if there are many hosts
        penalty = 0
        rtt_sum = 0
        n_success = 0
        for rtt in rtt_entries.split():
            if rtt == '-':
                penalty += CONFIG.getint(CONFIG.default_section, "LossPenalty")
            else:
                rtt_sum += float(rtt)
                n_success += 1
        if n_success:
            rtt_avg = int(rtt_sum / n_success)
            rtt_avg += CONFIG.getint(CONFIG.default_section, "BaseCost")
            # Clamp the result to 1-65535
            results[host] = max(_MIN_RTT, min(_MAX_RTT, rtt_avg+penalty))

    return results

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate IGP costs from FPing results')
    parser.add_argument('hostsfile', help='path to hosts file (newline separated list of addresses)', default="igpping-hosts.txt", nargs='?')
    parser.add_argument('config', help='path to config file', default="igpping.conf", nargs='?')
    parser.add_argument('--init', help='initialize file structure only (do not check pings or replace existing results)', action='store_true')
    args = parser.parse_args()

    if not shutil.which('fping'):
        print("ERROR: missing fping binary - please install it first")
        sys.exit(1)

    with open(args.config) as f:
        CONFIG.read_file(f)

    with open(args.hostsfile) as f:
        hosts = f.read().splitlines()

    if args.init:
        results = {}  # Use the default ping time for everything
    else:
        fping_args = [
            'fping',
            '-q',
            '--vcount',
            CONFIG.get(CONFIG.default_section, 'PingCount'),
            '--file',
            args.hostsfile
        ]
        print(f"Running fping with args: {fping_args}")
        fping_output = subprocess.run(fping_args, stderr=subprocess.PIPE, check=False)
        results = calc_costs(fping_output.stderr)

    write_costs(hosts, results, overwrite=not args.init)

if __name__ == '__main__':
    main()
