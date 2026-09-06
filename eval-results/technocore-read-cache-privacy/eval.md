# Eval Criteria: Technocore read-cache privacy boundary
**Domain:** build
**Date:** 2026-09-06 WIB

## Pass criteria (ALL must be true)

1. **Reproducibility**
   - [ ] `python3 -m unittest -v` passes from a fresh checkout at the live commit.
   - [ ] Two unchanged full-suite runs produce the same test count and exit code.

2. **Demonstrability**
   - [ ] A dependency-free CLI reads one captured HTTP response envelope as JSON and emits a deterministic JSON decision.
   - [ ] A reproduced caller-A response containing `# budget:` plus `s-maxage` is rejected because a shared CDN could replay A's pacing state to caller B.
   - [ ] Plain successful `/rooms`, room, and `/kv` reads with valid shared-cache directives are accepted.

3. **Negative test**
   - [ ] Before implementation, the focused test fails because `read_cache_privacy_guard` is absent.
   - [ ] Removing the completed guard makes the focused/full eval fail; restoring it makes the eval pass.

4. **User-spec match**
   - [ ] Work is based on fresh official commit `91a28151656a86c2583491512b6cbd87466c5613`, which expanded shared edge caching to `/kv` and retained caller-specific budget footers as `no-store`.
   - [ ] The contribution adds distinct defensive utility: executable response-policy validation rather than a generic checklist or duplicate cache-key logic.
   - [ ] Wrong methods/routes, malformed envelopes/headers, long-poll sharing, caller-specific footer sharing, and contradictory cache directives fail closed.

## Fail criteria (ANY = no-go)

- Critical HTTP response behavior is mocked without disclosure.
- Test asserts only implementation details instead of emitted decisions.
- The negative test passes without the guard.
- Existing tests regress or CI fails.
- Repository is a fork, live author differs from `aziraiga21`, or live commit cannot be verified.

## Output location

- `eval-results/technocore-read-cache-privacy/run-1.json`: RED and completed local evidence.
- `eval-results/technocore-read-cache-privacy/run-2.json`: negative-test, restored pass, fresh-checkout, and CI evidence.
