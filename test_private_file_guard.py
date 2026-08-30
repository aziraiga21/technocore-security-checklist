import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from private_file_guard import audit_private_file


class PrivateFileGuardTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX permission assertion")
    def test_owner_only_regular_file_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "identity.pem")
            path.write_text("encrypted test material", encoding="utf-8")
            path.chmod(0o600)

            result = audit_private_file(path)

            self.assertTrue(result["ok"])
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["mode"], "0600")

    @unittest.skipIf(os.name == "nt", "POSIX permission assertion")
    def test_group_or_other_access_fails_with_exact_exposure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "x25519.pem")
            path.write_text("encrypted test material", encoding="utf-8")
            path.chmod(0o640)

            result = audit_private_file(path)

            self.assertFalse(result["ok"])
            self.assertIn("group/other permission bits are 0040", result["findings"])

    @unittest.skipIf(os.name == "nt", "POSIX file-type assertion")
    def test_symlink_is_not_accepted_as_a_private_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "identity.pem")
            target.write_text("encrypted test material", encoding="utf-8")
            target.chmod(0o600)
            link = Path(directory, "current.pem")
            link.symlink_to(target)

            result = audit_private_file(link)

            self.assertFalse(result["ok"])
            self.assertIn("path is not a regular file", result["findings"])

    @unittest.skipIf(os.name == "nt", "POSIX ownership assertion")
    def test_file_owned_by_another_uid_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "identity.pem")
            path.write_text("encrypted test material", encoding="utf-8")
            path.chmod(0o600)
            foreign_uid = os.getuid() + 1

            result = audit_private_file(path, expected_uid=foreign_uid)

            self.assertFalse(result["ok"])
            self.assertIn(
                f"owner uid {os.getuid()} does not match expected uid {foreign_uid}",
                result["findings"],
            )

    def test_windows_fails_closed_instead_of_trusting_posix_mode_bits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "identity.pem")
            path.write_text("encrypted test material", encoding="utf-8")
            path.chmod(0o600)

            result = audit_private_file(path, platform="win32")

            self.assertFalse(result["ok"])
            self.assertIsNone(result["mode"])
            self.assertIn(
                "Windows ACL not verified; POSIX mode bits are not a security boundary",
                result["findings"],
            )

    @unittest.skipIf(os.name == "nt", "POSIX CLI assertion")
    def test_cli_emits_json_and_zero_for_owner_only_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "identity.pem")
            path.write_text("encrypted test material", encoding="utf-8")
            path.chmod(0o600)

            completed = subprocess.run(
                [sys.executable, "private_file_guard.py", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0)
            self.assertTrue(json.loads(completed.stdout)["ok"])

    @unittest.skipIf(os.name == "nt", "POSIX CLI assertion")
    def test_cli_returns_nonzero_for_exposed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "identity.pem")
            path.write_text("encrypted test material", encoding="utf-8")
            path.chmod(0o644)

            completed = subprocess.run(
                [sys.executable, "private_file_guard.py", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertFalse(json.loads(completed.stdout)["ok"])

    def test_cli_reports_missing_file_as_json_without_traceback(self):
        completed = subprocess.run(
            [sys.executable, "private_file_guard.py", "does-not-exist.pem"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertFalse(json.loads(completed.stdout)["ok"])
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
