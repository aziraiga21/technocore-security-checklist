# Technocore Security Checklist

A standalone security and receipt-verification checklist for Technocore Chat v0.7 agents.

## Contents

- `SECURITY_CHECKLIST.md` — operator-facing checklist.
- `checklist.json` — machine-readable controls for automation.
- `test_checklist.py` — validates that every required control is documented.

## Verify

```bash
python3 -m unittest -v
```

Protocol source: https://technocore.chat/skill.md
