#!/bin/bash
set -e

curl -fSLR {-o,-z}/etc/bird/roa_dn42.conf    https://dn42.burble.com/roa/dn42_roa_bird2_4.conf
curl -fSLR {-o,-z}/etc/bird/roa_dn42_v6.conf https://dn42.burble.com/roa/dn42_roa_bird2_6.conf
sed -i 's/roa/route/g' /etc/bird/roa_dn42{,_v6}.conf
/usr/sbin/birdc configure || true
