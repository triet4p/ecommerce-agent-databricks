---
name: sprint4-react-migration
description: Sprint 4 replaced Streamlit chat UI with React app in chat_ui/
metadata:
  type: project
---

Sprint 4 implemented a full React-based Chat UI replacement in `chat_ui/`,
replacing the Streamlit app in `ecommerce_agent/apps/chat_ui/`. The new app
uses Vite + React 18 (client) and Express (server) in a monorepo with npm
workspaces.

**Why:** The Streamlit full-page rerun model was incompatible with incremental
text streaming and responsive UX. The official Databricks `e2e-chatbot-app-next`
template was pinned (commit `2a4c792`) and adapted.

**Key files:**
- `chat_ui/packages/core/src/index.ts` — shared types (Sprint 2 events, Sprint
  3 models), event reducer, display policy, phase labels
- `chat_ui/server/src/lib/conversation.ts` — Sprint 3-adapted repository in
  TypeScript (same SQL, same schema)
- `chat_ui/server/src/middleware/identity.ts` — X-Forwarded-User extraction
- `chat_ui/server/src/routes/turns.ts` — streaming proxy (SSE passthrough)
- `chat_ui/server/src/index.ts` — Express app with API + static serving
- `chat_ui/client/src/contexts/ChatContext.tsx` — conversation state store
- `chat_ui/client/src/hooks/useChat.ts` — streaming chat hook
- `chat_ui/client/src/pages/ChatPage.tsx` — main UI with all UX states

**How to apply:**
- Build: `cd chat_ui && npm install && npm run build`
- Dev: `npm run dev` (starts server on :4000 and Vite on :3000 with proxy)
- Tests: `npx playwright test` (20 tests, all pass)
- Deploy: Update `databricks.yml` source_code_path to `chat_ui/` for the
  `ecommerce_agent_chat_ui` app, then `databricks bundle deploy`

**Remaining work (E7-E11):** Bundle validation, deployment, feature-parity
smokes, rollback test, and Streamlit removal.
