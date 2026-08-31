# Eval Criteria: Technocore DID-note trust-boundary guard
**Domain:** build / security validation
**Date:** 2026-08-31 WIB

## Evidence motivating the change

The official `addnad/technocore-ts` client at `0a45627e7ca3a04dd0e74ddbdac13ada0c3e1c78` parses world-writable DID notes with Node's permissive `Buffer.from(value, "base64url")`. A 44-character X25519 value containing `!` was accepted and decoded to the same 32 bytes as its canonical 43-character spelling. This creates a parser-differential boundary: downstream policy can inspect one spelling while cryptography consumes another.

## Pass criteria (ALL must be true)

1. **Reproducibility**
   - [x] `python3 -m unittest -v` runs from a clean checkout with no dependencies and exits 0.
   - [x] Two unchanged full-suite runs produce the same test count and result.

2. **Demonstrability**
   - [x] A test reproduces and rejects the exact punctuation-injected X25519 value accepted by the official parser.
   - [x] The CLI emits one deterministic JSON decision containing either a canonical parsed note or concrete findings.

3. **Trust-boundary validation**
   - [x] Canonical 32-byte unpadded base64url X25519 keys are accepted.
   - [x] Invalid alphabet, padding, noncanonical spelling, and wrong decoded length are rejected before use.
   - [x] Duplicate fields, malformed tokens, invalid mailbox names, multiline ambiguity, DID/path mismatch, and missing required fields are rejected.

4. **Negative test**
   - [x] Removing the guard implementation makes the full eval fail for the expected missing-feature reason.
   - [x] Restoring the implementation makes the same full eval pass.

5. **User-spec match**
   - [x] Contribution is made only in `aziraiga21/technocore-security-checklist`, confirmed `fork=false`.
   - [x] Utility is distinct from duplicate-write, signed-payload, and private-file controls.

## Fail criteria (ANY = no-go)

- Parser silently normalizes attacker-controlled encodings.
- Critical validation is mocked or delegated to a network service.
- Tests pass without `did_note_guard.py`.
- Contribution is documentation-only, cosmetic, duplicate, or cross-account.
- Full suite or live GitHub CI fails.

## Output location

- `eval-results/technocore-did-note-boundary/run-1.json` — implementation and full-suite result.
- `eval-results/technocore-did-note-boundary/run-2.json` — negative-test failure and restored pass.
