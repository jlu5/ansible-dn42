#!/bin/bash
# pingcheck.sh [<warn-threshold>] [<number of pings>]
# Latency / reachability test for dn42 peer interfaces

THRESHOLD=${1:-50}  # milliseconds
PING_COUNT=${2:-10}

c_red="$(tput setaf 9)"
c_yellow="$(tput setaf 3)"
c_reset="$(tput sgr0)"

print_configured_host() {
    echo -n "  Configured Endpoint: "
    grep -oP "(?<=Endpoint = ).*(?=\\:[0-9]{0,5})" "/etc/wireguard/$1.conf" || echo "NONE"
}

declare -A iface_for_ip;
for s in /sys/devices/virtual/net/dn42*; do
    ifname="$(basename "$s")"
    ip="$(sudo wg show "$ifname" | grep -oP "[0-9a-fA-F:.]{5,}(?=\\]?:[0-9]{0,5})")"
    if [[ -z "$ip" ]]; then
        echo "${c_red}[IFACE DOWN] $ifname${c_reset}"
        print_configured_host "$ifname"
        continue
    fi
    iface_for_ip["$ip"]="$ifname"
done

while read -r line; do
    line="$(tr -s ' ' <<< "$line")"
    ip="$(cut -d ' ' -f 1 <<< "$line")"
    #loss_stats="$(cut -d ' ' -f 5 <<< "$line")"
    ping_stats="$(cut -d ' ' -f 8 <<< "$line")"
    ifname="${iface_for_ip[$ip]}"
    if [[ -z "$ping_stats" ]]; then
        echo "${c_red}[PING FAILED] ${ifname}${c_reset} : $line"
        print_configured_host "$ifname"
        continue
    fi
    avg=$(cut -d '/' -f 1 <<< "$ping_stats")
    #echo "${iface_for_ip[$ip]} avg $avg"
    if (( $(echo "${avg}>${THRESHOLD}" | bc -l) )); then
        echo "${c_yellow}[HIGH LATENCY] ${ifname}${c_reset} has ${avg} > ${THRESHOLD} : $line"
        print_configured_host "$ifname"
    fi
done < <(fping -c${PING_COUNT} -q "${!iface_for_ip[@]}" 2>&1)
