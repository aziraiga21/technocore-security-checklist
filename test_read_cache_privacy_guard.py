import json
import subprocess
import sys
import unittest

from read_cache_privacy_guard import CachePrivacyError, validate_read_response


class ReadCachePrivacyGuardTests(unittest.TestCase):
    def test_rejects_sharing_one_callers_budget_footer(self):
        response = {
            "method": "GET",
            "path": "/kv/e-status/current",
            "status": 200,
            "headers": {"cache-control": "public, max-age=0, s-maxage=1, stale-while-revalidate=5"},
            "body": "technocore\n\nready\n# budget: 24 of 600 reads left this minute (refills 10/s; a 429 states the wait, and the full limits are in /.well-known/agent.json)",
        }

        with self.assertRaisesRegex(CachePrivacyError, "caller-specific budget footer"):
            validate_read_response(response)

    def test_accepts_shareable_plain_reads_on_the_official_cache_lanes(self):
        for path in ("/rooms", "/r/lobby", "/kv/e-status", "/kv/e-status/current"):
            with self.subTest(path=path):
                self.assertEqual(
                    validate_read_response(
                        {
                            "method": "GET",
                            "path": path,
                            "status": 200,
                            "headers": {
                                "cache-control": "public, max-age=0, s-maxage=1, stale-while-revalidate=5"
                            },
                            "body": "technocore\n\nready",
                        }
                    ),
                    {"ok": True, "private": False, "route": "read", "shareable": True},
                )

    def test_rejects_malformed_or_out_of_scope_response_envelopes(self):
        invalid = [
            ({}, "exactly"),
            ({"method": "POST", "path": "/rooms", "status": 200, "headers": {}, "body": ""}, "GET"),
            ({"method": "GET", "path": "/health", "status": 200, "headers": {}, "body": ""}, "route"),
            ({"method": "GET", "path": "/rooms", "status": True, "headers": {}, "body": ""}, "status"),
            ({"method": "GET", "path": "/rooms", "status": 200, "headers": [], "body": ""}, "headers"),
            ({"method": "GET", "path": "/rooms", "status": 200, "headers": {}, "body": 7}, "body"),
            (
                {
                    "method": "GET",
                    "path": "/rooms",
                    "status": 200,
                    "headers": {"Cache-Control": "no-store", "cache-control": "s-maxage=1"},
                    "body": "",
                },
                "duplicate header",
            ),
        ]
        for response, finding in invalid:
            with self.subTest(response=response):
                with self.assertRaisesRegex(CachePrivacyError, finding):
                    validate_read_response(response)

    def test_requires_no_store_for_every_caller_specific_response(self):
        private = {
            "method": "GET",
            "path": "/kv/e-status/current",
            "status": 200,
            "headers": {"cache-control": "no-store"},
            "body": "technocore\n\nready\n# budget: 24 of 600 reads left this minute (refills 10/s; a 429 states the wait, and the full limits are in /.well-known/agent.json)",
        }
        self.assertEqual(
            validate_read_response(private),
            {"ok": True, "private": True, "route": "read", "shareable": False},
        )
        private["headers"] = {}
        with self.assertRaisesRegex(CachePrivacyError, "must be no-store"):
            validate_read_response(private)

    def test_rejects_sharing_a_room_long_poll_even_without_a_footer(self):
        long_poll = {
            "method": "GET",
            "path": "/r/lobby?since=41&wait=0.5",
            "status": 200,
            "headers": {"cache-control": "public, max-age=0, s-maxage=1"},
            "body": '{"messages":[],"wait_held":true}',
        }
        with self.assertRaisesRegex(CachePrivacyError, "long-poll"):
            validate_read_response(long_poll)

        long_poll["headers"] = {"cache-control": "no-store"}
        self.assertEqual(
            validate_read_response(long_poll),
            {"ok": True, "private": True, "route": "read", "shareable": False},
        )

    def test_does_not_treat_user_content_as_an_official_budget_footer(self):
        self.assertEqual(
            validate_read_response(
                {
                    "method": "GET",
                    "path": "/kv/e-status/current",
                    "status": 200,
                    "headers": {"cache-control": "public, max-age=0, s-maxage=1"},
                    "body": "technocore\n\n# budget: user-authored text\nnot a server footer",
                }
            )["private"],
            False,
        )

    def test_rejects_contradictory_or_malformed_shared_cache_directives(self):
        bad_values = [
            "public, max-age=0, s-maxage=1, no-store",
            "max-age=0, s-maxage=1",
            "public, max-age=1, s-maxage=1",
            "public, max-age=0, s-maxage=0",
            "public, max-age=0, s-maxage=-1",
            "public, max-age=0, s-maxage=soon",
            "public, max-age=0, s-maxage=1, s-maxage=2",
        ]
        for value in bad_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(CachePrivacyError, "cache-control"):
                    validate_read_response(
                        {
                            "method": "GET",
                            "path": "/kv/e-status/current",
                            "status": 200,
                            "headers": {"cache-control": value},
                            "body": "technocore\n\nready",
                        }
                    )

    def test_rejects_sharing_error_responses(self):
        for status in (204, 404, 429, 500):
            with self.subTest(status=status):
                with self.assertRaisesRegex(CachePrivacyError, "successful 200"):
                    validate_read_response(
                        {
                            "method": "GET",
                            "path": "/kv/e-status/current",
                            "status": status,
                            "headers": {"cache-control": "public, max-age=0, s-maxage=1"},
                            "body": "error",
                        }
                    )

    def test_cli_emits_deterministic_machine_decisions_and_fails_closed(self):
        accepted_envelope = {
            "method": "GET",
            "path": "/kv/e-status/current",
            "status": 200,
            "headers": {"Cache-Control": "public, max-age=0, s-maxage=1"},
            "body": "technocore\n\nready",
        }
        refused_envelope = {
            **accepted_envelope,
            "body": "technocore\n\nready\n# budget: 24 of 600 reads left this minute (refills 10/s; a 429 states the wait, and the full limits are in /.well-known/agent.json)",
        }
        accepted = subprocess.run(
            [sys.executable, "read_cache_privacy_guard.py"],
            input=json.dumps(accepted_envelope),
            capture_output=True,
            text=True,
            check=False,
        )
        refused = subprocess.run(
            [sys.executable, "read_cache_privacy_guard.py"],
            input=json.dumps(refused_envelope),
            capture_output=True,
            text=True,
            check=False,
        )
        malformed = subprocess.run(
            [sys.executable, "read_cache_privacy_guard.py"],
            input="not-json",
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(accepted.returncode, 0)
        self.assertEqual(
            json.loads(accepted.stdout),
            {"ok": True, "private": False, "route": "read", "shareable": True},
        )
        for result in (refused, malformed):
            self.assertEqual(result.returncode, 1)
            decision = json.loads(result.stdout)
            self.assertEqual(decision["ok"], False)
            self.assertEqual(decision["shareable"], False)
            self.assertTrue(decision["findings"])
        self.assertEqual(accepted.stderr + refused.stderr + malformed.stderr, "")


if __name__ == "__main__":
    unittest.main()
