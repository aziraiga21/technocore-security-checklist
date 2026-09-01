import json
import subprocess
import sys
import unittest

from public_origin_guard import OriginError, validate_public_origin


class PublicOriginGuardTests(unittest.TestCase):
    def test_accepts_canonical_host_but_rejects_official_trailing_newline_abuse(self):
        self.assertEqual(
            validate_public_origin("https", "example.com"),
            "https://example.com",
        )

        with self.assertRaisesRegex(OriginError, "authority"):
            validate_public_origin("https", "example.com\n")

    def test_accepts_and_canonicalizes_supported_authorities(self):
        cases = {
            ("HTTPS", "API.Example.COM:443"): "https://api.example.com:443",
            ("http", "192.0.2.8:8080"): "http://192.0.2.8:8080",
            ("https", "[2001:0DB8::1]:8443"): "https://[2001:db8::1]:8443",
        }
        for inputs, expected in cases.items():
            with self.subTest(inputs=inputs):
                self.assertEqual(validate_public_origin(*inputs), expected)

    def test_rejects_authority_injection_and_ambiguous_network_names(self):
        cases = {
            "control suffix": ("https", "example.com\r"),
            "userinfo": ("https", "safe.example@attacker.example"),
            "path": ("https", "example.com/admin"),
            "query": ("https", "example.com?next=attacker"),
            "fragment": ("https", "example.com#attacker"),
            "empty port": ("https", "example.com:"),
            "zero port": ("https", "example.com:0"),
            "oversized port": ("https", "example.com:65536"),
            "ambiguous IPv4": ("https", "999.999.999.999"),
            "unbracketed IPv6": ("https", "2001:db8::1"),
            "non-http scheme": ("ftp", "example.com"),
        }
        for label, inputs in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(OriginError):
                    validate_public_origin(*inputs)

    def test_cli_emits_deterministic_json_and_fails_closed_without_traceback(self):
        accepted = subprocess.run(
            [sys.executable, "public_origin_guard.py", "https", "Example.COM"],
            check=False,
            capture_output=True,
            text=True,
        )
        refused = subprocess.run(
            [sys.executable, "public_origin_guard.py", "https", "example.com\n"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(accepted.stderr, "")
        self.assertEqual(
            json.loads(accepted.stdout),
            {"ok": True, "origin": "https://example.com"},
        )
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(refused.stderr, "")
        finding = json.loads(refused.stdout)
        self.assertEqual(finding["ok"], False)
        self.assertEqual(len(finding["findings"]), 1)
        self.assertIn("authority", finding["findings"][0])


if __name__ == "__main__":
    unittest.main()
