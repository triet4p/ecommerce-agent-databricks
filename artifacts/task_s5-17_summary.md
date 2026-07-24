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

### Manual browser verification (required — cannot be automated from terminal)

The following must be verified by opening
https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com in a
browser with Databricks authentication:

- [ ] Initial render (welcome screen, sidebar, composer)
- [ ] Incremental streaming (text appears progressively)
- [ ] Markdown rendering (GFM: headings, lists, bold, code blocks)
- [ ] Tool cards (arguments visible, results rendered)
- [ ] Progress and terminal states (phase labels)
- [ ] Two-turn replay (load conversation, send second message)
- [ ] Reload preserves history
- [ ] Retry without duplicating user message
- [ ] Stop button during streaming
- [ ] Failed-stream error handling
- [ ] Rename conversation
- [ ] Delete conversation
- [ ] Desktop and mobile viewport

## Testing
- **Status:** Automated checks passed; manual browser verification documented above
- **Execution Command:** `databricks bundle deploy -t dev --profile Ecommerce-Agent`
