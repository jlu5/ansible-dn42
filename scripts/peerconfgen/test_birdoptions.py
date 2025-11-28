#!/usr/bin/env python3
import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from birdoptions import BirdOptions, fill_bird_options
from exceptions import AbortError
from utils import FakeInput

class PeerConfFillBirdTest(unittest.TestCase):
    maxDiff = None

    cfg_dualstack = {
        'asn': '4242428888',
        'remote': 'test.null.invalid',
        'port': '8888',
        'wg_pubkey': 'dn42' * 10 + 'dn4=',
        'peer_v4': '172.22.108.88',
        'peer_v6': 'fe80::1234',
    }
    cfg_v6_only = {
        'asn': '4242428888',
        'remote': 'test.null.invalid',
        'port': '8888',
        'wg_pubkey': 'dn42' * 10 + 'dn4=',
        'peer_v4': None,
        'peer_v6': 'fe80::1234',
    }

    @unittest.mock.patch('builtins.input', FakeInput([
        'n',  # No extended next hop
    ]))
    def test_fill_bird_options_v6only(self):
        with unittest.mock.patch('birdoptions.get_rtt', return_value=0.909):
            self.assertEqual(BirdOptions(False, False),
                             fill_bird_options(None, self.cfg_v6_only))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',  # mp-bgp
        'n',  # extended next hop
    ]))
    def test_fill_bird_options_dualstack(self):
        with unittest.mock.patch('birdoptions.get_rtt', return_value=0.909):
            self.assertEqual(BirdOptions(True, False),
                             fill_bird_options(None, self.cfg_dualstack))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',  # mp-bgp
        'y',  # extended next hop
        'y',  # continue despite high ping
    ]))
    def test_fill_bird_options_high_ping(self):
        with unittest.mock.patch('birdoptions.get_rtt', return_value=200):
            self.assertEqual(BirdOptions(True, True),
                             fill_bird_options(None, self.cfg_dualstack))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',  # mp-bgp
        'y',  # extended next hop
        'n',  # abort because of high ping
    ]))
    def test_fill_bird_options_high_ping_abort(self):
        with unittest.mock.patch('birdoptions.get_rtt', return_value=200):
            with self.assertRaises(AbortError):
                self.assertEqual(BirdOptions(True, True),
                                fill_bird_options(None, self.cfg_dualstack))

    @unittest.mock.patch('builtins.input', FakeInput([
        'y',  # mp-bgp
        'y',  # extended next hop
        'n',  # abort because of failed ping
    ]))
    def test_fill_bird_options_failed_ping_abort(self):
        with unittest.mock.patch('birdoptions.get_rtt',
                side_effect=OSError("placeholder exception for testing")):
            with self.assertRaises(AbortError):
                self.assertEqual(BirdOptions(True, True),
                                fill_bird_options(None, self.cfg_dualstack))

if __name__ == '__main__':
    unittest.main()
