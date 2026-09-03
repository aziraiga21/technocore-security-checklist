# Eval Criteria: Technocore `/rooms` cache-key boundary
**Domain:** build
**Date:** 2026-09-03 WIB

## Fresh official source and distinct utility

- Official change: `flop-labs/technocore-chat@01c49fbe85b1bd05deb066b7fcae2a58d4eef053` adds an edge `/rooms` stale-while-revalidate lane after reproducing origin 524s and fixes raw-URL cache-key multiplication, caller-specific response sharing, cold-fill fan-out, and HEAD-to-GET cache poisoning during review.
- Threat boundary: a deployer must map attacker-controlled `/rooms` query URLs onto the handler's reply equivalence classes before shared caching; a raw URL key permits unbounded cold origin walks, while parser disagreement can serve one caller another row count.
- Reproduced abuse case: ignored query churn and over-limit decimal variants represent the same origin reply but produce distinct raw URL keys; non-ASCII digits, signs, whitespace, separators, overlong values, duplicate relevant parameters, userinfo, and fragments are refused as unshareable rather than guessed.
- Distinct utility: derive a deterministic, dependency-free canonical GET cache key for safely shareable `/rooms` requests and emit an explicit non-shareable finding for ambiguous requests.
- Prior repository state has duplicate-write, signed-payload, private-file, DID-note, public-origin, and append-receipt guards, but no edge cache-key validator.

## Pass criteria (ALL must be true)

1. **Reproducibility**
   - [ ] `python3 -m unittest -v` passes from a fresh checkout.
   - [ ] Two consecutive full-suite runs produce the same pass count and exit code.

2. **Demonstrability**
   - [ ] `/rooms?limit=200`, an over-limit decimal, and ignored-query churn collapse to the expected reply-space key.
   - [ ] `format=json` remains in the key while ignored format values do not.

3. **Negative and error paths**
   - [ ] Non-GET methods, wrong paths, userinfo, fragments, duplicate relevant parameters, non-ASCII/noncanonical/overlong limits, malformed URLs, booleans, and invalid max limits fail closed.
   - [ ] CLI emits deterministic JSON and exits 0 only for a shareable request.

4. **Negative test (eval reality)**
   - [ ] Focused behavior test is observed failing before each implementation slice.
   - [ ] Removing the implementation after GREEN makes the full eval fail; restoring it makes the full eval pass.

5. **User-spec match**
   - [ ] Utility is tied to the fresh official edge change and concrete raw-query amplification/parser-differential boundaries.
   - [ ] Change adds executable defensive behavior, not generic advice, duplicate cases, or cosmetic documentation.
   - [ ] GitHub identity `aziraiga21`, owned non-fork repository, live commit, and CI success are verified before daily state is recorded.

## Fail criteria (ANY = no-go)

- Critical behavior is mocked or depends on a live external service.
- Unknown query parameters survive into the shared key, or ambiguous numeric input is silently shared.
- Test passes when implementation is removed.
- Repository identity is not `aziraiga21` or repository is a fork.
- Live CI is not successful.

## Output location

- `eval-results/technocore-rooms-cache-key-boundary/run-1.json` — TDD RED/GREEN and development evidence.
- `eval-results/technocore-rooms-cache-key-boundary/run-2.json` — negative-test restoration, fresh-checkout, live-commit, and CI evidence.
