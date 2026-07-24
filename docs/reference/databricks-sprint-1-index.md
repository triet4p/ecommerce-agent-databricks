# Databricks Sprint 1 Documentation Index

Last verified against official documentation: **2026-07-16**.

Purpose: give an implementation agent a task-oriented source index for
[Sprint 1](../sprint-plans/sprint-1.md). This is not a replacement for the sprint
acceptance criteria or the architecture decisions. It identifies which current
Databricks documentation is authoritative for each platform-facing task and
where the agent must rely on repository evidence instead of guessing.

## Mandatory Reading Order

Before implementing any Sprint 1 task, read:

1. [`AGENTS.md`](../../AGENTS.md) for repository constraints.
2. [Architecture decisions](../../.agents/memory/decisions.md), newest entry last.
3. [Global plan](../PLAN.md) and [Sprint 1](../sprint-plans/sprint-1.md).
4. The row for the selected task in this index.
5. The linked official pages again at implementation time if this index is more
   than 30 days old or the page is marked Preview/Beta.

## Source-of-Truth Rules

Use the following precedence to prevent API hallucination:

1. **Architecture and allowed behavior:** the sprint plan and ADRs in this
   repository.
2. **Exact Python signatures:** the packages installed from `uv.lock` plus
   first-party API references. Documentation snippets can target newer versions.
3. **Workspace behavior, permissions, and product lifecycle:** current official
   Databricks documentation for the workspace cloud (`aws` in the links below).
4. **DeepSeek protocol behavior:** the verified experiment and recorded lessons;
   Databricks documentation does not define DeepSeek V4's provider protocol.
5. **Business rules:** canonical e-commerce policy documents. Platform docs and
   evaluation examples must never be used to invent refund or shipping policy.

Do not use community posts, old notebooks, generated snippets, or search-result
summaries as implementation authority. If an official page conflicts with the
locked package signature or an ADR, stop and record the conflict instead of
silently changing dependencies or architecture.

## Locked Compatibility Baseline

The implementation target is:

| Component | Sprint 1 baseline | Verification source |
|---|---:|---|
| Python | 3.13 | [`pyproject.toml`](../../pyproject.toml) |
| `databricks-langchain` | 0.20.0 | `pyproject.toml` and `uv.lock` |
| `databricks-sdk` | 0.120.0 after A1; current lock already resolves 0.120.0 | `uv.lock` |
| LangChain | 1.x; current lock 1.3.13 | `uv.lock` |
| MLflow | 3.x; current lock 3.14.0 | `uv.lock` |

Documentation install commands are illustrative only. Do not run `pip install`,
copy an older version pin, or upgrade the root dependency graph to make a docs
snippet work. This repository is managed with `uv`.

## Current Product and Release-Stage Checkpoints

| Capability | Status observed on 2026-07-16 | Sprint interpretation |
|---|---|---|
| Databricks Apps agent authoring | Current recommended custom-agent path | Host the production agent on Apps, not Model Serving. |
| Declarative Automation Bundles | Current name; formerly Databricks Asset Bundles | Use current bundle schema and CLI terminology. |
| Managed MCP clients/servers | Public Preview | Check workspace enablement; never silently fall back to another transport. |
| Unity Catalog SQL/Python UDFs | Official UDF page marked Public Preview | Check supported compute and permissions before integration tests. |
| Prompt Registry in deployed apps | Beta | Keep optional and environment-configurable until explicitly enabled. |
| Databricks AI Search | Current name; formerly Vector Search | Do not blindly rename installed SDK modules or API fields. |
| Custom Python Model Serving | Current custom-model path | Allowed only as model/tool boundary; the agent still runs on Apps. |
| AI Gateway on custom endpoints | Capability-dependent | Use the official endpoint-type matrix; do not assume every control exists. |

## Task-to-Documentation Map

