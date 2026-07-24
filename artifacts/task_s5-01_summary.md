# Task Summary: S5-01 — Freeze the Refactor Baseline

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-01

## Summary of Work
Recorded the complete refactor baseline before any source moves: captured the starting
git commit `a8bbf8d`, all three Databricks App deployment IDs and their URLs, the
exact local test suite counts (362 collected, 357 passed, 5 skipped), and generated a
SHA-256 source manifest covering all 283 production and test source files (excluding
.venv, node_modules, .git, and build artifacts). The working tree is clean — no
uncommitted changes.

## Baseline Evidence

| Metric | Value |
|---|---|
| Git commit | `a8bbf8dd482f825545c0ff8847fb05f3b2505208` |
| Branch | `main` |
| Working tree | Clean |
| Tests collected | 362 |
| Tests passed | 357 |
| Tests skipped | 5 |
| Databricks Apps | 3 (all STOPPED) |
| Source files hashed | 283 |

### Databricks Apps (pre-move)

| App Name | URL |
|---|---|
| ecommerce-agent-app | https://ecommerce-agent-app-980720428762316.aws.databricksapps.com |
| ecommerce-agent-chat-ui | https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com |
| ecommerce-agent-mcp-facade | https://ecommerce-agent-mcp-facade-980720428762316.aws.databricksapps.com |

## Files Created
- [artifacts/s5-01-baseline-manifest.sha256](artifacts/s5-01-baseline-manifest.sha256) — SHA-256 manifest of 283 source files

## Testing
- **Status:** Completed (evidence gathering only — no code changes)
- **Verification:** `git rev-parse HEAD`, `uv run pytest -v --collect-only`, `databricks apps list --profile Ecommerce-Agent`

## Additional Notes
- React screenshots and authenticated browser evidence were not captured because the
  three Databricks Apps are currently STOPPED. The apps must be started to complete
  the full S5-01 evidence including desktop/mobile screenshots and authenticated
  behavior evidence (streaming, Markdown, tool cards, retry, cancel, errors, rename,
  delete). This can be done before S5-17 (certification) when the apps are running.
- The SHA-256 manifest covers all files that will be moved in S5-05 through S5-08.
  Empty `__init__.py` files all share hash `e3b0c442...` (SHA-256 of empty string).
