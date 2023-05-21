#!/usr/bin/env python3

"""
Script to apply ip rules.
"""

import argparse
import subprocess

IP_RULE_MIN_PRIO = 20000
IP_RULE_MAX_PRIO = 20050

def add(path, ipv6=False):
    prio = IP_RULE_MIN_PRIO
    with open(path, encoding='utf8') as f:
        for rule in f.readlines():
            if not rule.strip():
                continue
            if prio > IP_RULE_MAX_PRIO:
                raise ValueError(f'Priority {prio} out of range')
            cmd = ['ip']
            if ipv6:
                cmd.append('-6')
            cmd += ['rule', 'add', 'priority', str(prio), *rule.split()]
            print(cmd)
            subprocess.call(cmd)
            prio += 1

def remove():
    for prio in range(IP_RULE_MIN_PRIO, IP_RULE_MAX_PRIO+1):
        cmd = ['ip', 'rule', 'del', 'priority', str(prio)]
        print(cmd)
        subprocess.call(cmd)

        cmd = ['ip', '-6', 'rule', 'del', 'priority', str(prio)]
        print(cmd)
        subprocess.call(cmd)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['add', 'del', 'refresh'])
    parser.add_argument('path')
    parser.add_argument('path6')
    args = parser.parse_args()

    action = args.action.lower()
    if action in {'del', 'refresh'}:
        remove()
    if action in {'add', 'refresh'}:
        add(args.path)
        add(args.path6, ipv6=True)

if __name__ == '__main__':
    main()
