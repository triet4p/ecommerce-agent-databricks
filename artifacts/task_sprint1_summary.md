# Sprint 1 Implementation Summary

**Completed:** 2026-07-20
**Branch:** `main`
**Canonical catalog:** `ecommerce_agent`

## Outcome

Sprint 1 delivers the modern, non-legacy e-commerce support vertical slice:

- LangChain 1.x `create_agent` with `ChatDatabricks(use_responses_api=True)`.
- MLflow 3 `ResponsesAgent` and `AgentServer` hosted on Databricks Apps.
- Instance-scoped tools, explicit managed-MCP/`UCFunctionToolkit` transports,
  deterministic required-operation workflows, and request-local safety gates.
- Source-controlled rules and skills with deterministic path resolution.
- Governed order, customer, seller, shipping, and synthetic refund-policy UC
  functions under `ecommerce_agent.agent_layer`.
- Typed search-and-rerank integration with transport timeout, bounded cold-start
  retry, strict malformed-response handling, and caller timeout alignment.
- Declarative Automation Bundle targets, least-privilege App resources, OAuth
  Agent App, Chat UI, and custom MCP façade.
- Isolated DeepSeek V4 adapter served from
  `ecommerce_agent.gold_layer.deepseek_v4_streaming_agent@4` through the existing
  singleton endpoint; the App/core never import provider code or credentials.
- Certification labs and official-document mappings for UC functions, MCP,
  Apps, Model Serving, retrieval, MLflow, evaluation, and AI Gateway.

## Runtime evidence

- Project endpoints remain exactly `search-and-rerank-endpoint` and
  `deepseek-v4-streaming-agent-lab`; both were `READY / NOT_UPDATING`.
- DeepSeek singleton serves canonical version 4 at 100% traffic.
- Agent App, Chat UI, and MCP façade deployments were `SUCCEEDED / RUNNING`.
- Deployment source hashes matched the local orchestrator, retriever, terminal
  response parsers, and MCP requirements.
- OAuth Agent SSE, direct `ChatDatabricks` reasoning/tool continuation, and MCP
  `function_call -> function_call_output -> final message` smokes passed.
- Managed UC functions and the reranker returned typed, non-empty live results.
- Development and production Bundle targets validated successfully.

## Verified limitations and safeguards

- A QPM-only AI Gateway request using SDK 0.120.0 returned
  `Rate limits is not currently supported for this endpoint type in this
  workspace.` Endpoint read-back contains no active `ai_gateway` config. This is
  recorded as a workspace capability result, not a product-wide limitation.
- The fallback safety envelope caps caller input at 100,000 characters,
  LangGraph execution at 12 steps, and model output at 1,500 tokens per call.
- Chat UI and MCP façade use a 180-second outer timeout so the retriever's two
  60-second attempts can finish.
- Exact combined Databricks Serving plus provider billing is unavailable in the
  Free Edition workspace. The provider price/formula and measured latency are
  recorded in `k8_deepseek_benchmark_2026-07-20.md`; paid production requires a
  new billing-data measurement.
- MLflow's public App response intentionally does not expose hidden provider
  reasoning. Reasoning replay is asserted at the `ChatDatabricks` boundary, and
  the App boundary separately asserts the complete tool loop and final message.

## Source of truth

Task-level completion and workspace evidence are recorded in
`docs/sprint-plans/sprint-1.md`. `docs/PLAN.md` records Sprint 1 as completed.
Historical experiment artifacts under the `workspace` catalog are not production
defaults and do not supersede the canonical `ecommerce_agent` namespace.
