# Ecommerce Agent Target Architecture

**Status:** Target architecture for Sprint 1  
**Architecture version:** 0.1  
**Last reviewed:** 2026-07-15  
**Diagram:** [Editable draw.io source](ecommerce-agent-architecture.drawio)

## Purpose

This document is the durable architecture reference for the e-commerce support
agent. It explains where each responsibility lives, how requests and data flow,
which Databricks capability owns each concern, and which paths exist only for
compatibility or certification study.

The target is deliberately modern:

- Python 3.13, LangChain 1.x, `databricks-langchain==0.20.0`,
  `databricks-sdk==0.120.0`, and MLflow 3.x.
- Databricks Apps plus MLflow `AgentServer` and `ResponsesAgent` for production
  hosting.
- LangChain `create_agent` plus `ChatDatabricks` for orchestration and model
  access.
- Managed MCP as the production transport for governed Unity Catalog functions
  when the workspace feature is enabled.
- No legacy runtime fallback and no automatic transport fallback.

## Diagram Pages and Notation

The draw.io file contains three pages:

1. **Production Runtime** — request, prompt, model, tool, retrieval, governance,
   and observability flow.
2. **Data and Delivery** — ingestion, Delta layers, AI Search, source packaging,
   deployment, identities, and optional integration Apps.
3. **Placement Decisions** — the decision rules for UC Functions, local tools,
   serving tools, MCP, rules, and skills.

Line notation:

- Solid navy line: synchronous production request or data dependency.
- Dashed blue line: asynchronous deployment, ingestion, or observability flow.
- Dashed gray line: optional or future path.
- Dashed orange line: compatibility or certification-only path.

The diagram uses Databricks' published Lava, Navy, Oat, and White palette and
self-contained vector glyphs. It does not embed a modified Databricks trademark
logo or depend on remote image URLs. This keeps the source editable and usable
offline while respecting the official brand guidance.

## 1. Production Runtime

### 1.1 Entry points

The production runtime is the **Agent App**. It is deployed on Databricks Apps
and exposes the MLflow Responses API contract:

1. An authenticated client sends a `/responses` request.
2. MLflow `AgentServer` handles invoke and streaming transport.
3. `CoreAgent`, implemented as an MLflow `ResponsesAgent`, translates the
   request to the LangChain message contract and preserves tool-call and
   tool-result events.
4. LangChain `create_agent` runs the tool-calling loop.
5. `ChatDatabricks` calls the configured Foundation Model API or serving
   endpoint.

The App is built once at process startup. Request-specific state must not leak
through process-global registries.

### 1.2 Prompt composition

Prompt context has three distinct lifecycles:

| Content | Runtime behavior | Canonical location |
|---|---|---|
| Base system prompt | Loaded at agent construction; may resolve from a Prompt Registry alias | `ecommerce_agent/config.yaml` and MLflow Prompt Registry |
| Rules | Always appended to the system prompt, so the list stays small | `ecommerce_agent/rules/*.md` |
| Skills | Progressive disclosure through `list_skills` and `load_skill`; full content is loaded only when selected | `ecommerce_agent/skills/*.md` |

Rules and skills are packaged with the App source by default. They are behavior,
not operational data, so Git review, tests, deployment, and rollback must stay
atomic. A read-only UC Volume skill provider is an optional future extension
only when content needs a publishing lifecycle independent of an App release.

### 1.3 Tool routing

#### Governed Unity Catalog functions

Use UC Functions for reusable, permissioned business or data logic that benefits
from Unity Catalog discovery, lineage, grants, and auditability.

Planned SQL table functions:

- `get_order_status`
- `get_customer_order_history`
- `get_seller_performance`
- `get_shipping_delay_stats`

Planned Python UC function:

- `check_refund_eligibility` — backed by a versioned policy matrix and returning
  a typed explanation for unsupported or ambiguous claims.

The production agent discovers and invokes an explicit allowlist of these
functions through the **Databricks managed Unity Catalog functions MCP server**.
The App service principal receives only `USE CATALOG`, `USE SCHEMA`, and
`EXECUTE` privileges required for the allowlist.

`UCFunctionToolkit` is not the automatic production fallback. It belongs to:

- a deliberately selected compatibility deployment target for a workspace
  without managed MCP; and
- certification labs that compare toolkit and MCP tool schemas.

If managed MCP discovery or authentication fails in the MCP target, the request
fails observably. It must never silently switch transport.

#### Local deterministic tools

Use in-process LangChain tools when logic is pure, fast, testable, requires no
external resource, and gains no material governance benefit from UC execution:

