#!/usr/bin/env python3
import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from utils import FakeInput
from peerconfgen import complete_peer_config

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

if __name__ == '__main__':
    unittest.main()
