import json
import subprocess
import sys
import unittest

from rooms_cache_key_guard import CacheKeyError, canonical_rooms_key


class RoomsCacheKeyGuardTests(unittest.TestCase):
    def test_collapses_attacker_query_churn_onto_the_reply_space(self):
        expected = "https://technocore.chat/rooms?limit=200"
        aliases = [
            "https://technocore.chat/rooms?limit=200",
            "https://technocore.chat/rooms?limit=999999999",
            "https://technocore.chat/rooms?limit=200&ignored=1",
            "https://technocore.chat/rooms?ignored=2&limit=999999999",
        ]
        for url in aliases:
            with self.subTest(url=url):
                self.assertEqual(canonical_rooms_key(url, max_limit=200), expected)

    def test_preserves_only_reply_selecting_format_and_normalizes_the_origin(self):
        self.assertEqual(
            canonical_rooms_key(
                "HTTPS://TECHNOCORE.CHAT:443/rooms?format=json&tracking=1", max_limit=200
            ),
            "https://technocore.chat/rooms?format=json",
        )
        self.assertEqual(
            canonical_rooms_key("http://TECHNOCORE.CHAT:80/rooms?format=text", max_limit=200),
            "http://technocore.chat/rooms",
        )

    def test_rejects_requests_outside_the_shareable_grammar(self):
        invalid = [
            ({"url": "https://technocore.chat/not-rooms"}, "path"),
            ({"url": "https://user@technocore.chat/rooms"}, "userinfo"),
            ({"url": "https://technocore.chat/rooms#fragment"}, "fragment"),
            ({"url": "https://technocore.chat/rooms?limit=1&limit=2"}, "duplicate"),
            ({"url": "https://technocore.chat/rooms?format=json&format=text"}, "duplicate"),
            ({"url": "https://technocore.chat/rooms?limit=+1"}, "ASCII digits"),
            ({"url": "https://technocore.chat/rooms?limit=１２"}, "ASCII digits"),
            ({"url": "https://technocore.chat/rooms?limit=1_0"}, "ASCII digits"),
            ({"url": "https://technocore.chat/rooms?limit=0000000001"}, "ASCII digits"),
            ({"url": "rooms?limit=1"}, "absolute"),
            ({"url": "https://technocore.chat/rooms", "method": "POST"}, "GET"),
            ({"url": "https://technocore.chat/rooms", "max_limit": True}, "max_limit"),
            ({"url": "https://technocore.chat/rooms", "max_limit": 0}, "max_limit"),
            (
                {"url": "https://technocore.chat/rooms?" + "&".join(f"x{i}=1" for i in range(101))},
                "too many",
            ),
        ]
        for arguments, finding in invalid:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(CacheKeyError, finding):
                    canonical_rooms_key(**arguments)

    def test_cli_emits_a_machine_decision_and_fails_closed(self):
        accepted = subprocess.run(
            [
                sys.executable,
                "rooms_cache_key_guard.py",
                "https://technocore.chat/rooms?noise=7&limit=999&format=json",
                "--max-limit",
                "200",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        refused = subprocess.run(
            [sys.executable, "rooms_cache_key_guard.py", "https://technocore.chat/rooms?limit=%EF%BC%91"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(
            json.loads(accepted.stdout),
            {
                "cache_key": "https://technocore.chat/rooms?format=json&limit=200",
                "ok": True,
                "shareable": True,
            },
        )
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(json.loads(refused.stdout)["shareable"], False)
        self.assertIn("ASCII digits", json.loads(refused.stdout)["findings"][0])
        self.assertEqual(accepted.stderr + refused.stderr, "")


if __name__ == "__main__":
    unittest.main()
