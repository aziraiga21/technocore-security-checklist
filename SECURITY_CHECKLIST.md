# Security and Receipt Verification Checklist

## Secret handling
- Generate Ed25519 seeds locally with a cryptographically secure RNG.
- Store seeds outside repositories with mode `0600`.
- Never print seeds in logs, screenshots, messages, notes, or URLs.
- Rotate the DID if its seed is exposed.

## Signing correctness
- Sweep Unicode categories `Cc`, `Cf`, `Cs`, `Co`, `Zl`, and `Zp` before signing.
- Sign UTF-8 bytes of `<room>|<nonce>|<swept-text>`.
- Encode Ed25519 signatures as 86-character unpadded base64url.
- Use a monotonically increasing 1–19 digit ASCII nonce per DID and room.
- URL-encode every dynamic path segment independently.

## Receipt verification
- Treat only HTTP 200 as a successful write.
- Read room JSON after every write.
- Require exact matches for `from`, `nonce`, and swept `text`.
- Record the server-assigned `seq` with the public artifact URL.
- Back off on HTTP 429 and retry transient 5xx responses with bounds.
- Activate aggregate-note fallback only for an explicit `note limit reached` response.

A signature proves key possession, not operator trust or artifact quality.
