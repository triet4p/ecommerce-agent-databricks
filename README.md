# E-commerce Agent on Databricks

An e-commerce support agent hosted on Databricks Apps. It uses LangChain 1.x,
MLflow `ResponsesAgent`/`AgentServer`, `ChatDatabricks`, governed Unity Catalog
functions, local deterministic tools, and a custom reranking endpoint.

## Architecture and resource limits

The production agent is a Databricks App, not a Model Serving agent. The
workspace quota allows exactly two project-owned Model Serving endpoints:

| Endpoint | Purpose |
|---|---|
| `search-and-rerank-endpoint` | policy retrieval and custom reranking |
| `deepseek-v4-streaming-agent-lab` | isolated DeepSeek provider boundary |

Do not create temporary, per-environment, blue-green, or Agent Serving
endpoints. The DeepSeek endpoint is updated in place only after it is
`NOT_UPDATING`; the reranker is replaced only after a quality comparison.

Unity Catalog production resources use catalog `ecommerce_agent`, with
`agent_layer` functions and `gold_layer.order_summary`.

## Local development

```powershell
uv sync --all-groups
uv run python -m compileall agent_core ecommerce_agent data-processing
uv run pytest -v
uvx ruff check .
uvx ruff format --check .
```

Credentialed checks are gated. Load `DATABRICKS_HOST` and `DATABRICKS_TOKEN`
from `.env` into the current process only; never print or commit either value.

```powershell
$env:RUN_DATABRICKS_TESTS = '1'
uv run pytest tests/integration -m databricks -v
```

The local `mlflow.db` file is test output and is ignored by Git.

The DeepSeek singleton contract can be exercised without creating an endpoint:

```powershell
$env:RUN_DATABRICKS_TESTS = '1'
uv run pytest tests/integration/test_deepseek_chatdatabricks_contract.py -v
```

## Deploy the agent App

The root [databricks.yml](databricks.yml) defines one singleton App,
`ecommerce-agent-app`, its MLflow experiment, `CAN_QUERY` endpoint resources,
and `EXECUTE` grants for the governed functions. It never defines a Model
Serving endpoint resource.

```powershell
databricks bundle validate -t dev
databricks bundle validate -t prod
databricks bundle plan -t dev
databricks bundle deploy -t dev
databricks bundle run ecommerce_agent -t dev
```

Databricks Apps uses the root `pyproject.toml` plus `uv.lock`; do not add a root
`requirements.txt`, because it would override the locked `uv` install.

The App's externally authenticated Responses API is
`POST /api/responses`. The native MLflow `/responses` route remains available
inside the server, but an App-to-App or local API request needs an OAuth token
audience-scoped for `ecommerce-agent-app`; a workspace PAT is deliberately not
accepted by App ingress. Supply that token only in the process environment as
`DATABRICKS_AGENT_APP_OAUTH_TOKEN` to run the gated smoke test:

```powershell
$env:RUN_DATABRICKS_TESTS = '1'
uv run pytest tests/integration/test_agent_app_api_contract.py -v
```

## DeepSeek boundary

`deepseek_adapter/` is the only provider-specific package. It is deployed as a
custom Model Serving model and must never be imported by `agent_core` or the
Databricks App. It preserves reasoning through tool-result continuations and
rejects `tool_choice` in DeepSeek thinking mode. See
[the deployment module](deepseek_adapter/deployment.py),
[benchmark evidence](artifacts/k8_deepseek_benchmark_2026-07-20.md), and the
[AI Gateway matrix](docs/deepseek-ai-gateway-matrix.md).

## Verification status and known prerequisites

- Bundle dev/prod validation, Agent App startup, and Chat UI startup have been
  verified. Both use the documented `/api/responses` OAuth route.
- UC function contracts and the reranker have credentialed coverage.
- Managed MCP discovery and an unknown-ID UC-function invocation have been
  verified through the current per-function route. The code deliberately never
  falls back to `UCFunctionToolkit`; auth/grant failures stay visible.
- AI Gateway QPM/inference-table controls are not active on the current custom
  endpoint: the workspace rejects QPM-only configuration for this endpoint type.
  The deployment workflow retains the current SDK call shape for future
  capability changes; today the App enforces bounded input, graph steps, and
  model output instead.
- Chat UI and MCP façade have isolated source trees. The façade was recreated
  and starts successfully; both consumers parse the terminal Responses API
  message rather than assuming `output[0]` is text, so tool-loop responses are
  supported.

See [Sprint 1 plan](docs/sprint-plans/sprint-1.md) for task-level evidence and
[certification labs](docs/certification-labs/SPRINT_1_LABS.md) for isolated
hands-on exercises.
