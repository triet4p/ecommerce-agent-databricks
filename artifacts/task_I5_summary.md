# Task Summary: I5 DeepSeek Model Serving Streaming Lab

**Sprint:** Sprint 1
**Task:** I5

## Summary of Work

Added a self-contained Databricks source notebook that directly initializes the
current DeepSeek V4 LangChain integration, packages it as an MLflow
`ResponsesAgent` model adapter, verifies its MLflow signature, registers it in
Unity Catalog, and creates or updates a small scale-to-zero Model Serving
endpoint with a secret-backed API key. The caller now uses the intended
`ChatDatabricks(use_responses_api=True)` interface. The final test streams two
user turns with forced tool calls, forwards the tool schemas to DeepSeek, emits
reasoning items, reconstructs `reasoning_content` for subsequent DeepSeek calls,
and fails if the reasoning/tool round-trip is not actually exercised.

## Files Modified

* [experiments/DeepSeekServingEndpointStreaming.py](../experiments/DeepSeekServingEndpointStreaming.py) - Self-contained Databricks notebook for the direct and served DeepSeek streaming experiment.
* [tests/experiments/test_deepseek_serving_notebook.py](../tests/experiments/test_deepseek_serving_notebook.py) - Static contract tests for notebook format, current API pins, secret handling, and streaming assertions.
* [docs/sprint-plans/sprint-1.md](../docs/sprint-plans/sprint-1.md) - Marks certification lab task I5 complete.
* [docs/CERTIFICATION_INDEX.md](../docs/CERTIFICATION_INDEX.md) - Links the implemented lab to current official Databricks documentation.

## Testing

* **Test File:** [tests/experiments/test_deepseek_serving_notebook.py](../tests/experiments/test_deepseek_serving_notebook.py)
* **Status:** Passed
* **Execution Command:** `.venv\\Scripts\\python.exe tests\\experiments\\test_deepseek_serving_notebook.py -v`

## Additional Notes

* The notebook was not run against Databricks or DeepSeek, as requested. Its
  integration cells require workspace credentials, Unity Catalog permissions,
  the configured secret, and paid Model Serving compute.
* The notebook uses an explicit `deepseek-v4-flash` default because DeepSeek has
  scheduled the `deepseek-chat` and `deepseek-reasoner` aliases for retirement on
  2026-07-24.
* A successful final cell now establishes that this exact route streamed two
  tool-calling turns without dropping DeepSeek reasoning. It does not establish
  that every future provider/model version uses the same metadata shape.
