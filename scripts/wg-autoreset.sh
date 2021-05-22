#!/bin/bash
# Automatically reset dead WireGuard tunnels

if [[ $EUID -ne 0 ]]; then
	echo "This script must be run as root."
	exit 1
fi

read -ra wg_interfaces < <(wg show interfaces)

TIMEOUT=$(expr 60 '*' 30)  # 30 minutes

for iface in "${wg_interfaces[@]}"; do
    last_handshake="$(wg show "$iface" latest-handshakes)"
    if [[ -z "$last_handshake" ]]; then
        echo "$iface: last handshake field is empty (interface probably failed to start)"
        echo "  Hard resetting interface"
        ip link del "$iface"
        ifup "$iface"
        echo "  Done"
        continue
    fi

    last_handshake_time="$(cut -f 2 <<< "$last_handshake")"
    if (($(date +%s) - $last_handshake_time > $TIMEOUT)); then
        echo "$iface: last handshake $last_handshake_time is longer than ${TIMEOUT}s ago"
        echo "  Soft resetting interface"
        # XXX: hardcoded path
        wg syncconf "$iface" "/etc/wireguard/$iface.conf"
        echo "  Done"
    else
        echo "$iface: OK"
    fi
done
