# Sprint 1 Closeout Summary

**Completed:** 2026-07-20
**Catalog:** `ecommerce_agent`
**Endpoint budget:** two existing project endpoints; no third endpoint created

## Findings closed

1. App-to-App callers now use a 180-second timeout, exceeding the retriever's
   two 60-second attempts plus backoff and model/tool overhead.
2. Chat UI and MCP response parsers scan backward and return only the terminal
   assistant message; multi-message regression tests prevent concatenating an
   intermediate message.
3. Request-local operation gates remain isolated. Application fallback controls
   cap request input at 100,000 characters, LangGraph execution at 12 steps, and
   model output at 1,500 tokens per call.
4. DeepSeek deployment contract fixtures use the canonical
   `ecommerce_agent.gold_layer` model. Historical `workspace` artifacts are
   explicitly labeled as migration sources only.
5. Global plan, Sprint plan, implementation summary, certification index,
   README, AI Gateway matrix, benchmark, and lessons learned agree on the final
   deployment and verified limitations.
6. Credentialed UC tests now skip cleanly when the explicit warehouse variable
   is absent instead of raising an environment `KeyError`.

## Local verification

- `uv run pytest -q -p no:cacheprovider`: 250 passed, 4 skipped, 37 subtests.
- `python -m compileall`: clean.
- `ruff check .`: clean.
- `ruff format --check .`: 64 files formatted.
- `git diff --check`: clean.

## Workspace verification

- Bundle validation: development and production `Validation OK`.
- Bundle dev deployment: complete.
- Agent App deployment `01f184166f6f1014831fc63e83f1888c`: `SUCCEEDED`,
  App `RUNNING`.
- Chat UI deployment `01f184169b8b1af18bc776464e411b8c`: `SUCCEEDED`, App
  `RUNNING`.
- MCP façade deployment `01f184169f401ab8b7ffc9b817b4375b`: `SUCCEEDED`, App
  `RUNNING`.
- Snapshot hashes matched local orchestrator, Chat UI app/parser, and MCP
  server/parser source.
- DeepSeek endpoint: `READY / NOT_UPDATING`, serving
  `ecommerce_agent.gold_layer.deepseek_v4_streaming_agent@4`.
- OAuth Agent SSE and direct `ChatDatabricks` streaming reasoning/tool contracts
  passed.
- Full credentialed integration suite: 4 passed in one clean run.
- UC order and synthetic refund-policy credentialed tests passed; the serverless
  warehouse was returned toward its prior stopped state after the test.
- MCP façade order tool loop passed with boolean `isError=False` and terminal
  delivered-order text.
- App logs contain no new request-processing error from the verified smokes. The
  Agent App emitted one system-only SIGTERM timeout while replacing the previous
  snapshot; the new deployment reached `SUCCEEDED/RUNNING` and handled all
  subsequent contracts.

## AI Gateway capability result

The SDK 0.120.0 QPM-only request used endpoint QPM 15 and no inference table. It
returned:

```text
Rate limits is not currently supported for this endpoint type in this workspace.
```

Endpoint read-back still exposes no `ai_gateway` config. QPM 15 is therefore a
tested desired configuration, not an active control. The repository keeps the
current SDK workflow for future workspace capability changes and uses the
application safety envelope in this deployment.

## Cost evidence

Measured cold/warm latency and the current DeepSeek V4 Flash price formula are
recorded in `k8_deepseek_benchmark_2026-07-20.md`. Exact combined Databricks
Serving plus provider billing is unavailable in Free Edition, so the current
deployment is a learning/dev baseline rather than a paid-production cost claim.
