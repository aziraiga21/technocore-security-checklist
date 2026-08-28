import json
import unittest
from pathlib import Path


class ChecklistTests(unittest.TestCase):
    def test_every_machine_control_is_documented(self):
        root = Path(__file__).parent
        data = json.loads((root / "checklist.json").read_text())
        document = (root / "SECURITY_CHECKLIST.md").read_text().lower().replace("`", "")
        phrases = {
            "seed_mode_0600": "0600",
            "no_seed_output": "never print seeds",
            "unicode_sweep_before_signing": "before signing",
            "canonical_room_nonce_text": "<room>|<nonce>|<swept-text>",
            "unpadded_base64url_signature": "unpadded base64url",
            "monotonic_nonce": "monotonically increasing",
            "exact_receipt_readback": "exact matches",
            "bounded_retry": "with bounds",
            "explicit_note_cap_fallback": "note limit reached",
            "duplicate_422_rephrase": "422 duplicate refusal",
        }
        self.assertEqual(set(data["required_controls"]), set(phrases))
        for control, phrase in phrases.items():
            with self.subTest(control=control):
                self.assertIn(phrase, document)


if __name__ == "__main__":
    unittest.main()
