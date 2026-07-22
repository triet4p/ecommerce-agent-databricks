# S3B-01 — Trusted Identity Boundary

## Outcome

Added a single identity normalization function for the conversation service and
a trusted-header extractor that accepts only `X-Forwarded-User`. Blank,
oversized, and `unknown@unknown` identities are rejected; canonical owner
values are trimmed and case-folded before every service-to-repository call.

## Verification

- `tests/conversation/test_identity.py`
- `tests/conversation/test_redaction.py`
- `tests/conversation/test_replay.py`

The next atomic task applies database schema hardening and production React
server adoption of this extractor. Streamlit is intentionally not the target
of that integration work.
