# E-commerce Agent Architecture

- **Status:** Implemented and deployed
- **Architecture version:** 0.4
- **Last reviewed:** 2026-07-24
- **Editable diagram:** [ecommerce-agent-architecture.drawio](ecommerce-agent-architecture.drawio)
- **Operations:** [Databricks Apps redeployment runbook](../operations/redeploy.md)

Rendered diagram pages:

- [Production Runtime](previews/architecture-page-1.png)
- [Data, Delivery and Identity](previews/architecture-page-2.png)
- [Placement Decisions](previews/architecture-page-3.png)

Page 2 was last rendered and visually inspected with draw.io Desktop 30.3.6.
Pages 1 and 3 were unchanged in architecture version 0.4.

## 1. System summary

The system is an owner-scoped conversational support application on Databricks.
React is the default user interface. A Node/Express server owns trusted identity,
Lakebase persistence, replay construction, cancellation, and the streaming proxy
to a separate Agent App.

```text
Authenticated browser
        |
        v
Chat UI App (React + Node)
   |                  |
   | owner-scoped     | OAuth /api/responses
   v                  v
Lakebase          Agent App
                      |
          +-----------+-----------+
          |                       |
          v                       v
DeepSeek endpoint       Governed tools / reranker
```

An optional Streamlit client can temporarily replace React in the same Chat UI
App slot. It uses the same trusted identity, conversation service, Lakebase
schema, and Agent App. The optional MCP facade exposes the whole support agent as
one Streamable HTTP MCP integration.

## 2. Databricks resource topology

The Declarative Automation Bundle declares exactly three Databricks Apps:

| Resource key | App name | Responsibility | Generated source |
|---|---|---|---|
| `ecommerce_agent` | `ecommerce-agent-app` | Responses API agent runtime | `.build/apps/agent_app` |
| `ecommerce_agent_chat_ui` | `ecommerce-agent-chat-ui` | React or Streamlit UI plus Lakebase persistence | `.build/apps/chat_ui` by default |
| `ecommerce_agent_mcp_facade` | `ecommerce-agent-mcp-facade` | Optional inbound MCP integration | `.build/apps/mcp_facade` |

React and Streamlit are two source configurations for one App resource:

```text
default:  chat_ui_source=.build/apps/chat_ui
demo:     chat_ui_source=.build/apps/streamlit_chat_ui
```

They cannot run simultaneously in this topology. Restoring React means deploying
again without the override.

### External singleton dependencies

| Resource | Purpose |
|---|---|
| `deepseek-v4-streaming-agent-lab` | model provider boundary used through `ChatDatabricks` |
| `search-and-rerank-endpoint` | policy retrieval and custom reranking |
| `ecommerce-agent-conversations` Lakebase project | transactional conversation history |
| `ecommerce_agent` Unity Catalog catalog | governed functions and commerce data |
| `/Shared/ecommerce-agent-app` MLflow experiment | traces and evaluation evidence |

The bundle grants the minimum App permissions required for these resources. It
does not create temporary Model Serving endpoints.

## 3. Source and deployment boundaries

### Maintained source

```text
agent_core/                         reusable orchestration and interfaces
ecommerce_agent/
  apps/
    agent_app/
    chat_ui/
    mcp_facade/
    streamlit_chat_ui/
  conversation/                    canonical persistence/service layer
  rules/
  skills/
  tools/
```

`agent_core` must remain independent of the e-commerce use case. Product
configuration, prompts, rules, skills, tools, persistence, and entry points live
under `ecommerce_agent`.

### Generated deployment sources

Databricks Apps flattens `source_code_path` into the runtime working directory.
Repository source directories are therefore not valid deployment contracts by
themselves. `scripts/build_apps.py` builds four isolated roots:

```text
.build/apps/
  agent_app/
  chat_ui/
  mcp_facade/
  streamlit_chat_ui/
```

Each root contains only its runtime source, root `app.yaml`, and dependency
inputs:

| Artifact | Runtime dependency contract |
|---|---|
| Agent | `pyproject.toml` + `uv.lock`; `uv run --frozen` |
| React/Node | `package.json` + `package-lock.json` |
| MCP facade | component-owned `requirements.txt` |
| Streamlit | component-owned `requirements.txt` |

The Agent component retains its own nested `requirements.txt` as component
metadata, but the generated Agent root intentionally has no `requirements.txt`.
Databricks source preparation failed when that root exposed both the locked `uv`
workflow and a root pip dependency entry point.

Generated artifacts exclude tests, caches, `node_modules`, build output from
other Apps, and local credentials. Contract tests import modules from the
isolated artifact working directories to reproduce deployment resolution.

## 4. Request and streaming flow

1. Databricks App ingress authenticates the browser and injects trusted identity.
2. The Chat UI server resolves the owner key; client-provided identity is never
   authoritative.
3. The server creates an idempotent turn in Lakebase.
4. Completed conversation items are replayed within the context budget.
5. The Chat UI server obtains App-to-App OAuth and calls Agent
   `POST /api/responses`.
6. SSE events are proxied to the browser while the server accumulates canonical
   output items.
