# Eval Criteria: Technocore public-origin boundary
**Domain:** build
**Date:** 2026-09-01 WIB

## Evidence and threat boundary

Fresh official change: `flop-labs/technocore-chat@94896d86c0d20dc3d3efee87f71fc72a820dc4a8` changed `re.match` to `fullmatch` after reproducing that `example.com\n` passed a Host allowlist and reached advertised JSON, XML, and headers.

Boundary: a reverse-proxy `Host` value or operator-provided public origin is untrusted input; it must not steer generated absolute URLs unless the entire authority and scheme are canonical and free of controls, paths, query strings, fragments, or userinfo.

## Pass criteria (ALL must be true)

1. **Reproducibility**
   - [ ] `python3 -m unittest -v` passes from a fresh checkout.
   - [x] Two unchanged full-suite runs produce the same test count and exit code.

2. **Demonstrability**
   - [x] `public_origin_guard.py https 'example.com'` emits `{"ok":true,"origin":"https://example.com"}` and exits 0.
   - [x] The same command with a trailing newline in the authority emits one JSON finding, no traceback, and exits 1.

3. **Negative test**
   - [x] Removing `public_origin_guard.py` makes the full eval fail because the tested implementation is absent.
   - [x] Restoring it makes the same eval pass.

4. **User-spec match**
   - [x] Work is in `aziraiga21/technocore-security-checklist`, verified `fork=false`, under GitHub identity `aziraiga21`.
   - [x] Tests pin the official trailing-newline abuse and reject control characters, userinfo, path/query/fragment injection, invalid ports, and non-HTTP(S) schemes.
   - [x] Valid DNS names, IPv4, bracketed IPv6, and optional numeric ports are accepted and canonicalized.

## Fail criteria (ANY = no-go)

- Generic checklist or prose without executable defensive utility.
- Critical parser behavior mocked or dependent on a live external service.
- Test passes on baseline or after implementation removal.
- A malformed authority is partially accepted or repaired silently.
- Contribution is pushed from an identity other than `aziraiga21`.

## Output location

- `eval-results/technocore-public-origin-boundary/run-1.json` (negative test)
- `eval-results/technocore-public-origin-boundary/run-2.json` (restored/fresh verification)
