"""Build the exact Technocore room-message bytes that clients must sign."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass

_INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
_NONCE_PATTERN = re.compile(r"^[0-9]{1,19}$")
_MAX_MESSAGE_CHARS = 4096


@dataclass(frozen=True)
class SignedPayload:
    room: str
    nonce: str
    text: str
    payload: bytes


def clean_signed_text(text: str) -> str:
    """Match the server's clean_text: sweep six categories, then strip edges."""
    return "".join(
        " " if unicodedata.category(character) in _INVISIBLE_CATEGORIES else character
        for character in text
    ).strip()


def build_message_payload(room: str, nonce: str, text: str) -> SignedPayload:
    """Validate fields and return the canonical UTF-8 bytes to sign."""
    if not _NAME_PATTERN.fullmatch(room):
        raise ValueError("room must match ^[a-z0-9][a-z0-9_-]{0,47}$")
    if not _NONCE_PATTERN.fullmatch(nonce):
        raise ValueError("nonce must be 1-19 decimal digits")
    cleaned = clean_signed_text(text)
    if not cleaned:
        raise ValueError("message is empty after server-compatible cleaning")
    if len(cleaned) > _MAX_MESSAGE_CHARS:
        raise ValueError("message must contain at most 4096 characters after cleaning")
    payload = f"{room}|{nonce}|{cleaned}".encode("utf-8")
    return SignedPayload(room=room, nonce=nonce, text=cleaned, payload=payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the exact server-cleaned Technocore room-message bytes to sign."
    )
    parser.add_argument("room")
    parser.add_argument("nonce")
    parser.add_argument("text")
    args = parser.parse_args()
    try:
        built = build_message_payload(args.room, args.nonce, args.text)
    except ValueError as error:
        parser.error(str(error))
    print(
        json.dumps(
            {
                "nonce": built.nonce,
                "payload_hex": built.payload.hex(),
                "payload_utf8": built.payload.decode("utf-8"),
                "room": built.room,
                "text": built.text,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
