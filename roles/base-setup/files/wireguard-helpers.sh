#!/bin/sh
# Wireguard helpers, based off Mic92's code @ https://github.com/Mic92/bird-dn42/tree/master/wireguard
###
# MIT License
#
# Copyright (c) 2017 Jörg Thalheim
# Copyright (c) 2020 James Lu <james@overdrivenetworks.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###

set -eu

add() {
  listen_port="$1"
  name="$2"
  public_key="$3"
  endpoint="$4"
  ip4="$5"
  ip6="$6"
  own_ip6="${7:-$OWN_IP6}"
  del "$@"
  ip link add dev "$name" type wireguard

  echo "$PRIVATE_KEY" | wg set "$name" \
    $([ -n "${listen_port+x}" ] && echo "listen-port $listen_port") \
    private-key /dev/stdin \
    peer "$public_key" \
    allowed-ips "0.0.0.0/0,::/0" \
    $([ -n "$endpoint" ] && echo "endpoint $endpoint")

  ip link set dev "$name" up

  if [ -n "${OWN_IP4+x}" ]; then
    add_addr="ip addr add $OWN_IP4 dev $name"
    if [ -n "${ip4}" ]; then
      add_addr="$add_addr peer $ip4"
    fi
    if [ -n "${OWN_IP4_LIFETIME+x}" ]; then
      add_addr="$add_addr preferred ${OWN_IP4_LIFETIME} scope link"
    fi
    eval $add_addr
  fi
  if [ -n "${own_ip6+x}" ]; then
    add_addr6="ip addr add $own_ip6 dev $name"
    if [ -n "$ip6" ]; then
      add_addr6="$add_addr6 peer $ip6"
    fi
    eval $add_addr6
  fi
}
del() {
  name="$2"
  if ip link | grep -q "$name"; then
    ip link del "$name"
  fi
}

case "${1:-}" in
start)
  peers add
  ;;
stop)
  peers del
  ;;
restart)
  peers del
  peers add
  ;;
*)
  echo "USAGE: $0 start|restart|stop" >&2
  exit 1
  ;;
esac