7. Output is persisted only after `response.completed`.
8. Error, cancellation, missing-terminal, and upstream-body failures do not
   persist partial assistant output.

The stable event and display rules are defined in the
[Chat UI event contract](../contracts/chat-ui-event-contract.md).

## 5. Agent runtime

The Agent App starts MLflow `AgentServer` with an MLflow `ResponsesAgent`.
`CoreAgent` translates Responses API input to LangChain messages, then
`create_agent` runs the model/tool loop through `ChatDatabricks`.

### Prompt composition

| Content | Lifecycle | Canonical location |
|---|---|---|
| Base prompt/config | loaded at agent construction | `ecommerce_agent/config.yaml` and MLflow Prompt Registry |
| Rules | always included | `ecommerce_agent/rules/*.md` |
| Skills | loaded on demand | `ecommerce_agent/skills/*.md` |

Rules and skills are source-controlled behavior and deploy atomically with the
Agent. Operational policy documents and business data remain governed data, not
mutable application source.

### Tool placement

| Need | Placement |
|---|---|
| Governed reusable query/policy logic | Unity Catalog SQL or Python function |
| Pure deterministic calculation | local LangChain tool |
| Network call or custom reranking | thin local adapter plus serving endpoint |
| UC function discovery/invocation | explicitly selected managed MCP or toolkit transport |
| Long situational procedure | source-backed progressive-disclosure skill |

Transport failures remain visible. The runtime never silently falls back from
managed MCP to another tool transport.

## 6. Conversation persistence

Lakebase is the synchronous OLTP store. The Chat UI App owns:

- `conversations`: owner-scoped container and soft deletion;
- `turns`: idempotency key, monotonic sequence, lifecycle status and trace ID;
- `conversation_items`: canonical message/tool output payloads.

Security and integrity rules include:

- every CRUD and lifecycle operation is owner-scoped;
- terminal complete/fail/cancel transitions are idempotent;
- only completed message history enters replay;
- tool provenance remains persisted separately;
- credential and reasoning fields are redacted;
- payload size and output-item count are bounded;
- a typed error rejects context that exceeds the replay budget.

The stable schema and replay guarantees are documented in the
[conversation persistence contract](../contracts/conversation-persistence.md).

## 7. Data and retrieval

Structured commerce data follows the governed medallion path:

```text
UC Volume -> Bronze Delta -> Silver Delta -> Gold Delta -> UC functions
```

Policy documents follow:

```text
UC Volume -> parse/chunk -> Delta chunk table -> Mosaic AI Search
          -> search-and-rerank endpoint -> search_policy_docs tool
```

Returned document chunks retain source identity. Deterministic refund
eligibility uses governed policy logic rather than treating retrieved prose as
the final decision.

## 8. Identity and security boundaries

- Browser identity comes from trusted Databricks ingress headers.
- Each App has its own service principal.
- Chat UI-to-Agent and MCP-to-Agent calls use audience-scoped OAuth.
- Lakebase credentials are injected through the `conversation-store` App
  resource.
- App hostnames, tokens, passwords, and credentials are never committed.
- Raw model reasoning is not exposed in the UI or persisted as conversation
  history.
- Cross-user access is prevented at service and repository boundaries; a
  separate authenticated browser session is used when manually certifying
  cross-user isolation.

## 9. Delivery and recovery

The reproducible delivery sequence is:

```text
local tests
  -> scripts/build_apps.py
  -> bundle validate --strict
  -> bundle deploy
  -> bundle run App resources
  -> status/log checks
  -> authenticated browser smoke
```

Recovery rebuilds and redeploys a known-good Git revision. The detailed commands
and the Streamlit-to-React switch procedure are in
[operations/redeploy.md](../operations/redeploy.md).

## 10. Explicit non-goals

The production graph does not include:

- Model Serving as the agent host;
- a fourth App for Streamlit;
- automatic MCP/toolkit fallback;
- DBFS for code, configuration, rules, or skills;
- Delta tables for synchronous chat-state reads/writes;
- static OAuth tokens shared between Apps;
- direct deployment from non-isolated repository source roots.

## 11. Maintaining this document

Update the Markdown, draw.io source, and rendered previews together whenever any
of these change:

- App boundary, active UI source, or downstream resource;
- generated artifact layout or dependency mechanism;
- identity, permission, request, persistence, or deployment flow;
- Unity Catalog object, Model Serving dependency, or Lakebase binding;
- production versus optional/compatibility path.

After editing:

1. validate draw.io XML with the repository skill script;
2. render every affected page;
3. inspect previews at original resolution;
4. repair documentation links;
5. update `.agents/memory/decisions.md` for a durable architecture decision;
6. update the certification index when coverage changes.

## Related documentation

- [Documentation index](../README.md)
- [Redeployment runbook](../operations/redeploy.md)
- [Browser verification](../operations/browser-verification.md)
- [Chat UI event contract](../contracts/chat-ui-event-contract.md)
- [Conversation persistence contract](../contracts/conversation-persistence.md)
- [Certification index](../certification/README.md)
- [Implementation plan](../PLAN.md)
- [Durable architecture decisions](../../.agents/memory/decisions.md)
