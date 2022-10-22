#!/bin/bash

cd "$(dirname "$0")" || exit 1  # move to script directory
cd .. || exit 1

oldname="$1"
newname="$2"

if [[ -z "$newname" ]]; then
    echo "usage: $0 <old name> <new name>"
    echo "rename a server definition"
    exit 1
fi

set -x
sed -i "s/$oldname/$newname/g" global-config/igp-tunnels.yml hosts.yml
sed -iE "s/\(cleanup_remove_ifaces: \[.*\)\]/\1,igp-$oldname\]/" global-config/general.yml
mv -i "roles/config-bird2/config/peers/$oldname" "roles/config-bird2/config/peers/$newname"
for vpn in "wireguard" "gre" "openvpn"; do
    if [[ -f "roles/config-$vpn/config/$oldname.yml" ]]; then
        mv -i "roles/config-$vpn/config/$oldname.yml" "roles/config-$vpn/config/$newname.yml"
    fi
done
