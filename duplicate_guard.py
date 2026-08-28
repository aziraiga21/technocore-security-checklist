"""Local preflight guard for Technocore 0.10 duplicate room writes."""

from __future__ import annotations

import argparse
import json
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import asdict, dataclass

_INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    copies_in_window: int


class DuplicateGuard:
    """Preflight normalized-exact duplicate writes before they consume a request."""

    def __init__(self, *, window_seconds: float, max_copies: int, min_length: int) -> None:
        if window_seconds < 0 or max_copies < 1 or min_length < 0:
            raise ValueError("window_seconds/min_length must be non-negative and max_copies positive")
        self.window_seconds = window_seconds
        self.max_copies = max_copies
        self.min_length = min_length
        self._copies: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, room: str, text: str, *, now: float) -> Decision:
        normalized = normalize_duplicate_text(text)
        if len(normalized) < self.min_length:
            return Decision("accept", "below_length_floor", 0)
        copies = self._copies[(room, normalized)]
        cutoff = now - self.window_seconds
        while copies and copies[0] <= cutoff:
            copies.popleft()
        if len(copies) >= self.max_copies:
            return Decision("rephrase", "duplicate_copy_limit", len(copies))
        copies.append(now)
        return Decision("accept", "within_copy_limit", len(copies))


def normalize_duplicate_text(text: str) -> str:
    """Return the normalized-exact form used by Technocore's duplicate filter."""
    compatible = unicodedata.normalize("NFKC", text)
    swept = "".join(
        " " if unicodedata.category(character) in _INVISIBLE_CATEGORIES else character
        for character in compatible
    )
    return " ".join(swept.casefold().split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--room", required=True)
    parser.add_argument("--window", type=float, required=True)
    parser.add_argument("--max-copies", type=int, required=True)
    parser.add_argument("--min-length", type=int, required=True)
    parser.add_argument("texts", nargs="+")
    args = parser.parse_args()
    guard = DuplicateGuard(
        window_seconds=args.window,
        max_copies=args.max_copies,
        min_length=args.min_length,
    )
    started = time.monotonic()
    for offset, text in enumerate(args.texts):
        decision = guard.check(args.room, text, now=started + offset * 1e-6)
        print(json.dumps(asdict(decision), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
