#!/usr/bin/env python3
"""Tests for peerconfgen"""

import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from peerconfgen import scrape_peer_config, complete_peer_config
from birdoptions import fill_bird_options, BirdOptions
from exporters import gen_wg_config, gen_bird_peer_config
from utils import get_dn42_latency_value

class FakeInput():
    """
    A mock input() function that returns a sequence of predetermined inputs,
    one for each successive input() call.
    """
    def __init__(self, inputs):
        self.inputs = inputs
        self.idx = 0
        self.max_idx = len(inputs)

    def __call__(self, _prompt):
        if self.idx < self.max_idx:
            value = self.inputs[self.idx]
            self.idx += 1
            return value
        raise ValueError("Not expecting any further input() calls")

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
            'remote': ['test.example.org'],
            'wg_pubkey': ['0Y25dQSJA4xo1EPFVPsSwhZoYdJP8WHCoeYDt31N5WU=']
        }, scrape_peer_config(s))

class PeerConfCompleteTest(unittest.TestCase):
    maxDiff = None

    @unittest.mock.patch('builtins.input', FakeInput([
        '4242424242',
        'test.example.org',
        '12345',
        'A' * 43 + '=',
        '172.22.108.1',
        'fe80::1080'
    ]))
    def test_complete_all_fields(self):
        self.assertEqual({
            'asn': '4242424242',
            'remote': 'test.example.org',
            'port': '12345',
            'wg_pubkey': 'A' * 43 + '=',
            'peer_v4': '172.22.108.1',
            'peer_v6': 'fe80::1080',
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([\
        '4242424242',
        '',  # remote
        'A' * 43 + '=',
        '',  # tunnel v4
        'fe80::1080'
    ]))
    def test_complete_all_some_optional(self):
        self.assertEqual({
            'asn': '4242424242',
            'remote': None,
            'port': None,
            'wg_pubkey': 'A' * 43 + '=',
            'peer_v4': None,
            'peer_v6': 'fe80::1080',
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([
        # ASN retries
        'badASN',
        '4242424242',
        '',  # remote
        'A' * 43 + '=',
        '',  # tunnel v4
        'fe80::1080'
    ]))
    def test_complete_all_retry_asn(self):
        self.assertEqual({
            'asn': '4242424242',
            'remote': None,
            'port': None,
            'wg_pubkey': 'A' * 43 + '=',
            'peer_v4': None,
            'peer_v6': 'fe80::1080',
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([
        '4242424242',
        '',  # remote

        # Bad key attempts
        'badKey',
        '🔑',
        '',
        'A' * 42,  # bad length, all too common in practice
        'e' * 43 + '=',

        '',  # tunnel v4
        'fe80::1080'
    ]))
    def test_complete_all_retry_wg_pubkey(self):
        self.assertEqual({
            'asn': '4242424242',
            'remote': None,
            'port': None,
            'wg_pubkey': 'e' * 43 + '=',
            'peer_v4': None,
            'peer_v6': 'fe80::1080',
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([
        '4242424242',
        '',  # remote
        'Zz' * 21 + 'Z=',  # fake wg key

        # tunnel v4
        'fe80::1080',  # wrong IP version
        '8.8.8.8',     # not a dn42 IP
        '172.22.108.23',
        # tunnel v6
        'fd86:bad:11b7::1'
    ]))
    def test_complete_all_retry_peer_v4(self):
        self.assertEqual({
            'asn': '4242424242',
            'remote': None,
            'port': None,
            'wg_pubkey': 'Zz' * 21 + 'Z=',
            'peer_v4': '172.22.108.23',
            'peer_v6': 'fd86:bad:11b7::1',
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([
        '4242424242',
        '',  # remote
        'Test' * 10 + '123=',  # fake wg key

        # tunnel v4
        '172.22.108.23',
        # tunnel v6
        'fe80:1080',
        '10.0.0.1',
        '::1',  # loopback is not allowed here
        'fd86:bad:11b7::1'
    ]))
    def test_complete_all_retry_peer_v6(self):
        self.assertEqual({
            'asn': '4242424242',
            'remote': None,
            'port': None,
            'wg_pubkey': 'Test' * 10 + '123=',  # fake wg key,
            'peer_v4': '172.22.108.23',
            'peer_v6': 'fd86:bad:11b7::1',
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([
        '4201279999',
        'abc.local',  # remote
        # port retries
        'five',
        '',    # port cannot be empty if remote is set
        '3.1415927',
        '8443',
        'Test' * 10 + '123=',  # fake wg key
        # tunnel v4
        '172.22.108.23',
        # tunnel v6
        ''
    ]))
    def test_complete_all_retry_port(self):
        self.assertEqual({
            'asn': '4201279999',
            'remote': 'abc.local',
            'port': '8443',
            'wg_pubkey': 'Test' * 10 + '123=',
            'peer_v4': '172.22.108.23',
            'peer_v6': None,
        }, complete_peer_config({}))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',   # confirm ASN
        '',    # empty remote
        'Y',   # confirm wg key
        'yes', # confirm IPv4
        'YES', # confirm IPv6
    ]))
    def test_complete_prefilled_confirm_all(self):
        prefilled = {
            'asn': ['12345'],
            'remote': [],
            'port': [],
            'wg_pubkey': ['Zz' * 21 + 'Z='],
            'peer_v4': ['10.0.0.1'],
            'peer_v6': ['fe80::1234', 'fd10::1'],
        }
        self.assertEqual({
            'asn': '12345',
            'remote': None,
            'port': None,
            'wg_pubkey': 'Zz' * 21 + 'Z=',
            'peer_v4': '10.0.0.1',
            'peer_v6': 'fe80::1234',
        }, complete_peer_config(prefilled))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',   # confirm ASN
        '',    # empty remote
        'Y',   # confirm wg key
        'yes', # confirm IPv4
        'n',   # reject first IPv6
        'YES', # accept 2nd
    ]))
    def test_complete_prefilled_reject_first(self):
        prefilled = {
            'asn': ['12345'],
            'remote': [],
            'port': [],
            'wg_pubkey': ['Zz' * 21 + 'Z='],
            'peer_v4': ['10.0.0.1'],
            # A common case is to find both link-local and ULA IPv6 on a page
            'peer_v6': ['fe80::1234', 'fd10::1'],
        }
        self.assertEqual({
            'asn': '12345',
            'remote': None,
            'port': None,
            'wg_pubkey': 'Zz' * 21 + 'Z=',
            'peer_v4': '10.0.0.1',
            'peer_v6': 'fd10::1',
        }, complete_peer_config(prefilled))

    @unittest.mock.patch('builtins.input', FakeInput([
        'N',   # reject ASN
        'n',   # reject ASN
        'test', # invalid input - retry
        'no',   # reject ASN
        '4242428888',  # all guesses exhausted; manually type in something else
        'y',   # accept remote
        'y',   # accept port
        'Y',   # confirm wg key
        'n',   # reject IPv4
        '',    # leave IPv4 empty
        'Yes', # confirm first IPv6
    ]))
    def test_complete_prefilled_reject_all(self):
        prefilled = {
            'asn': ['12345', '123456', '1234567'],
            'remote': ['test.null.invalid'],
            'port': ['12345'],
            'wg_pubkey': ['dn42' * 10 + 'dn4='],
            'peer_v4': ['10.0.0.1'],
            # A common case is to find both link-local and ULA IPv6 on a page
            'peer_v6': ['fe80::1234', 'fd10::1'],
        }
        self.assertEqual({
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '12345',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fe80::1234',
        }, complete_peer_config(prefilled))

    @unittest.mock.patch('builtins.input', FakeInput([
        '4242424242',
        '',  # remote
        '',  # port
        'A' * 43 + '=',
        '',  # tunnel v4
        '',  # tunnel v6
    ]))
    def test_complete_no_tunnel_ips_error(self):
        self.assertRaises(ValueError, lambda: complete_peer_config({}))