- `compute_delay_severity`
- `customer_value_score`
- skill discovery and loading (`list_skills`, `load_skill`)

`customer_value_score` may assist prioritization but must not determine service
eligibility.

#### Search and rerank serving tool

`search_policy_docs` remains a thin local adapter around the custom
search-and-rerank Model Serving endpoint. It is not a UC Python function because
the implementation requires service calls and model-backed reranking that do
not fit a sandboxed UC Python function.

The endpoint:

1. queries the AI Search index with over-fetch and metadata filters;
2. reranks candidate chunks;
3. returns typed, source-safe results to the agent.

It must not be replaced by a plain AI Search MCP call until retrieval quality,
latency, and cost are compared on the same evaluation dataset.

### 1.4 Model access and AI Gateway

`ChatDatabricks` calls the configured LLM serving endpoint. Unity AI Gateway is
applied to that endpoint for supported controls such as:

- usage and cost tracking;
- inference tables;
- rate limiting;
- endpoint permissions and governance.

The agent itself runs on Databricks Apps rather than being deployed as an agent
Model Serving endpoint.

### 1.5 Observability

MLflow tracing records the agent span hierarchy, including prompt resolution,
model calls, retrieval, tool calls, tool results, latency, and errors. Offline
evaluation uses versioned evaluation datasets, built-in and custom scorers, and
SME rubrics. AI Gateway inference tables complement traces with model endpoint
usage and cost data.

Sensitive customer fields must be redacted or excluded before traces and
inference tables become production evidence stores.

## 2. Data and Retrieval Architecture

### 2.1 Structured commerce data

Olist source data follows a medallion flow:

1. Raw source files land in a governed UC Volume.
2. Ingestion creates Bronze Delta tables with source fidelity.
3. Transformations create validated Silver entities.
4. Gold Delta tables expose agent-ready order, customer, seller, shipping, and
   policy-matrix facts.
5. UC SQL/Python functions read the Gold contract rather than embedding table
   joins and policy thresholds in the agent prompt.

All catalog, schema, table, volume, function, and vector index names derive from
one environment-aware namespace contract.

### 2.2 Policy documents

Policy PDFs and other unstructured documents are operational data, so they live
in a UC Volume rather than in the application package. The document pipeline
parses, normalizes, chunks, and writes source metadata into a Delta chunk table.
An AI Search index is synchronized from that table.

Every returned chunk must retain a stable source identifier. Refund logic must
use an auditable, versioned policy matrix; retrieved prose alone is insufficient
for deterministic eligibility decisions.

### 2.3 What does not belong in Volumes

The following remain in Git and are deployed with source:

- Python application code;
- validated configuration;
- small always-on rules;
- progressive-disclosure skills;
- Declarative Automation Bundle definitions;
- unit tests and certification labs.

This distinction prevents mutable Volume files from changing agent behavior
without code review or a reproducible release.

## 3. App and Integration Topology

### Required App

**Agent App** contains the production agent runtime. It owns no browser UI and
does not expose its internal business logic as ad-hoc HTTP tools.

### Optional Apps

- **Chat UI App** is a thin authenticated client for end users. It invokes the
  Agent App using documented app-to-app OAuth and has no agent logic.
- **Custom MCP facade App** exposes the whole support agent as one MCP tool for
  other agents or development clients. This is an inbound integration surface;
  it is different from the outbound managed MCP client used by the Agent App to
  call UC Functions.

The optional Apps require explicit `CAN_USE` and OAuth configuration. They must
not share static tokens or inherit broader workspace permissions.

## 4. Deployment and Identity

The root `pyproject.toml` and `uv.lock` are the runtime dependency source of
truth. Declarative Automation Bundles deploy development and production targets,
including:

- Agent App source, command, and environment variables;
- App resource declarations for the LLM endpoint, reranker endpoint, MLflow
  experiment, and enabled governed resources;
- grants for the App service principal;
- data jobs and required platform resources where supported by the bundle.

Each App uses its own service principal identity. User identity is used for
front-door authentication; downstream resource access uses the App identity and
least-privilege grants. No hostnames, OAuth tokens, or workspace credentials are
committed to source.

## 5. Placement Decision Table

