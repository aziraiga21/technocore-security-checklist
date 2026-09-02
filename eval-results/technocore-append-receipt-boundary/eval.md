# Eval Criteria: Technocore append-receipt boundary
**Domain:** build
**Date:** 2026-09-02 WIB

## Fresh official source and distinct utility

- Official change: `flop-labs/technocore-chat@ba868a3f275b234722dfb003f158ef822ec8061d` fixes a production-reachable path where `append()` returned a successful `posted` record but immediate compaction removed that record and reset the room sequence.
- Threat boundary: an agent must not treat HTTP 200 or the top-level `posted` object alone as durable acceptance; the same write response includes the post-compaction `messages` view and can provide an immediate consistency receipt.
- Distinct utility: validate a captured Technocore write response offline and fail closed unless the acknowledged record appears exactly once, byte-for-byte, in the post-write room view with coherent sequence metadata.
- Prior repository state has payload, duplicate, file-permission, DID-note, and origin guards, but no append durability/receipt validation.

## Pass criteria (ALL must be true)

1. **Reproducibility**
   - [x] `python3 -m unittest -v` passes from a fresh checkout.
   - [x] Repeated full-suite runs have the same pass count and exit code.

2. **Demonstrability**
   - [x] A fixture reproducing the pre-fix response shape (`posted.seq == 2`, empty `messages`, reset `last_seq`) is rejected with a specific `posted record is absent` finding.
   - [x] A coherent response containing the exact posted record is accepted and emits deterministic JSON.

3. **Negative and error paths**
   - [x] Missing/duplicate/mutated posted records, incoherent room/count/first_seq/last_seq metadata, malformed JSON, and non-object roots are rejected.
   - [x] CLI exits 0 only for a verified receipt and nonzero for an official-bug reproduction.

4. **Negative test (eval reality)**
   - [x] Before implementation, the focused test fails because `append_receipt_guard` is missing.
   - [x] Removing the implementation after GREEN makes the full eval fail; restoring it makes the full eval pass.

5. **User-spec match**
   - [x] Utility is tied to a fresh official change and a concrete reproduced validation gap.
   - [x] Change adds executable defensive behavior, not a generic checklist or cosmetic documentation.
   - [x] GitHub identity, owned non-fork repository, live commit, and CI success are verified before recording daily state.

## Fail criteria (ANY = no-go)

- Critical behavior is mocked or depends on a live external service.
- Validator accepts a response where `posted` is absent from `messages` or differs from its matching sequence record.
- Tests pass when implementation is removed.
- Repository identity is not `aziraiga21` or repository is a fork.
- CI is not successful.

## Output location

- `eval-results/technocore-append-receipt-boundary/run-1.json` — RED and development evidence.
- `eval-results/technocore-append-receipt-boundary/run-2.json` — negative-test restoration, fresh-checkout, live-commit, and CI evidence.
