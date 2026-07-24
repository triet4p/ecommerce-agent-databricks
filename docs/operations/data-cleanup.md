# Legacy Conversation Data Cleanup

## Decision Required

The existing Lakebase records owned by `unknown@unknown` cannot be safely
attributed to an authenticated person. They must not be reassigned from any
browser input or inferred identity.

The planned one-time, project-scoped cleanup is a **hard delete of only**
`conversations.conversations` rows where `owner = 'unknown@unknown'`; existing
foreign-key cascades remove their turns and items. Run it only after the
repository owner confirms retention/privacy approval and after an export
approved by the data owner if one is required. The application itself rejects
that owner going forward.

Until approval, do not execute this deletion. The migration merely gives legacy
items deterministic `legacy:<uuid>` keys so schema hardening can proceed
without modifying their payloads or ownership.