| Need | Put it here | Why |
|---|---|---|
| Governed query over UC data | UC SQL function | Native data access, grants, reuse, auditability |
| Governed deterministic policy logic | UC Python function | Central reusable contract with typed parameters and result |
| Pure calculation with no external state | Local LangChain tool | Lowest latency and simplest unit testing |
| Network call, large model, or custom reranking | Thin local adapter plus serving endpoint | Keeps heavy/network behavior outside the UC function sandbox |
| UC function discovery/execution in production | Managed MCP client/server | Current governed, interoperable tool transport |
| Workspace without managed MCP | Explicit compatibility target using top-level `UCFunctionToolkit` | Visible operational choice; no hidden fallback |
| Mandatory short instruction | Rule in source | Always present and versioned with code |
| Situational long procedure | Skill in source | Progressive disclosure avoids permanent prompt cost |
| Independently published content library | Optional read-only UC Volume provider | Separate lifecycle only when publishing requirements justify it |
| Raw or generated business data/documents | UC Volume and Delta tables | Governed operational data lifecycle |
| Agent hosting | Databricks App plus MLflow `AgentServer` | Current production App path |
| Agent interoperability | Optional custom MCP facade App | Exposes the agent without duplicating its internal tools |

## 6. Explicit Non-Goals and Legacy Boundary

The production import graph must not contain:

- `databricks.agents.deploy` as an agent hosting fallback;
- a hand-written FastAPI emulation of the Responses API;
- LangChain `AgentExecutor`, `create_tool_calling_agent`, or LangGraph
  `create_react_agent`;
- `databricks_langchain.uc_ai` internal imports;
- `projects.ecommerce_support` paths;
- DBFS paths for code, configuration, rules, or skills;
- an automatic MCP-to-toolkit fallback.

MLflow pyfunc, UC model registration, Model Serving agent exercises, and direct
`UCFunctionToolkit` exercises may exist under certification labs. They must be
clearly labeled and must not be imported by production code.

## 7. Known Decisions Still Requiring Validation

- Managed MCP is a workspace capability that must be checked before selecting
  the production MCP target.
- App-to-App OAuth for the optional UI and custom MCP facade must be verified in
  the deployment workspace with `CAN_USE` grants.
- The custom search-and-rerank endpoint remains until an evaluation demonstrates
  that a simpler AI Search integration meets the same quality and latency gate.
- A future persistent conversation-memory store is not part of Sprint 1 and
  needs an explicit data retention and privacy decision.
- The canonical refund policy corpus must be available before deterministic
  eligibility logic is implemented.

## 8. Maintaining This Living Document

Update this document and the draw.io source in the same change whenever any of
these change:

- a production hosting or tool transport;
- the canonical location of rules, skills, prompts, or business data;
- an App boundary or downstream resource;
- a Unity Catalog object or permission boundary;
- a request, retrieval, ingestion, or observability flow;
- a compatibility or certification-only path.

Update procedure:

1. Change the relevant diagram page and bump `Architecture version`.
2. Update the affected section and placement table here.
3. Update `.agents/memory/decisions.md` for a durable architectural decision.
4. Update `docs/CERTIFICATION_INDEX.md` if certification coverage changes.
5. Update the sprint task and run the draw.io XML validation check.
6. Re-review linked official documentation if it is more than 90 days old or a
   dependency/platform version changes.

## Official References

Reviewed on 2026-07-15:

- [Databricks reference architectures](https://docs.databricks.com/aws/en/lakehouse-architecture/reference)
- [Databricks brand guidance](https://brand.databricks.com/iconography)
- [Author an AI agent and deploy it on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent)
- [Productionize an agent on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/productionize-agent)
- [Add resources to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources)
- [Build multi-agent systems on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/multi-agent-apps)
- [Use MCP servers in agents](https://docs.databricks.com/aws/en/agents/mcp/use-mcp-in-agents)
- [Databricks managed MCP servers](https://docs.databricks.com/aws/en/agents/mcp/managed-mcp)
- [Unity Catalog tools with LangChain](https://docs.databricks.com/aws/en/agents/agent-framework/unity-catalog-tool-integration)
- [Unity Catalog user-defined functions](https://docs.databricks.com/aws/en/udf/unity-catalog)
- [Work with files in Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files)
- [Recommendations for files and Volumes](https://docs.databricks.com/aws/en/files/files-recommendations)
- [Delta Lake](https://docs.databricks.com/aws/en/delta)
- [Create an AI Search index](https://docs.databricks.com/aws/en/ai-search/create-ai-search)
- [MLflow 3 for GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/)
- [Use prompts in deployed applications](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/use-prompts-in-deployed-apps)
- [Unity AI Gateway](https://docs.databricks.com/aws/en/ai-gateway)
- [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)

## Related Repository Documents

- [Implementation plan](../PLAN.md)
- [Sprint 1 plan](../sprint-plans/sprint-1.md)
- [Certification coverage index](../CERTIFICATION_INDEX.md)
- [Durable architecture decisions](../../.agents/memory/decisions.md)
