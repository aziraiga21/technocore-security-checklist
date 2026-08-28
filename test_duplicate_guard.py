import json
import subprocess
import sys
import unittest

from duplicate_guard import DuplicateGuard, normalize_duplicate_text


class DuplicateGuardTests(unittest.TestCase):
    def test_normalization_matches_official_duplicate_equivalence(self):
        variants = [
            "Deploy  NOW",
            "deploy now",
            "ＤＥＰＬＯＹ\u200d\tNOW",
        ]

        self.assertEqual(
            [normalize_duplicate_text(text) for text in variants],
            ["deploy now", "deploy now", "deploy now"],
        )

    def test_sixth_normalized_copy_requires_rephrasing(self):
        guard = DuplicateGuard(window_seconds=60, max_copies=5, min_length=16)
        variants = [
            "Deploy the safe patch",
            "deploy  the safe patch",
            "ＤＥＰＬＯＹ THE SAFE PATCH",
            "deploy the safe\u200d patch",
            "DEPLOY THE SAFE PATCH",
            "deploy the safe patch",
        ]

        decisions = [guard.check("lobby", text, now=1000 + index) for index, text in enumerate(variants)]

        self.assertEqual([decision.action for decision in decisions[:5]], ["accept"] * 5)
        self.assertEqual(decisions[5].action, "rephrase")
        self.assertEqual(decisions[5].reason, "duplicate_copy_limit")

    def test_only_text_strictly_below_length_floor_is_exempt(self):
        guard = DuplicateGuard(window_seconds=60, max_copies=1, min_length=4)

        short = [guard.check("lobby", "abc", now=second) for second in (1, 2)]
        exact = [guard.check("lobby", "abcd", now=second) for second in (1, 2)]

        self.assertEqual([decision.action for decision in short], ["accept", "accept"])
        self.assertEqual([decision.action for decision in exact], ["accept", "rephrase"])

    def test_copy_budget_returns_after_window_expires(self):
        guard = DuplicateGuard(window_seconds=5, max_copies=1, min_length=1)

        first = guard.check("lobby", "repeat", now=10)
        inside_window = guard.check("lobby", "repeat", now=14.9)
        after_window = guard.check("lobby", "repeat", now=15)

        self.assertEqual(first.action, "accept")
        self.assertEqual(inside_window.action, "rephrase")
        self.assertEqual(after_window.action, "accept")

    def test_copy_budgets_are_isolated_by_room(self):
        guard = DuplicateGuard(window_seconds=60, max_copies=1, min_length=1)

        lobby = guard.check("lobby", "same message", now=1)
        project = guard.check("project", "same message", now=2)

        self.assertEqual(lobby.action, "accept")
        self.assertEqual(project.action, "accept")

    def test_cli_emits_machine_readable_decisions(self):
        result = subprocess.run(
            [
                sys.executable,
                "duplicate_guard.py",
                "--room",
                "lobby",
                "--window",
                "60",
                "--max-copies",
                "1",
                "--min-length",
                "1",
                "same message",
                "SAME  MESSAGE",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        decisions = [json.loads(line) for line in result.stdout.splitlines()]

        self.assertEqual([item["action"] for item in decisions], ["accept", "rephrase"])
        self.assertEqual(decisions[1]["reason"], "duplicate_copy_limit")


if __name__ == "__main__":
    unittest.main()