### A-B. Runtime, configuration, and imports

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| A1-A4 | `pyproject.toml`, `uv.lock`, banned-symbol list in Sprint 1 | [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html), [Databricks SDK workspace APIs](https://databricks-sdk-py.readthedocs.io/en/stable/clients/workspace.html), [Migrate to MLflow 3](https://docs.databricks.com/aws/en/mlflow3/genai/agent-eval-migration) | Inspect locked signatures. Do not import APIs merely because they appear in a newer docs example. Do not add legacy `databricks-agents<1.0` evaluation APIs. |
| B1-B3 | Repository config schema and YAML contract | [Define environment variables in a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/environment-variables), [Key concepts in Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/key-concepts) | Platform docs define injected resources, not this repository's Pydantic schema. Keep config paths repository-relative and endpoint names environment-driven. |
| B4-B6 | Repository package layout and public exports | No Databricks platform API is normative for Python package boundaries. | Remove `projects.ecommerce_support`; do not invent a Databricks-specific import root or workspace path. |

### C. Agent and tool construction

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| C1 | ADR plus locked `databricks-langchain` signature | [Author an AI agent on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent), [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html) | Production model construction is `ChatDatabricks(endpoint=..., use_responses_api=True)` plus LangChain 1.x `create_agent`; do not use provider-specific initialization in App/core. |
| C2-C5 | Existing `agent_core` public contracts and unit tests | [Connect agents to tools](https://docs.databricks.com/aws/en/agents/agent-framework/agent-tool), [Author agent: local Python tools](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) | Local registries and pure tools are repository concerns. Do not turn deterministic local calculations into UC functions without a governance reason. |
| C6-C8 | Managed MCP ADR and task acceptance tests | [Managed MCP servers](https://docs.databricks.com/aws/en/agents/mcp/managed-mcp), [Use MCP servers in agents](https://docs.databricks.com/aws/en/agents/mcp/use-mcp-in-agents), [Databricks LangChain MCP client API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html), [Managed MCP `_meta` parameters](https://docs.databricks.com/aws/en/agents/mcp/managed-mcp-meta-param) | Feature is Public Preview. For the LangChain production path, use the locked top-level `DatabricksMultiServerMCPClient`/`DatabricksMCPServer` API; do not replace it with a lower-level docs example without a plan change. Use allowlisted server URLs, declare all underlying App resources, and never trigger `UCFunctionToolkit` automatically after MCP failure. |
| C9 | Explicit compatibility target only | [Create agent tools using UC functions](https://docs.databricks.com/aws/en/agents/agent-framework/create-custom-tool), [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html) | Import only the documented top-level `UCFunctionToolkit`. Do not copy example version pins or use `databricks_langchain.uc_ai` internals. |
| C10-C14 | Sprint policy plus verified DeepSeek evidence | [Connect agents to tools](https://docs.databricks.com/aws/en/agents/agent-framework/agent-tool), [`lessons-learned.md`](../../.agents/memory/lessons-learned.md), [`DeepSeekServingEndpointStreaming.py`](../../experiments/DeepSeekServingEndpointStreaming.py) | Databricks docs do not guarantee DeepSeek `tool_choice`. Required/state-changing actions need deterministic routing, schema validation, and completion checks outside the prompt. |

### D. Rules, skills, and files

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| D1-D4 | ADR: rules and skills are source-controlled | [Key concepts in Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/key-concepts) | Default runtime files ship with App source. Do not introduce DBFS, `/Volumes`, sync jobs, or remote mutation into the default provider. |
| D5 | Optional Volume provider only | [Work with files in UC Volumes](https://docs.databricks.com/aws/en/volumes/volume-files), [Add resources to an App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources) | A Volume needs an explicit App resource and read-only permission. It is not the canonical source until publishing, versioning, cache, and rollback are designed. |

### E. Unity Catalog data and business tools

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| E1-E5 | One environment-aware three-level namespace | [UC UDFs](https://docs.databricks.com/aws/en/udf/unity-catalog), [UC permissions concepts](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/permissions-concepts), [Add a UDF resource to an App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/functions), [Medallion architecture](https://docs.databricks.com/aws/en/lakehouse/medallion) | Use `catalog.schema.object`. Execution requires `USE CATALOG`, `USE SCHEMA`, and `EXECUTE`; do not treat object creation as proof that the App can call it. |
| E6-E9 | Approved synthetic refund policy, then UC Python function contract | [UC UDFs](https://docs.databricks.com/aws/en/udf/unity-catalog) | Databricks docs only define function mechanics. Policy `SYNTH-REFUND-2026-01` is a user-approved learning artifact, not an Olist policy; changing its thresholds requires a new version and tests. |
| E10-E14 | Canonical shipping/product policy and local tests | [Author agent: local Python tools](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) | Local calculations remain deterministic and bounded. A configured tool is not complete until its implementation, backing data, and contract tests all exist. |

### F. Retriever and serving tool contract

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| F1-F3 | Typed repository request/response contract and SDK 0.120.0 signature | [Query custom model endpoints](https://docs.databricks.com/aws/en/machine-learning/model-serving/score-custom-model-endpoints), [Serving endpoints SDK API](https://databricks-sdk-py.readthedocs.io/en/stable/workspace/serving/serving_endpoints.html), [Query AI Search](https://docs.databricks.com/aws/en/ai-search/query-ai-search) | The reranker endpoint is not interchangeable with plain AI Search until quality and latency are measured. Preserve endpoint failures; do not return an empty success result for transport errors. |

### G-H. App hosting, deployment, and verification

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| G1-G3 | MLflow 3 `ResponsesAgent`/`AgentServer` contract | [Author an AI agent on Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent), [MLflow 3 for GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/) | Do not preserve handwritten FastAPI emulation or add `databricks.agents.deploy` as a fallback. Preserve typed tool-call and tool-result streaming events. |
| G4-G5 | Bundle-owned App and least-privilege resources | [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/), [Add resources to an App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources), [Use MCP servers in agents](https://docs.databricks.com/aws/en/agents/mcp/use-mcp-in-agents), [App environment variables](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/environment-variables) | Declare every direct and MCP-transitive resource under the App in `databricks.yml`. The App gets `CAN_QUERY` on the model endpoint and no DeepSeek secret access. |
| G6 | OAuth app-to-app invocation | [Build a multi-agent system on Apps](https://docs.databricks.com/aws/en/agents/agent-framework/multi-agent-apps), [Connect to an App API](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/connect-local), [App permissions](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/permissions) | App-to-app calls require OAuth and `CAN_USE` on the target App. Do not embed a PAT or copy one App's service-principal credentials into another. |
| H1-H6 | Sprint commands and credentialed smoke-test acceptance criteria | [Author an AI agent on Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent), [Bundle authentication](https://docs.databricks.com/aws/en/dev-tools/bundles/authentication) | Local import success is not a Databricks integration test. Validate both bundle targets and run the deployed App with its actual service-principal permissions. |

### I. Certification labs and retrieval/evaluation

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| I1-I5, I8 | Certification index and isolated labs | [Current exam guide](https://www.databricks.com/sites/default/files/2026-02/Databricks-Certified-Generative-AI-Engineer-Associate-Exam-Guide-Interrim-Feb26.pdf), [Create tools with UC functions](https://docs.databricks.com/aws/en/agents/agent-framework/create-custom-tool), [Deploy custom Python code](https://docs.databricks.com/aws/en/machine-learning/model-serving/deploy-custom-python-code), [Migrate to MLflow 3](https://docs.databricks.com/aws/en/mlflow3/genai/agent-eval-migration) | Labs may teach compatibility concepts but cannot become production imports or hidden fallbacks. Superseded APIs can be described, not executed by production code. |
| I6 | Retrieval lab | [Databricks AI Search](https://docs.databricks.com/aws/en/ai-search/ai-search), [Create AI Search indexes](https://docs.databricks.com/aws/en/ai-search/create-ai-search), [Query AI Search](https://docs.databricks.com/aws/en/ai-search/query-ai-search), [AI Search filtering](https://docs.databricks.com/aws/en/ai-search/filtering-guide) | Use current product name while preserving the exact installed SDK namespace. Select ANN/hybrid/filter/rerank behavior from measured retrieval quality, not docs marketing examples. |
| I7 | MLflow evaluation and AI governance lab | [Evaluate and monitor agents](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor), [MLflow 3 concepts](https://docs.databricks.com/aws/en/mlflow3/genai/concepts/), [AI Gateway endpoint matrix](https://docs.databricks.com/aws/en/ai-gateway/overview-serving-endpoints), [Configure AI Gateway](https://docs.databricks.com/aws/en/ai-gateway/configure-ai-gateway-endpoints), [Use Prompt Registry in apps](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/use-prompts-in-deployed-apps) | Use `mlflow.genai`, not MLflow 2 Agent Evaluation APIs. Prompt Registry is Beta. Verify controls per endpoint type rather than assuming parity. |

### J-K. Verified DeepSeek route and production model boundary

| Sprint tasks | Primary authority | Official references | Anti-hallucination constraint |
|---|---|---|---|
| J1-J5 | Completed experiment output and lessons | [Deploy custom Python code](https://docs.databricks.com/aws/en/machine-learning/model-serving/deploy-custom-python-code), [Create custom endpoints](https://docs.databricks.com/aws/en/machine-learning/model-serving/create-manage-serving-endpoints), [Secret-backed serving environment](https://docs.databricks.com/aws/en/machine-learning/model-serving/store-env-variable-model-serving) | Preserve the verified evidence: `ChatDatabricks` streaming, tool loop, and reasoning round-trip passed. Do not reinterpret the lab as permission to host the production agent on Model Serving. |
| K1-K3 | Verified adapter protocol extracted from the experiment | [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html), [Deploy custom Python code](https://docs.databricks.com/aws/en/machine-learning/model-serving/deploy-custom-python-code) | The adapter owns provider-specific normalization. App/core must not import `ChatDeepSeek`, provider credentials, or `experiments`. Keep explicit tests for unsupported `tool_choice`. |
| K4 | MLflow 3 model logging and UC registration | [Log, load, and register MLflow models](https://docs.databricks.com/aws/en/mlflow/models), [Manage model lifecycle in UC](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/) | Use the UC registry and three-level model name. Do not use the legacy Workspace Model Registry or infer a model version from “latest.” |
| K5-K7 | Endpoint update, creator identity, secrets, and lifecycle | [Create custom endpoints](https://docs.databricks.com/aws/en/machine-learning/model-serving/create-manage-serving-endpoints), [Secret-backed serving environment](https://docs.databricks.com/aws/en/machine-learning/model-serving/store-env-variable-model-serving), [Serving endpoints SDK API](https://databricks-sdk-py.readthedocs.io/en/stable/workspace/serving/serving_endpoints.html), [Monitor endpoint health](https://docs.databricks.com/aws/en/machine-learning/model-serving/monitor-diagnose-endpoints) | Endpoint creator identity is durable and needs UC plus secret access. Do not rely on the five-minute waiter; verify config/version and collect build/server logs on failure. |
| K8-K9 | Measured cost/latency gate and credentialed App E2E test | [Custom model endpoint scaling](https://docs.databricks.com/aws/en/machine-learning/model-serving/custom-models), [Model Serving overview](https://docs.databricks.com/aws/en/machine-learning/model-serving/), [Add resources to an App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources) | Scale-to-zero has cold-start cost and latency. DeepSeek is a production candidate only after measurement; direct provider access is not an automatic fallback. |
| K10-K12 | Verified AI Gateway capability matrix | [AI Gateway endpoint matrix](https://docs.databricks.com/aws/en/ai-gateway/overview-serving-endpoints), [Configure AI Gateway](https://docs.databricks.com/aws/en/ai-gateway/configure-ai-gateway-endpoints) | For custom endpoints, do not assume fallbacks or AI guardrails; route optimization also changes supported tracking/rate controls. Output guardrails do not apply to streaming. Implement explicit application/provider controls for uncovered gaps. |

## Handoff Checklist for an Implementation Agent

For each selected atomic task, the agent must include in its handoff:

- The task ID and exact acceptance criterion implemented.
- The official pages consulted and their observed release stage.
- The installed package signature inspected when a Python API was used.
- Tests run locally, plus credentialed Databricks evidence when required.
- Any official-doc/locked-version conflict, without resolving it by an
  unapproved upgrade.
- Confirmation that no banned legacy symbol, direct provider secret, or
  `experiments` import entered the production graph.

## Maintenance Rule

Update this index when a Sprint 1 task changes platform surface, an official page
moves, a Preview/Beta feature changes stage, or the dependency lock changes.
Changing a link alone does not authorize an architectural change; update the ADR
first when a decision changes.
