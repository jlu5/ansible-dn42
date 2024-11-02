#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

path = pathlib.Path(__file__).parent.parent / 'filter_plugins' / 'network_utils.py'
network_utils = import_from_path('network_utils', path)

class TestNetworkUtils(unittest.TestCase):
    def test_peer_v4(self):
        config = {
            'peer_v4': '172.22.108.5',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 4),
            '172.22.108.5',
        )

        config = {
            'peer_v4': '172.22.108.10/31',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 4),
            '172.22.108.10',
        )

        with self.assertRaises(ValueError):
            network_utils.get_dn42_remote_ip({}, 4)

    def test_peer_v6(self):
        config = {
            'peer_v6': 'fe80::1/64',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 6),
            'fe80::1',
        )

        config = {
            'peer_v6': 'fd00:1122:3344:5566:7788:99aa:bbcc:ddee',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 6),
            'fd00:1122:3344:5566:7788:99aa:bbcc:ddee',
        )

        with self.assertRaises(ValueError):
            network_utils.get_dn42_remote_ip({}, 6)

    def test_local_v4(self):
        config = {
            'local_v4': '169.254.108.22/31',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 4),
            '169.254.108.23',
        )

        config = {
            'local_v4': '169.254.108.53/30',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 4),
            '169.254.108.54',
        )

        # Range too big to guess an IP
        config = {
            'local_v4': '169.254.108.54/28',
        }
        with self.assertRaises(ValueError):
            network_utils.get_dn42_remote_ip(config, 4)

        # Using the network address is erroneous
        config = {
            'local_v4': '169.254.108.52/30',
        }
        with self.assertRaises(ValueError):
            network_utils.get_dn42_remote_ip(config, 4)

        # Using the broadcast address is erroneous
        config = {
            'local_v4': '169.254.108.55/30',
        }
        with self.assertRaises(ValueError):
            network_utils.get_dn42_remote_ip(config, 4)

    def test_local_v6(self):
        config = {
            'local_v6': 'fd00::3/127',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 6),
            'fd00::2',
        )

        config = {
            'local_v6': 'fd00::4/127',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 6),
            'fd00::5',
        )

        # Does anyone actually use this?!
        config = {
            'local_v6': 'fd00::5/126',
        }
        self.assertEqual(
            network_utils.get_dn42_remote_ip(config, 6),
            'fd00::6',
        )

        # Range too big to guess an IP
        config = {
            'local_v6': 'fd00::6/64',
        }
        with self.assertRaises(ValueError):
            network_utils.get_dn42_remote_ip(config, 6)

if __name__ == '__main__':
    unittest.main()
