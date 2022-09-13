#!/usr/bin/env python3
import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from peerconfgen import scrape_peer_config

class PeerConfScrapeTest(unittest.TestCase):
    maxDiff = None

    def test_scrape_tabular(self):
        s = """
Location\tSomewhere on Earth
Hostname\tdn42.pop.example.com
Clearnet IPv4\t1.2.3.4
Clearnet IPv6\t2605:6400:10:da::4242
WireGuard Key\t0123456789abcdefghijklmnopqrstuvwxyzABCDEFGH=
dn42 IPv4\t172.20.229.112/32
dn42 IPv6 (Link-local)\tfe80::1234/64
dn42 IPv6 (ULA)\tfd86:bad:11b7::4242/128
"""
        #pprint.pprint(scrape(s), indent=4)
        self.assertEqual({
            'asn': [],
            'peer_v4': ['172.20.229.112'],
            'peer_v6': ['fe80::1234', 'fd86:bad:11b7::4242'],
            'port': [],
            'remote': ['dn42.pop.example.com', '1.2.3.4', '2605:6400:10:da::4242'],
            'wg_pubkey': ['123456789abcdefghijklmnopqrstuvwxyzABCDEFGH=']
        }, scrape_peer_config(s))

    def test_scrape_as1080(self):
        s = """AS4242421080

    Hostname: dn42-us-chi01.jlu5.com
    WireGuard / OpenVPN port: 20000 + last 4 digits of your ASN
    WireGuard pubkey: u4WJMAoCHIOeh/+6NWMytNygp+/wrMogB+rwyVzXoEg=
    Tunneled IPv4 address: 172.20.229.113
    Tunneled IPv6 address: fe80::113 (link-local) OR fd86:bad:11b7::1
"""
        self.assertEqual({
            'asn': ['4242421080'],
            'peer_v4': ['172.20.229.113'],
            'peer_v6': ['fe80::113', 'fd86:bad:11b7::1'],
            'port': [],
            'remote': ['dn42-us-chi01.jlu5.com'],
            'wg_pubkey': ['u4WJMAoCHIOeh/+6NWMytNygp+/wrMogB+rwyVzXoEg=']
        }, scrape_peer_config(s))

    def test_scrape_manyvalues(self):
        s = """
Scavenger hunt!

123456 4242421080 424242234 6939 174 4242420000 4201279999
AS4242427777 4242428888suffixes-not-accepted
dn42-us-chi01.jlu5.com Test.Example.Com wiki.dn42 HELLO.WORLD de-nbg01.rtr.highdef.dn42 A b. CDEF
ipv4: 8.8.8.8 172.20.229.113 172.11.1.1 172.1 172.11.1.1111
ipv6: fd86:bad fd86:really:Bad FD???? fd:86:badbad::1  fd:86:bad::1 FD88::5 a:b:C:d e::e::e fd::BEEF
"""
        self.assertEqual({
            'asn': ['4242421080', '4242420000', '4201279999', '4242427777'],
            'peer_v4': ['172.20.229.113'],
            'peer_v6': ['FD88::5'],
            'port': [],
            'remote': ['dn42-us-chi01.jlu5.com',
                       'Test.Example.Com',
                       'HELLO.WORLD',
                       '8.8.8.8',
                       '172.11.1.1',
                       'fd:86:bad::1',
                       'fd::BEEF'],
            'wg_pubkey': []
        }, scrape_peer_config(s))

    def test_scrape_prefer_link_local6(self):
        s = """fd86:bad:11b7::4242/128 fe80::1234/64
"""
        #pprint.pprint(scrape(s), indent=4)
        self.assertEqual({
            'asn': [],
            'peer_v4': [],
            'peer_v6': ['fe80::1234', 'fd86:bad:11b7::4242'],
            'port': [],
            'remote': [],
            'wg_pubkey': []
        }, scrape_peer_config(s))

    def test_scrape_only_ula6(self):
        s = """AS4242429999
WireGuard node: test.example.com:3<last 4 digits of your ASN>
WireGuard pubkey: 0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=
Tunnel IPv4: 172.22.108.22
Tunnel IPv6: fd00::1
"""
        self.assertEqual({
            'asn': ['4242429999'],
            'peer_v4': ['172.22.108.22'],
            'peer_v6': ['fd00::1'],
            'port': [],
            'remote': ['test.example.com'],
            'wg_pubkey': ['0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=']
        }, scrape_peer_config(s))

    def test_scrape_only_link_local6(self):
        s = """AS4242429999
Endpoint: test.example.org:20000 + last 4 digits of ASN
WireGuard pubkey: 0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=
Tunnel v4: 172.22.108.22
Tunnel v6: fe80::9999
"""
        self.assertEqual({
            'asn': ['4242429999'],
            'peer_v4': ['172.22.108.22'],
            'peer_v6': ['fe80::9999'],
            'port': [],
            'remote': ['test.example.org'],
            'wg_pubkey': ['0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=']
        }, scrape_peer_config(s))

    def test_scrape_wireguard_port(self):
        s = """AS4242429999
Endpoint: test.example.org:21080
WireGuard pubkey: 0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=
Tunnel v4: 172.22.108.22
Tunnel v6: fe80::9999

scraping test:  33333 20000 12345 50505 test:23456
"""
        self.assertEqual({
            'asn': ['4242429999'],
            'peer_v4': ['172.22.108.22'],
            'peer_v6': ['fe80::9999'],
            'port': ['21080', '33333', '50505', '23456'],
            'remote': ['test.example.org'],
            'wg_pubkey': ['0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=']
        }, scrape_peer_config(s))

if __name__ == '__main__':
    unittest.main()
