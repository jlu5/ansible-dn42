#!/usr/bin/env python3
"""Generate the config for a new Smokeping entry"""

import argparse
import ipaddress
import re
import socket
import urllib.parse

import pycountry
import requests

# https://stackoverflow.com/a/36760050
IP4_RE = re.compile(r'((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}')
IP6_RE = re.compile(
    r'[a-fA-F0-9]{1,4}:[a-fA-f0-9:]+' # lazy check
)
def scrape_ips(url, force_dns=False):
    url_parts = urllib.parse.urlparse(url)
    netloc = url_parts.netloc or url
    if not url_parts.scheme:
        url = 'http://' + url
    dns_results = {ipaddress.ip_address(entry[-1][0]) for entry in socket.getaddrinfo(netloc, 80)}
    print(dns_results)
    r = requests.get(url, timeout=10)

    ipv4 = ipv6 = None
    if force_dns:
        for ip in dns_results:
            if ipv4 and ipv6:
                break
            if not ipv4 and isinstance(ip, ipaddress.IPv4Address):
                ipv4 = netloc
            if not ipv6 and isinstance(ip, ipaddress.IPv6Address):
                ipv6 = netloc
        return ipv4, ipv6

    for m_ipv4 in IP4_RE.finditer(r.text):
        ipv4 = m_ipv4.group(0)
        ipaddr = ipaddress.ip_address(ipv4)
        if not ipaddr.is_global:
            continue
        if ipaddr in dns_results:
            ipv4 = netloc
        break
    for m_ipv6 in IP6_RE.finditer(r.text):
        ipv6 = m_ipv6.group(0)
        try:
            ipaddr = ipaddress.ip_address(ipv6)
            if not ipaddr.is_global:
                continue
            if ipaddr in dns_results:
                ipv6 = netloc
        except ValueError as e:
            print(f'Skipping invalid v6 IP: {ipv6}, {e}')
            ipv6 = None
        else:
            break
    assert ipv4 or ipv6
    return ipv4, ipv6

def get_field(desc, prefilled=None):
    if prefilled:
        return prefilled
    return input(f'{desc}: ')

_COUNTRIES_SHOW_PROVINCE = {'CA', 'US'}
def fmt_smokeping(entry_name, address, isp, country, province, city, levels=2):
    assert levels >= 0
    hdr = '+' * levels
    country = country.upper()
    province = province.upper()
    city = city.title()
    print(f'{hdr} {entry_name}')
    if country == 'UK':
        country = 'GB'
    pycountry_entry = pycountry.countries.get(alpha_2=country)
    assert pycountry_entry
    if country == 'GB':
        country = 'UK'
    # if ipv6:
    #     print('probe = FPing6')
    if country in _COUNTRIES_SHOW_PROVINCE:
        print(f'menu = [{country}/{province}] {isp}')
        loc = f'{city}, {province}, {country}'
        print(f'title = [{country}/{province}] {isp} - {loc} [{address}]')
    else:
        print(f'menu = [{country}] {isp}')
        loc = f'{city}, {pycountry_entry.name}'
        print(f'title = [{country}] {isp} - {loc} [{address}]')
    print(f'host = {address}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?')
    parser.add_argument('-C', '--country', help='country code', nargs='?')
    parser.add_argument('-p', '--province', help='province/state code (US, CA only)', nargs='?')
    parser.add_argument('-c', '--city', help='city name', nargs='?')
    parser.add_argument('-n', '--name', help='entry name', nargs='?')
    parser.add_argument('-i', '--isp', help='ISP / hosting provider', nargs='?')
    parser.add_argument('-d', '--force-dns', help='Use DNS only instead of scraper', action='store_true')

    args = parser.parse_args()

    if args.url:
        ips = scrape_ips(args.url, force_dns=args.force_dns)
        print("Scraped IPs:", ips)
        ipv4, ipv6 = ips
    else:
        ipv4 = input("IPv4 address: ").strip()
        if ipv4:
            ipaddress.IPv4Address(ipv4)
        ipv6 = input("IPv6 address: ").strip()
        if ipv6:
            ipaddress.IPv6Address(ipv6)
    country = get_field('country code (XX)', args.country).upper()
    province = ''
    if country in {'CA', 'US'}:
        province = get_field('state/province code (XX)', args.province) or ''
    city = get_field('city name (in full)', args.city)
    entry_name = get_field('Smokeping entry name', args.name)
    isp = get_field('ISP / hosting provider', args.isp)

    if ipv4:
        print('\nIPv4:')
        fmt_smokeping(entry_name, ipv4, isp, country, province, city)
    if ipv6:
        print('\nIPv6:')
        fmt_smokeping(entry_name, ipv6, isp, country, province, city)

if __name__ == '__main__':
    main()
