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

A signature proves key possession, not operator trust or artifact quality. A local duplicate guard is advisory because the server combines traffic from all writers; a server-side 422 remains authoritative.
