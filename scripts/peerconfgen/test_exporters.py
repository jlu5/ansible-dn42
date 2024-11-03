#!/usr/bin/env python3
import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from birdoptions import BirdOptions
from exporters import gen_peer_config

class PeerConfWriteTest(unittest.TestCase):
    maxDiff = None

    def test_export_two_sessions(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(
            mp_bgp=False,
            extended_next_hop=False,
        )
        self.assertEqual({
            'name': 'dn42-somelongna',
            'port': 28888,
            'remote': 'test.null.invalid:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
            'bgp': {
                'asn': 4242428888,
                'ipv4': True,
                'ipv6': True,
                'mp_bgp': False,
                'extended_next_hop': False,
            }
        }, gen_peer_config('somelongname', cfg, bird_options))

    def test_export_no_remote(self):
        cfg = {
            'asn': '4242429876',
            'remote': None,
            'port': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(
            mp_bgp=False,
            extended_next_hop=False,
        )
        self.assertEqual({
            'name': 'dn42-abcdef',
            'port': 29876,
            'remote': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
            'bgp': {
                'asn': 4242429876,
                'ipv4': True,
                'ipv6': True,
                'mp_bgp': False,
                'extended_next_hop': False,
            }
        }, gen_peer_config('abcdef', cfg, bird_options))

    def test_export_mp_bgp(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(
            mp_bgp=True,
            extended_next_hop=False,
        )
        self.assertEqual({
            'name': 'dn42-abcdef',
            'port': 28888,
            'remote': 'test.null.invalid:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
            'bgp': {
                'asn': 4242428888,
                'ipv4': True,
                'ipv6': True,
                'mp_bgp': True,
                'extended_next_hop': False,
            }
        }, gen_peer_config('abcdef', cfg, bird_options))

    def test_export_mp_bgp_enh(self):
        cfg = {
            'asn': '4242424242',
            'remote': None,
            'port': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(
            mp_bgp=True,
            extended_next_hop=True,
        )
        self.assertEqual({
            'name': 'dn42-abcdef',
            'port': 24242,
            'remote': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fe80::1234',
            'bgp': {
                'asn': 4242424242,
                'ipv4': True,
                'ipv6': True,
                'mp_bgp': True,
                'extended_next_hop': True,
            }
        }, gen_peer_config('abcdef', cfg, bird_options))

    def test_export_v4_only(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': None,
        }
        bird_options = BirdOptions(
            mp_bgp=False,
            extended_next_hop=False,
        )
        self.assertEqual({
            'name': 'dn42-somelongna',
            'port': 28888,
            'remote': 'test.null.invalid:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': None,
            'bgp': {
                'asn': 4242428888,
                'ipv4': True,
                'ipv6': False,
                'mp_bgp': False,
                'extended_next_hop': False,
            }
        }, gen_peer_config('somelongname', cfg, bird_options))

    def test_export_v6_only(self):
        cfg = {
            'asn': '4242428888',
            'remote': 'test.null.invalid',
            'port': '21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fd86:11b7:bad::4242',
        }
        bird_options = BirdOptions(
            mp_bgp=False,
            extended_next_hop=False,
        )
        self.assertEqual({
            'name': 'dn42-somelongna',
            'port': 28888,
            'remote': 'test.null.invalid:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fd86:11b7:bad::4242',
            'bgp': {
                'asn': 4242428888,
                'ipv4': False,
                'ipv6': True,
                'mp_bgp': False,
                'extended_next_hop': False,
            }
        }, gen_peer_config('somelongname', cfg, bird_options))

    def test_export_inet_asn(self):
        cfg = {
            'asn': '123456',
            'remote': 'test.null.invalid',
            'port': '21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fd86:11b7:bad::4242',
        }
        bird_options = BirdOptions(
            mp_bgp=False,
            extended_next_hop=False,
        )
        self.assertEqual({
            'name': 'dn42-testnet',
            'port': 23456,
            'remote': 'test.null.invalid:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': None,
            'peer_v6': 'fd86:11b7:bad::4242',
            'bgp': {
                'asn': 123456,
                'ipv4': False,
                'ipv6': True,
                'mp_bgp': False,
                'extended_next_hop': False,
            }
        }, gen_peer_config('testnet', cfg, bird_options))

if __name__ == '__main__':
    unittest.main()
