# Task Summary: J1-J5 DeepSeek/ChatDatabricks Runtime Verification

**Sprint:** Sprint 1  
**Tasks:** J1-J5  
**Date:** 2026-07-15

## Outcome

Streaming works through the intended route:

`serverless notebook -> ChatDatabricks(use_responses_api=True) -> Databricks Model Serving -> MLflow ResponsesAgent -> ChatDeepSeek -> DeepSeek V4 Flash`

The final evidence run completed with `TERMINATED / SUCCESS`, no task error, and
an untruncated notebook result:

- catalog: `workspace`
- endpoint: `deepseek-v4-streaming-agent-lab`
- registered model: `workspace.gold_layer.deepseek_v4_streaming_agent`, version 4
- turn 1: 1 tool call, 1 reasoning round-trip, 33 stream chunks, 28 visible text deltas
- turn 2: 1 tool call, 1 reasoning round-trip, 140 stream chunks, 135 visible text deltas
- Databricks run ID: `843390409034780`

## Root Causes Fixed

1. Five minutes was too short for custom model image creation, and a waiter was
   required before querying.
2. An endpoint created through the UI lacked the `DEEPSEEK_API_KEY` served-entity
   environment variable.
3. MLflow 3.14's standard ResponsesAgent signature rejected full runtime function
   tools before Python execution; the `tools` input was widened to `Array(Any)`.
4. DeepSeek V4 thinking mode rejected `tool_choice`; tools are now bound without
   that parameter and their use is asserted after inference.
5. A second endpoint update raced an update already in progress; the notebook now
   waits for `NOT_UPDATING` before submission.

## Verification

- Local notebook contract tests: 10 passed.
- Python compile check: passed for `experiments` and `tests/experiments`.
- Live endpoint simple stream: 5 chunks, 3 visible text deltas, reasoning and text blocks observed.
- Live two-turn local caller: passed through `ChatDatabricks`.
- Live serverless smoke run: passed with the metrics above.
