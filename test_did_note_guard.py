import json
import subprocess
import sys
import unittest

from did_note_guard import DidNoteError, parse_did_note


DID = "did:key:z6Mkexampleidentity"
CANONICAL_KEY = "BwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwc"


class DidNoteGuardTests(unittest.TestCase):
    def test_accepts_canonical_note_and_binds_expected_did(self):
        note = parse_did_note(
            f"{DID} x25519:{CANONICAL_KEY} mailbox:p-agent-inbox",
            expected_did=DID,
        )

        self.assertEqual(note.did, DID)
        self.assertEqual(note.x25519, CANONICAL_KEY)
        self.assertEqual(note.mailbox, "p-agent-inbox")
        self.assertEqual(
            note.fields,
            {"x25519": CANONICAL_KEY, "mailbox": "p-agent-inbox"},
        )

    def test_rejects_punctuation_injected_x25519_accepted_by_node_buffer(self):
        injected = CANONICAL_KEY[:10] + "!" + CANONICAL_KEY[10:]

        with self.assertRaisesRegex(DidNoteError, "canonical unpadded base64url"):
            parse_did_note(
                f"{DID} x25519:{injected} mailbox:p-agent-inbox",
                expected_did=DID,
            )

    def test_rejects_padded_short_and_noncanonical_x25519_spellings(self):
        cases = {
            "padding": CANONICAL_KEY + "=",
            "wrong decoded length": CANONICAL_KEY[:-1],
            "nonzero unused bits": CANONICAL_KEY[:-1] + "x",
        }
        for label, key in cases.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(DidNoteError, "canonical unpadded base64url"):
                    parse_did_note(
                        f"{DID} x25519:{key} mailbox:p-agent-inbox",
                        expected_did=DID,
                    )

    def test_rejects_note_whose_did_does_not_match_lookup_path(self):
        with self.assertRaisesRegex(DidNoteError, "does not match expected DID"):
            parse_did_note(
                f"did:key:z6Mkattacker x25519:{CANONICAL_KEY} mailbox:p-agent-inbox",
                expected_did=DID,
            )

    def test_rejects_duplicate_fields_instead_of_last_value_wins(self):
        with self.assertRaisesRegex(DidNoteError, "duplicate field: mailbox"):
            parse_did_note(
                f"{DID} x25519:{CANONICAL_KEY} mailbox:p-safe mailbox:p-attacker",
                expected_did=DID,
            )

    def test_rejects_ambiguous_or_incomplete_note_structure(self):
        cases = {
            "multiline": f"ignored banner\n{DID} x25519:{CANONICAL_KEY} mailbox:p-safe",
            "malformed field": f"{DID} x25519:{CANONICAL_KEY} mailbox",
            "missing x25519": f"{DID} mailbox:p-safe",
            "missing mailbox": f"{DID} x25519:{CANONICAL_KEY}",
        }
        for label, value in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(DidNoteError):
                    parse_did_note(value, expected_did=DID)

    def test_rejects_mailbox_outside_room_name_grammar(self):
        with self.assertRaisesRegex(DidNoteError, "mailbox must match"):
            parse_did_note(
                f"{DID} x25519:{CANONICAL_KEY} mailbox:../Admin",
                expected_did=DID,
            )

    def test_cli_emits_canonical_json_for_valid_note(self):
        completed = subprocess.run(
            [
                sys.executable,
                "did_note_guard.py",
                "--expected-did",
                DID,
                f"{DID} x25519:{CANONICAL_KEY} mailbox:p-agent-inbox",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "did": DID,
                "fields": {"mailbox": "p-agent-inbox", "x25519": CANONICAL_KEY},
                "mailbox": "p-agent-inbox",
                "ok": True,
                "x25519": CANONICAL_KEY,
            },
        )

    def test_cli_fails_closed_with_json_finding_and_no_traceback(self):
        injected = CANONICAL_KEY[:10] + "!" + CANONICAL_KEY[10:]
        completed = subprocess.run(
            [
                sys.executable,
                "did_note_guard.py",
                "--expected-did",
                DID,
                f"{DID} x25519:{injected} mailbox:p-agent-inbox",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("canonical unpadded base64url", result["findings"][0])


if __name__ == "__main__":
    unittest.main()
