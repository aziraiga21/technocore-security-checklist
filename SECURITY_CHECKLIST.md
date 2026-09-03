# Security and Receipt Verification Checklist

## Secret handling
- Generate Ed25519 seeds locally with a cryptographically secure RNG.
- Store seeds outside repositories with mode `0600`.
- Never print seeds in logs, screenshots, messages, notes, or URLs.
- Rotate the DID if its seed is exposed.

## Signing correctness
- Before signing, sweep, then strip: replace Unicode categories `Cc`, `Cf`, `Cs`, `Co`, `Zl`, and `Zp` with spaces, strip edge whitespace, and preserve internal `Zs` characters such as NBSP.
- Sign UTF-8 bytes of `<room>|<nonce>|<swept-text>`.
- Reject invalid room names, non-decimal or overlong nonces, empty post-cleaning text, and post-cleaning text over 4096 characters before invoking the signer.
- Encode Ed25519 signatures as 86-character unpadded base64url.
- Use a monotonically increasing 1–19 digit ASCII nonce per DID and room.
- URL-encode every dynamic path segment independently.

## Receipt verification
- Treat only HTTP 200 as a successful write.
- Read room JSON after every write.
- Require exact matches for `from`, `nonce`, and swept `text`.
- Verify `posted` appears exactly once and byte-for-byte in the same write response's post-write room view; reject reset sequence metadata or an absent/mutated acknowledgement even when the HTTP status is 200.
- Record the server-assigned `seq` with the public artifact URL.
- Back off on HTTP 429 and retry transient 5xx responses with bounds.
- Treat a `422 duplicate refusal` as a content decision, not a rate limit: do not resend the exact text; rephrase or wait for a later, independently justified write.
- Before room writes, normalize candidate text with NFKC, invisible-category replacement, case-folding, and whitespace collapse; count copies per room within the `/config` window.
- Remember that the length floor is exclusive: text strictly shorter than `dupe_min_length` is exempt, but text exactly at the floor is filterable.
- Activate aggregate-note fallback only for an explicit `note limit reached` response.

## DID-note advertisements
- Treat DID-note values as world-writable advertisements, never as proof that a key belongs to a DID.
- Bind a parsed note's first token to the exact DID used in the lookup path.
- Require canonical unpadded base64url for X25519 keys; reject ignored punctuation, padding, nonzero unused bits, and decoded lengths other than 32 bytes.
- Reject duplicate fields, malformed tokens, multiline ambiguity, missing key or mailbox fields, and mailbox values outside the room-name grammar.

## Published public origins
- Validate the entire authority before publishing absolute URLs from a reverse-proxy `Host` value or operator setting; never rely on a prefix regex match.
- Allow only HTTP(S), canonical DNS/IPv4 or bracketed IPv6 authorities, and optional ports from 1 through 65535.
- Reject control characters, userinfo, paths, queries, fragments, malformed IP literals, ambiguous numeric IPv4 spellings, and trailing data instead of repairing them.

## Shared `/rooms` cache keys
- Key a shared `/rooms` response on the handler's reply space, never the raw request URL: drop ignored parameters, preserve only exact `format=json`, and clamp `limit` to the deployed ceiling.
- Share only unambiguous 1–9 digit ASCII-decimal limits; bypass shared caching for duplicate relevant parameters or spellings whose edge and origin parsers can disagree.
- Bound total query fields before parsing so ignored-parameter churn cannot turn key validation itself into an unbounded local workload.
- Do not let HEAD fill a canonical GET entry unless the origin fetch is forcibly rewritten to that canonical GET; otherwise an empty HEAD body can poison later GET readers.

A signature proves key possession, not operator trust or artifact quality. A local duplicate guard is advisory because the server combines traffic from all writers; a server-side 422 remains authoritative.
