# Eval Criteria: Technocore private-file boundary audit
**Domain:** build
**Date:** 2026-08-30 WIB

## Quality-gate evidence

- Fresh official change: `addnad/technocore-ts@53562403f36fefa6089b680c2705bd309436d4e6` documents that `chmod(0600)` is a no-op on Windows and private files land with default ACLs.
- Threat boundary: local encrypted identity, X25519, and room-key-store files cross from Technocore into host filesystem access control.
- Reproducible abuse/validation gap: a POSIX private file readable by group/other must fail; Windows must never be reported secure from meaningless POSIX mode bits.
- Prior-state comparison: repository history through `ff0af6452680d47c68608faef0eee31fb7d54b51` has payload/duplicate guards but no local private-file permission validator.
- Precise utility: fail closed when a Technocore private file is not a regular owner-only POSIX file or when Windows ACLs have not been independently verified.

## Pass criteria (ALL must be true)

1. **TDD / behavior**
   - [ ] A test written first fails because `private_file_guard` does not exist.
   - [ ] A mode-0600 regular file owned by the invoking POSIX user passes.
   - [ ] Group/other access, a non-regular path, and a foreign owner fail with specific findings.
   - [ ] A simulated Windows check fails closed rather than trusting POSIX mode bits.
   - [ ] CLI returns 0 only for a passing audit and emits machine-readable JSON.

2. **Reproducibility and regression**
   - [ ] `python3 -m unittest -v` passes twice from the working tree.
   - [ ] A fresh detached checkout of the live commit passes the full suite.

3. **Negative test**
   - [ ] Removing the implementation makes the full eval fail.
   - [ ] Restoring it makes the full eval pass.

4. **User-spec match**
   - [ ] Commit is authored/pushed only as `aziraiga21` to `aziraiga21/technocore-security-checklist` (`fork=false`).
   - [ ] Live commit, CI success, WIB timestamp, and one-sentence value are verified before state is atomically updated.

## Fail criteria (ANY = no-go)

- Generic checklist/readme-only change.
- Windows is marked secure based on POSIX mode bits.
- Test passes before implementation exists.
- Full suite or live CI fails.
- Any write is made under a GitHub identity other than `aziraiga21`.

## Output location

- `eval-results/technocore-private-file-boundary/run-N.json`
