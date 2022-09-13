#!/usr/bin/env python3
import pprint  # pylint: disable=unused-import
import unittest
import unittest.mock

from birdoptions import BirdOptions
from exporters import gen_wg_config, gen_bird_peer_config

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
            'asn': '64512',
            'port': 12345,
            'remote': 'abcd.efgh.ijkl:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::1234',
        }
        bird_options = BirdOptions(mp_bgp=True, extended_next_hop=False, latency=10)

        expected = """protocol bgp testpeer_64512 from dnpeers {
    neighbor fe80::1234 as 64512;
    interface "dn42-testpeer";
    passive off;

    ipv4 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
        extended next hop off;
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

        expected = """protocol bgp testpeer_123456 from dnpeers {
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

        expected = """protocol bgp testpeer_123456 from dnpeers {
    neighbor fe80::1234 as 123456;
    interface "dn42-testpeer";
    passive on;

    ipv4 {
        import where dn42_import_filter(3,24,34);
        export where dn42_export_filter(3,24,34);
        extended next hop off;
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
        extended next hop off;
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
            'asn': '4242421080',
            'remote': 'test',
            'port': 11001,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '10.0.0.1',
            'peer_v6': None
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=False, latency=1.515)

        expected = """protocol bgp v4only_1080 from dnpeers {
    neighbor 10.0.0.1 as 4242421080;
    passive off;

    ipv4 {
        import where dn42_import_filter(1,24,34);
        export where dn42_export_filter(1,24,34);
        extended next hop off;
    };
}
""".strip()
        self.assertEqual(expected, gen_bird_peer_config('v4only', cfg, bird_options).strip())

    def test_bird_config_v4_only_passive(self):
        cfg = {
            'asn': '4242421234',
            'remote': None,
            'port': None,
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '10.0.0.1',
            'peer_v6': None
        }
        bird_options = BirdOptions(mp_bgp=False, extended_next_hop=False, latency=1.515)

        expected = """protocol bgp v4only_1234 from dnpeers {
    neighbor 10.0.0.1 as 4242421234;
    passive on;

    ipv4 {
        import where dn42_import_filter(1,24,34);
        export where dn42_export_filter(1,24,34);
        extended next hop off;
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

    def test_bird_config_prefix_numeric_peername(self):
        cfg = {
            'asn': '123456',
            'port': 12345,
            'remote': 'abcd.efgh.ijkl:21080',
            'wg_pubkey': 'dn42' * 10 + 'dn4=',
            'peer_v4': '172.22.108.88',
            'peer_v6': 'fe80::9999',
        }
        bird_options = BirdOptions(mp_bgp=True, extended_next_hop=True, latency=10)

        self.assertIn("protocol bgp _99999999_123456", gen_bird_peer_config('99999999', cfg, bird_options))

if __name__ == '__main__':
    unittest.main()
