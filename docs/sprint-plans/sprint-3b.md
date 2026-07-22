# Sprint 3b Plan — Conversation Persistence Hardening

## Goal

Correct the Sprint 3 production boundary before React adopts it: trusted
identity, owner-scoped durable data, transaction-safe sequencing and state
transitions, safe persistence, reliable migrations, and real integration
evidence. React rendering remains Sprint 4 scope.

Status legend: `[ ]` pending / `[~]` in progress / `[x]` done.

## Atomic Tasks

- [x] **S3B-01:** Replace fallback/browser-provided ownership with a validated,
  normalized trusted Databricks forwarded identity at the server boundary.
- [x] **S3B-02:** Add schema v2 constraints, owner/request/trace bounds, item
  idempotency key uniqueness, and a safe data-cleanup procedure for legacy
  `unknown@unknown` records.
- [x] **S3B-03:** Make migrations lock, DDL, version recording, waiting, and
  version verification transactional on one session connection.
- [x] **S3B-04:** Make conversation turn creation atomic, owner-scoped,
  idempotent, and concurrency-safe.
- [~] **S3B-05:** Make complete/fail/cancel transitions owner-scoped,
  idempotent, state-checked, transaction-safe, and item-key deduplicated.
- [x] **S3B-06:** Enforce soft deletion and prevent all access or mutation of a
  deleted conversation.
- [x] **S3B-07:** Sanitize every persisted input/output item, including known
  JSON-string fields, and enforce item-count and payload limits.
- [x] **S3B-08:** Define/revise replay provenance contract: canonical tool
  audit records, message-only model history, no JSON-text heuristic.
- [ ] **S3B-09:** Build the React-server-compatible stream lifecycle boundary:
  terminal completion only, terminal failures/cancellations, typed context
  overflow, trace persistence, and metadata-only logging.
- [~] **S3B-10:** Package the conversation module with the Chat App; remove
  personal hard-coded deployment values; make verification schema read-only;
  standardize database naming and assess Lakebase cost policy.
- [ ] **S3B-11:** Add isolated PostgreSQL integration coverage for migrations,
  constraints, concurrency, retries, isolation, deletion, and redaction.
- [ ] **S3B-12:** Add stream lifecycle and security persistence tests, then run
  a real React-server-to-Agent-App E2E test.
- [ ] **S3B-13:** Resolve Ruff findings and update Sprint 3 status, closeout,
  F8/F9/F10 evidence, replay contract, naming documentation, and superseded
  lessons.

## Completion Gate

Do not close Sprint 3/Sprint 3b until P0 data/service/migration protections
and PostgreSQL integration tests pass. React presentation work can proceed in
Sprint 4 only against this hardened contract.
