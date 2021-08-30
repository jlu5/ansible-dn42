#!/bin/bash
# Automatically reset dead WireGuard tunnels

if [[ -f /opt/dn42/interfaces-dn42 ]]; then
    IFACEFILE=/opt/dn42/interfaces-dn42
else
    IFACEFILE=/etc/network/interfaces
fi

if [[ $EUID -ne 0 ]]; then
	echo "This script must be run as root."
	exit 1
fi

export PATH="$PATH:/sbin:/usr/sbin"
echo "Current time: $(date)"

read -ra wg_interfaces < <(wg show interfaces)

TIMEOUT=$(expr 60 '*' 30)  # 30 minutes

reset_iface() {
    echo "  Stopping interface $1"
    ifdown "$1" --interfaces="$IFACEFILE"
    ip link del "$1"
    echo "  Starting interface $1"
    ifup "$1" --interfaces="$IFACEFILE"
    echo "  Done"
}

for iface in "${wg_interfaces[@]}"; do
    last_handshake="$(wg show "$iface" latest-handshakes)"
    if [[ -z "$last_handshake" ]]; then
        echo "$iface: last handshake field is empty (interface probably failed to start)"
        reset_iface "$iface"
        continue
    fi

    last_handshake_time="$(cut -f 2 <<< "$last_handshake")"
    if (($(date +%s) - $last_handshake_time > $TIMEOUT)); then
        echo "$iface: last handshake $last_handshake_time is longer than ${TIMEOUT}s ago"
        reset_iface "$iface"
    else
        echo "$iface: OK"
    fi
done
