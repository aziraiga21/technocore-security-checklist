#!/usr/bin/env python3
"""Fail-closed parser for untrusted Technocore DID-note advertisements."""

from dataclasses import dataclass
import argparse
import base64
import binascii
import json
import re
import sys


_X25519_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")


class DidNoteError(ValueError):
    """A DID note is ambiguous or unsafe to consume."""


@dataclass(frozen=True)
class DidNote:
    did: str
    fields: dict[str, str]
    x25519: str
    mailbox: str


def parse_did_note(value: str, *, expected_did: str) -> DidNote:
    """Parse a canonical DID note and bind it to the DID used for lookup."""
    if "\n" in value or "\r" in value:
        raise DidNoteError("DID note must contain exactly one line")
    tokens = value.split()
    if not tokens:
        raise DidNoteError("DID note must not be empty")
    did = tokens[0]
    if did != expected_did:
        raise DidNoteError("note DID does not match expected DID lookup path")
    fields: dict[str, str] = {}
    for token in tokens[1:]:
        if ":" not in token:
            raise DidNoteError(f"field must be key:value: {token}")
        key, field_value = token.split(":", 1)
        if not key or not field_value:
            raise DidNoteError(f"field must have nonempty key and value: {token}")
        if key in fields:
            raise DidNoteError(f"duplicate field: {key}")
        fields[key] = field_value
    missing = {"x25519", "mailbox"} - fields.keys()
    if missing:
        raise DidNoteError(f"missing required field: {sorted(missing)[0]}")
    x25519 = fields["x25519"]
    if not _X25519_PATTERN.fullmatch(x25519):
        raise DidNoteError("x25519 must be canonical unpadded base64url")
    try:
        raw = base64.b64decode(x25519 + "=", altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as error:
        raise DidNoteError("x25519 must be canonical unpadded base64url") from error
    if len(raw) != 32 or base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != x25519:
        raise DidNoteError("x25519 must be canonical unpadded base64url encoding 32 bytes")
    mailbox = fields["mailbox"]
    if not _NAME_PATTERN.fullmatch(mailbox):
        raise DidNoteError("mailbox must match ^[a-z0-9][a-z0-9_-]{0,47}$")
    return DidNote(
        did=did,
        fields=fields,
        x25519=x25519,
        mailbox=mailbox,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-did", required=True)
    parser.add_argument("note")
    args = parser.parse_args(argv)
    try:
        note = parse_did_note(args.note, expected_did=args.expected_did)
    except DidNoteError as error:
        print(json.dumps({"findings": [str(error)], "ok": False}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "did": note.did,
                "fields": note.fields,
                "x25519": note.x25519,
                "mailbox": note.mailbox,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
