import json
import subprocess
import sys
import unittest

from append_receipt_guard import ReceiptError, validate_append_receipt


class AppendReceiptGuardTests(unittest.TestCase):
    def test_accepts_exact_readback_but_rejects_official_compaction_loss_shape(self):
        posted = {"seq": 2, "ts": "2026-09-02T01:49:15.000000Z", "from": "bot", "text": "x" * 300}
        coherent = {
            "room": "lobby",
            "count": 1,
            "first_seq": 2,
            "last_seq": 2,
            "generation": 1,
            "messages": [posted],
            "posted": posted,
        }
        self.assertEqual(validate_append_receipt(coherent), posted)

        lost = {
            "room": "lobby",
            "count": 0,
            "first_seq": None,
            "last_seq": 0,
            "generation": 1,
            "messages": [],
            "posted": posted,
        }
        with self.assertRaisesRegex(ReceiptError, "posted record is absent"):
            validate_append_receipt(lost)

    def test_requires_one_exact_record_at_the_acknowledged_sequence(self):
        posted = {"seq": 7, "ts": "2026-09-02T01:49:15.000000Z", "from": "bot", "text": "paid"}
        base = {
            "room": "deals",
            "count": 1,
            "first_seq": 7,
            "last_seq": 7,
            "generation": 3,
            "posted": posted,
        }

        duplicate = {**base, "count": 2, "messages": [posted, posted]}
        with self.assertRaisesRegex(ReceiptError, "appears more than once"):
            validate_append_receipt(duplicate)

        mutated = {
            **base,
            "messages": [{**posted, "text": "redirected"}],
        }
        with self.assertRaisesRegex(ReceiptError, "does not exactly match"):
            validate_append_receipt(mutated)

    def test_rejects_malformed_response_shapes_as_receipt_errors(self):
        malformed = [
            None,
            [],
            {},
            {"posted": [], "messages": []},
            {"posted": {"seq": True}, "messages": []},
            {"posted": {"seq": 1}, "messages": {}},
            {"posted": {"seq": 1}, "messages": ["not-a-record"]},
        ]
        for response in malformed:
            with self.subTest(response=response):
                with self.assertRaises(ReceiptError):
                    validate_append_receipt(response)

    def test_rejects_incoherent_room_view_metadata(self):
        posted = {"seq": 8, "ts": "2026-09-02T01:49:15.000000Z", "from": "bot", "text": "ok"}
        valid = {
            "room": "lobby",
            "count": 1,
            "first_seq": 8,
            "last_seq": 8,
            "generation": 4,
            "messages": [posted],
            "posted": posted,
        }
        mutations = [
            {**valid, "room": ""},
            {**valid, "count": 2},
            {**valid, "first_seq": 7},
            {**valid, "last_seq": 9},
            {**valid, "generation": True},
            {**valid, "messages": [posted, {**posted, "seq": 7}], "count": 2, "last_seq": 7},
        ]
        for response in mutations:
            with self.subTest(response=response):
                with self.assertRaises(ReceiptError):
                    validate_append_receipt(response)

    def test_cli_verifies_stdin_and_fails_closed_without_tracebacks(self):
        posted = {"seq": 2, "ts": "2026-09-02T01:49:15.000000Z", "from": "bot", "text": "x"}
        valid = {
            "room": "lobby",
            "count": 1,
            "first_seq": 2,
            "last_seq": 2,
            "generation": 1,
            "messages": [posted],
            "posted": posted,
        }
        lost = {**valid, "count": 0, "first_seq": None, "last_seq": 0, "messages": []}

        accepted = subprocess.run(
            [sys.executable, "append_receipt_guard.py"],
            input=json.dumps(valid),
            capture_output=True,
            text=True,
            check=False,
        )
        refused = subprocess.run(
            [sys.executable, "append_receipt_guard.py"],
            input=json.dumps(lost),
            capture_output=True,
            text=True,
            check=False,
        )
        malformed = subprocess.run(
            [sys.executable, "append_receipt_guard.py"],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout), {"ok": True, "posted_seq": 2, "room": "lobby"})
        self.assertEqual(refused.returncode, 1)
        self.assertIn("posted record is absent", json.loads(refused.stdout)["findings"][0])
        self.assertEqual(malformed.returncode, 1)
        self.assertIn("valid JSON", json.loads(malformed.stdout)["findings"][0])
        self.assertEqual(accepted.stderr + refused.stderr + malformed.stderr, "")


if __name__ == "__main__":
    unittest.main()
