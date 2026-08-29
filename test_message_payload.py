import json
import subprocess
import sys
import unittest

from message_payload import build_message_payload, clean_signed_text


class SignedPayloadTests(unittest.TestCase):
    def test_clean_signed_text_matches_official_server_vectors(self):
        vectors = [
            ("  padded  ", "padded"),
            ("\nhi\n", "hi"),
            ("\ufeffhi", "hi"),  # Cf
            ("a\ue000b", "a b"),  # Co
            ("co\u00adoperate", "co operate"),  # Cf
            ("a\u2028b", "a b"),  # Zl
            ("a\u2029b", "a b"),  # Zp
            ("rocket \U0001f680 here", "rocket \U0001f680 here"),
            ("a\u00a0b", "a\u00a0b"),  # Zs is deliberately not swept
        ]

        for raw, expected in vectors:
            with self.subTest(raw=raw):
                self.assertEqual(clean_signed_text(raw), expected)

    def test_build_message_payload_signs_cleaned_utf8_bytes(self):
        built = build_message_payload("lobby", "42", "  co\u00adoperate \U0001f680  ")

        self.assertEqual(built.room, "lobby")
        self.assertEqual(built.nonce, "42")
        self.assertEqual(built.text, "co operate \U0001f680")
        self.assertEqual(built.payload, "lobby|42|co operate \U0001f680".encode("utf-8"))

    def test_build_message_payload_rejects_invalid_protocol_fields(self):
        invalid_cases = [
            ("../lobby", "1", "hello", "room"),
            ("lobby", "1e3", "hello", "nonce"),
            ("lobby", "12345678901234567890", "hello", "nonce"),
            ("lobby", "1", "\u200b\u200d\ufeff", "empty"),
            ("lobby", "1", "x" * 4097, "4096"),
        ]

        for room, nonce, text, message in invalid_cases:
            with self.subTest(room=room, nonce=nonce, message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_message_payload(room, nonce, text)

    def test_cli_emits_cleaned_text_and_exact_payload_hex(self):
        result = subprocess.run(
            [sys.executable, "message_payload.py", "lobby", "42", "  co\u00adoperate  "],
            check=True,
            capture_output=True,
            text=True,
        )

        output = json.loads(result.stdout)
        self.assertEqual(output["text"], "co operate")
        self.assertEqual(output["payload_utf8"], "lobby|42|co operate")
        self.assertEqual(output["payload_hex"], b"lobby|42|co operate".hex())

    def test_cli_rejects_bad_input_without_a_traceback(self):
        result = subprocess.run(
            [sys.executable, "message_payload.py", "../lobby", "42", "hello"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("room must match", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
