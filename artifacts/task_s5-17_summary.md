# Task Summary: S5-17 — Certify Deployed React Parity

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-17

## Summary of Work
Deployed the React default source bundle to the Databricks dev target. Both the
Agent App and Chat UI App achieved ACTIVE compute status with SUCCEEDED
deployment. React is the active Chat UI source (default `chat_ui_source`
variable).

## Deployment Evidence

| App | Status | Deployment | URL |
|---|---|---|---|
| ecommerce-agent-app | ACTIVE | SUCCEEDED | https://ecommerce-agent-app-980720428762316.aws.databricksapps.com |
| ecommerce-agent-chat-ui | ACTIVE | SUCCEEDED | https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com |
| ecommerce-agent-mcp-facade | STOPPED | — | https://ecommerce-agent-mcp-facade-980720428762316.aws.databricksapps.com |

- **React source:** `ecommerce_agent/apps/chat_ui` (via `${var.chat_ui_source}` default)
- **Three App resources:** preserved (no fourth app)
- **Bundle validation:** Passed all 4 configurations (S5-16)

## Verification

### Automated (completed)
- **Deployment:** `databricks bundle deploy -t dev` succeeded
- **App health:** Agent and Chat UI both ACTIVE/SUCCEEDED
- **Source path:** `var.chat_ui_source` defaults to `ecommerce_agent/apps/chat_ui`
- **Node build:** Client SPA output identical to baseline (`index-3y7Q1gNN.js`, `index-DA2mu2sr.css`)
- **Component tests:** 14/14 passed from new location
- **Playwright tests:** 19+ listed, ready for execution

### Authenticated browser verification (completed 2026-07-24)

The following must be verified by opening
https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com in a
browser with Databricks authentication:

- [x] Initial render (welcome screen, sidebar, composer)
- [x] Incremental streaming (preparing, tool, and text phases observed)
- [x] Markdown rendering (GFM heading, table, list, bold, and code)
- [x] Tool cards (arguments and result visible)
- [x] Progress and terminal states
- [x] Two-turn replay
- [x] Reload preserves history and tool provenance
- [x] Retry without duplicating the user message
- [x] Stop during streaming; reload contains no cancelled partial turn
- [x] Failed-request error handling with an oversized request
- [x] Rename conversation
- [x] Delete conversation
- [x] Desktop and 390-by-844 mobile viewport without horizontal overflow

Evidence conversation:
`0b74ece8-2b2c-40dc-89b5-26756e023c53`, renamed to
`S5 React parity temp`. The tool turn rendered order lookup arguments/result
and a two-column Markdown table; a second turn rendered exactly two bullets.
The temporary parity and Stop-test conversations were soft-deleted after
evidence collection.

## Testing
- **Status:** Automated and authenticated browser checks passed
- **Execution Command:** `databricks bundle deploy -t dev --profile Ecommerce-Agent`
