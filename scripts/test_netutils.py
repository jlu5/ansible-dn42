import unittest

from _netutils import get_ptr_zone

class TestGetPtrZone(unittest.TestCase):
    def test_ipv4(self):
        self.assertEqual(
            get_ptr_zone('172.20.0.0/16'), '20.172.in-addr.arpa'
        )
        self.assertEqual(
            get_ptr_zone('172.20.0.0/24'), '0.20.172.in-addr.arpa'
        )
        self.assertRaises(ValueError, lambda: get_ptr_zone('192.168.0.0/19'))

    def test_ipv4_rfc2317(self):
        self.assertEqual(
            get_ptr_zone('172.22.108.0/25'), '0/25.108.22.172.in-addr.arpa'
        )
        self.assertEqual(
            get_ptr_zone('172.22.108.128/27'), '128/27.108.22.172.in-addr.arpa'
        )
        self.assertEqual(
            get_ptr_zone('172.20.229.112/28', rfc2317_separator='-'),
                         '112-28.229.20.172.in-addr.arpa'
        )

    def test_ipv6(self):
        self.assertEqual(
            get_ptr_zone('fd00::/8'), 'd.f.ip6.arpa'
        )
        self.assertEqual(
            get_ptr_zone('fd86:bad:11b7::/48'), '7.b.1.1.d.a.b.0.6.8.d.f.ip6.arpa'
        )
        self.assertEqual(
            get_ptr_zone('fd86:bad:11b7:aaaa::/64'), 'a.a.a.a.7.b.1.1.d.a.b.0.6.8.d.f.ip6.arpa'
        )
        self.assertRaises(ValueError, lambda: get_ptr_zone('fc00::/7'))