class PeerConfFillBirdTest(unittest.TestCase):
    maxDiff = None

    def test_calc_dn42_latency(self):
        self.assertEqual(1, get_dn42_latency_value(0.9))
        self.assertEqual(1, get_dn42_latency_value(2.5))
        self.assertEqual(2, get_dn42_latency_value(2.8))
        self.assertEqual(2, get_dn42_latency_value(7.15))
        self.assertEqual(3, get_dn42_latency_value(9.99))
        self.assertEqual(3, get_dn42_latency_value(18.1))
        self.assertEqual(4, get_dn42_latency_value(24.9))
        self.assertEqual(8, get_dn42_latency_value(1500))

    @unittest.mock.patch('builtins.input', FakeInput([
        'n',  # don't auto calculate ping
        'n',  # No extended next hop
        '5',  # manual latency value
    ]))
    def test_fill_bird_options_v6only(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '8888',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fe80::1234',
        }
        self.assertEqual(BirdOptions(False, False, 5.0),
                         fill_bird_options('DUMMYINVALID', cfg))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',  # mp-bgp
        'n',  # extended next hop
        'n',  # don't auto calculate ping
        '123',# manual latency value
    ]))
    def test_fill_bird_options_dualstack(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '8888',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        self.assertEqual(BirdOptions(True, False, 123.0),
                         fill_bird_options('DUMMYINVALID', cfg))


    @unittest.mock.patch('builtins.input', FakeInput([
        'y',  # mp-bgp
        'y',  # extended next hop
        'y',  # auto calculate ping
    ]))
    def test_fill_bird_options_pingtest(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '8888',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        mock_ping_text = """PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.

--- 8.8.8.8 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3030ms
rtt min/avg/max/mdev = 0.874/0.909/0.995/0.050 ms"""
        with unittest.mock.patch('birdoptions.remote_ping', return_value=mock_ping_text):
            self.assertEqual(BirdOptions(True, True, 0.909),
                             fill_bird_options('DUMMYINVALID', cfg))

class PeerConfWriteTest(unittest.TestCase):
    maxDiff = None

    def test_wg_conf(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        self.assertEqual({
            'name': 'dn42-somelongna',
            'port': 28888,
            'remote': 'test.null.invalid:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }, gen_wg_config('somelongname', cfg))

    def test_wg_conf_no_remote(self):
        cfg = {
            'asn': '4242428888',
            'remote': None,
            'port': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        self.assertEqual({
            'name': 'dn42-abcdef',
            'port': 28888,
            'remote': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }, gen_wg_config('abcdef', cfg))

    def test_bird_config_mpbgp(self):
        cfg = {
            'asn': '123456',
            'port': 12345,
            'remote': 'abcd.efgh.ijkl:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=True, extended_next_hop=False, latency=10)

        expected = """protocol bgp testpeer_3456 from dnpeers {
    neighbor fe80::1234 as 123456;
    interface "dn42-testpeer";
    passive off;

    ipv4 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
        #extended next hop on;
    };
    ipv6 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('testpeer', cfg, bird_options).strip())

    def test_bird_config_mpbgp_enh(self):
        cfg = {
            'asn': '123456',
            'port': 12345,
            'remote': 'abcd.efgh.ijkl:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=True, extended_next_hop=True, latency=10)

        expected = """protocol bgp testpeer_3456 from dnpeers {
    neighbor fe80::1234 as 123456;
    interface "dn42-testpeer";
    passive off;

    ipv4 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
        extended next hop on;
    };
    ipv6 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('testpeer', cfg, bird_options).strip())

    def test_bird_config_mpbgp_passive(self):
        cfg = {
            'asn': '123456',
            'port': None,
            'remote': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=True, extended_next_hop=False, latency=10)

        expected = """protocol bgp testpeer_3456 from dnpeers {
    neighbor fe80::1234 as 123456;
    interface "dn42-testpeer";
    passive on;

    ipv4 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
        #extended next hop on;
    };
    ipv6 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('testpeer', cfg, bird_options).strip())


    def test_bird_config_dualstack_no_mpbgp(self):
        cfg = {
            'asn': '4201080001',
            'remote': 'example.com',
            'port': '123',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '10.0.0.1',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=False, latency=1.515)

        expected = """protocol bgp myTest_0001 from dnpeers {
    neighbor 10.0.0.1 as 4201080001;
    passive off;

    ipv4 {
        import where dn42_import_filter(1,24,34);
        export where dn42_export_filter(1,24,34);
        #extended next hop on;
    };
}

protocol bgp myTest_0001_v6 from dnpeers {
    neighbor fe80::1234 as 4201080001;
    interface "dn42-myTest";
    passive off;

    ipv6 {
        import where dn42_import_filter(1,24,34);
        export where dn42_export_filter(1,24,34);
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('myTest', cfg, bird_options).strip())

    def test_bird_config_v4_only(self):
        cfg = {
            'asn': '4242420001',
            'remote': 'test',
            'port': 11001,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '10.0.0.1',
            'peer_v6': None
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=False, latency=1.515)

        expected = """protocol bgp v4only_0001 from dnpeers {
    neighbor 10.0.0.1 as 4242420001;
    passive off;

    ipv4 {
        import where dn42_import_filter(1,24,34);
        export where dn42_export_filter(1,24,34);
        #extended next hop on;
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('v4only', cfg, bird_options).strip())

    def test_bird_config_v4_only_passive(self):
        cfg = {
            'asn': '4242420001',
            'remote': None,
            'port': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '10.0.0.1',
            'peer_v6': None
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=False, latency=1.515)

        expected = """protocol bgp v4only_0001 from dnpeers {
    neighbor 10.0.0.1 as 4242420001;
    passive on;

    ipv4 {
        import where dn42_import_filter(1,24,34);
        export where dn42_export_filter(1,24,34);
        #extended next hop on;
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('v4only', cfg, bird_options).strip())

    def test_bird_config_v6_only(self):
        cfg = {
            'asn': '4201080001',
            'remote': 'test',
            'port': 5555,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=False, latency=25)

        expected = """protocol bgp myTest_0001_v6 from dnpeers {
    neighbor fe80::1234 as 4201080001;
    interface "dn42-myTest";
    passive off;

    ipv6 {
        import where dn42_import_filter(4,24,34);
        export where dn42_export_filter(4,24,34);
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('myTest', cfg, bird_options).strip())

    def test_bird_config_v6_only_enh_passive(self):
        cfg = {
            'asn': '4201080001',
            'remote': None,
            'port': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=True, latency=25)

        expected = """protocol bgp myTest_0001 from dnpeers {
    neighbor fe80::1234 as 4201080001;
    interface "dn42-myTest";
    passive on;

    ipv4 {
        import where dn42_import_filter(4,24,34);
        export where dn42_export_filter(4,24,34);
        extended next hop on;
    };
    ipv6 {
        import where dn42_import_filter(4,24,34);
        export where dn42_export_filter(4,24,34);
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('myTest', cfg, bird_options).strip())



if __name__ == '__main__':
    unittest.main()
