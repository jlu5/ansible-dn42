#!/usr/bin/env python3
import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from birdoptions import BirdOptions, fill_bird_options
from utils import FakeInput, get_dn42_latency_value

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

if __name__ == '__main__':
    unittest.main()
