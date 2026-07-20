# Sprint 1 Certification Labs

These exercises are isolated from the production import graph. Use the project
workspace credentials and catalog `ecommerce_agent`; do not create an endpoint
for a lab. The two approved endpoints are reused only where stated.

## I2 — Unity Catalog SQL and Python functions

**Goal:** inspect and execute one current UC SQL function and one UC Python
function through the Statement Execution API.

1. Run `DESCRIBE FUNCTION EXTENDED ecommerce_agent.agent_layer.get_order_status`.
2. Execute `SELECT * FROM ecommerce_agent.agent_layer.get_order_status('<known-order-id>')`.
3. Run `DESCRIBE FUNCTION EXTENDED ecommerce_agent.agent_layer.check_refund_eligibility`.
4. Execute the Python UDF with a documented synthetic-policy case and an
   unsupported case; retain the typed explanation returned by each.
5. Confirm the caller has `USE CATALOG ecommerce_agent`, `USE SCHEMA
   ecommerce_agent.agent_layer`, and `EXECUTE` on both functions.

The reusable live contract is [test_uc_function_contract.py](../../tests/integration/test_uc_function_contract.py).
It is intentionally gated by `RUN_DATABRICKS_TESTS=1`.

## I3 — UCFunctionToolkit versus managed MCP

**Goal:** compare tool schemas without silently changing transport.

In a compatible serverless Python environment, build
`databricks_langchain.UCFunctionToolkit` from the five allowlisted function
names and record each tool's `name`, JSON schema, and description. Then discover
the same allowlist through the managed MCP URL and record the equivalent fields.
Compare function names, required inputs, descriptions, and auth failure mode.

The direct toolkit adapter is [uc_toolkit_adapter.py](../../agent_core/uc_toolkit_adapter.py);
the MCP lifecycle contract is [mcp_lifecycle.py](../../agent_core/mcp_lifecycle.py).
Local Spark Connect initialization is known to be incompatible with the locked
protobuf graph, so run this lab on Databricks rather than changing dependencies.

## I4 — Managed MCP allowlist and failures

**Goal:** discover and invoke an allowlisted UDF through a managed MCP server.

1. Construct `DatabricksMCPServer.from_uc_function` for
   `ecommerce_agent.agent_layer.get_order_status`. The locked client derives
   the current `/api/2.0/mcp/functions/<catalog>/<schema>/<function>` route
   and OAuth from `WorkspaceClient`; do not check in a workspace URL.
2. Discover tools and assert exactly that encoded function tool is exposed.
3. Invoke it asynchronously with an unknown order ID and assert the returned
   tabular envelope has `rows: []`.
4. Remove `EXECUTE` in an isolated test principal (or use a principal without
   the grant) and capture the authentication/authorization failure.
5. Restore grants and close the client session.

The production path must never fall back to `UCFunctionToolkit` if discovery or
execution fails. The live project smoke on 2026-07-20 discovered all five
allowlisted functions and verified the unknown-order empty envelope.

## I6 — Retrieval quality experiment

Run [CreateDocumentEvalDataset.py](../../data-processing/CreateDocumentEvalDataset.py)
on serverless against the existing policy corpus and
`search-and-rerank-endpoint`. Compare fixed-size versus structure-aware chunks,
ANN versus hybrid retrieval, metadata filters, and the custom reranker using:

| Metric | Definition |
|---|---|
| Recall@k | target document appears in first `k` results |
| MRR | reciprocal rank of first target document |
| p50/p95 latency | endpoint invocation elapsed time |
| Context relevance | MLflow judge or documented SME rubric |

Record query IDs, corpus version, endpoint model version, `top_k`, filters,
quality metrics, and cost/latency trade-off. Do not replace the reranker with AI
Search unless this comparison demonstrates equivalent quality.

## I7 — Evaluation and governance

Use the 15 rows in `ecommerce_agent.bronze_layer.eval_queries` as an evaluation
dataset. Create an MLflow 3 run that captures traces, retrieval outputs, tool
calls, answer quality, context relevance, latency, and an SME rubric. Register
the prompt only through the Prompt Registry alias workflow.

For the DeepSeek custom endpoint, document each AI Gateway control as verified,
unsupported, or not applicable before configuring it. At minimum distinguish
inference tables, QPM, TPM, and streaming output guardrails. Do not claim a
Gateway output guardrail covers streamed provider output; apply the App's
streaming safety policy as the compensating control.

## I8 — Current versus superseded API matrix

| Current API / pattern | Superseded or prohibited pattern | Reason |
|---|---|---|
| `ChatDatabricks(..., use_responses_api=True)` | `ChatDeepSeek` in App/core | provider boundary stays in serving adapter |
| `langchain.agents.create_agent` | `AgentExecutor`, `create_tool_calling_agent`, LangGraph `create_react_agent` | locked LangChain 1.x path |
| MLflow `ResponsesAgent` + `AgentServer` on Apps | `databricks.agents.deploy` or agent Model Serving | App is the hosting boundary |
| top-level `UCFunctionToolkit` | `databricks_langchain.uc_ai` | documented public integration only |
| `DatabricksMultiServerMCPClient` | implicit MCP-to-toolkit fallback | transport must be explicit |
| Declarative Automation Bundles | legacy Asset Bundle terminology/examples | current CLI schema and release name |
| `mlflow.genai` evaluation APIs | MLflow 2 Agent Evaluation APIs | MLflow 3 contract |

For every lab, record command/run IDs, resource state, endpoint version, and
terminal assertion without recording credential or secret values.
