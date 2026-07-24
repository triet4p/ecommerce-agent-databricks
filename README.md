# E-commerce Agent on Databricks

A production-style e-commerce support agent running on Databricks Apps. The
system combines a React chat UI, Lakebase conversation persistence, an MLflow
`ResponsesAgent`, governed Unity Catalog tools, custom retrieval/reranking, and
an optional MCP facade.

## Runtime topology

| Databricks App | Responsibility | Deployment artifact |
|---|---|---|
| `ecommerce-agent-app` | MLflow `AgentServer`, LangChain agent loop, governed tools | `.build/apps/agent_app` |
| `ecommerce-agent-chat-ui` | React UI and Lakebase persistence; switchable Streamlit demo | `.build/apps/chat_ui` or `.build/apps/streamlit_chat_ui` |
| `ecommerce-agent-mcp-facade` | Optional Streamable HTTP MCP integration | `.build/apps/mcp_facade` |

The Agent calls two existing Model Serving endpoints:

- `deepseek-v4-streaming-agent-lab` for model inference;
- `search-and-rerank-endpoint` for policy retrieval and reranking.

Unity Catalog production resources use catalog `ecommerce_agent`. Conversation
state is stored in the Lakebase project `ecommerce-agent-conversations`.

## Repository layout

```text
agent_core/                         reusable, use-case-independent agent core
ecommerce_agent/
  apps/
    agent_app/                      Agent App entry point and manifest
    chat_ui/                        React/Node monorepo and manifest
    mcp_facade/                     optional MCP facade and manifest
    streamlit_chat_ui/              switchable demo UI and manifest
  conversation/                     canonical persistence/service layer
  rules/                            always-loaded behavior
  skills/                           progressive-disclosure procedures
  tools/                            local and Databricks-backed tools
scripts/build_apps.py               builds isolated deployment source roots
data-processing/                    ingestion and transformation notebooks
tests/                              Python and deployment contract tests
docs/                               architecture, contracts, operations, plans
```

Application source stays under `ecommerce_agent/apps/`. Databricks deployment
never points directly at those directories: `scripts/build_apps.py` produces
self-contained, flattened source roots under `.build/apps/`.

## Prerequisites

- Python 3.13 and [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+ and npm 8+
- Databricks CLI 0.294+ with an OAuth-authenticated profile
- Access to the project-scoped Databricks resources declared in
  [`databricks.yml`](databricks.yml)

Never commit `.env`, Databricks tokens, OAuth tokens, customer data, or generated
credentials.

## Local setup and verification

```powershell
uv sync --all-groups
uv run pytest -q
uv run python -m compileall agent_core ecommerce_agent data-processing scripts
uvx ruff check .
uvx ruff format --check .
```

React/Node checks:

```powershell
Set-Location ecommerce_agent/apps/chat_ui
npm ci
npm run build
npm run typecheck
npm run lint
npm test
Set-Location ../../..
```

Credentialed integration tests are explicitly gated. Load credentials into the
current process only and follow the relevant test module; never print them.

## Build deployment artifacts

Run this before every bundle validation or deployment:

```powershell
uv run python scripts/build_apps.py
```

Expected output:

```text
.build/apps/
  agent_app/
  chat_ui/
  mcp_facade/
  streamlit_chat_ui/
```

The Agent artifact uses the packaged `pyproject.toml` and `uv.lock` with
`uv run --frozen`. Do not add a root `requirements.txt` to that artifact.

## Redeploy

Choose the Databricks profile explicitly. The examples use the project profile
`Ecommerce-Agent`:

```powershell
databricks auth profiles
databricks current-user me --profile Ecommerce-Agent

uv run python scripts/build_apps.py
databricks bundle validate --strict -t dev --profile Ecommerce-Agent
databricks bundle deploy -t dev --profile Ecommerce-Agent

databricks bundle run ecommerce_agent -t dev --profile Ecommerce-Agent
databricks bundle run ecommerce_agent_chat_ui -t dev --profile Ecommerce-Agent
```

Then verify:

```powershell
databricks apps get ecommerce-agent-app --profile Ecommerce-Agent -o json
databricks apps get ecommerce-agent-chat-ui --profile Ecommerce-Agent -o json
databricks apps logs ecommerce-agent-chat-ui --profile Ecommerce-Agent
```

The default Chat UI source is React. For the complete deployment, Streamlit
switch, smoke-test, restoration, and troubleshooting procedures, use the
[redeployment runbook](docs/operations/redeploy.md).

## Documentation

Start at the [documentation index](docs/README.md).

- [Current architecture](docs/architecture/ecommerce-agent-architecture.md)
- [Redeployment runbook](docs/operations/redeploy.md)
- [Chat event contract](docs/contracts/chat-ui-event-contract.md)
- [Conversation persistence contract](docs/contracts/conversation-persistence.md)
- [Implementation plan](docs/PLAN.md)
- [Certification index](docs/certification/README.md)
