# Task Summary: F1-F3 Retriever serving contract

**Sprint:** Sprint 1
**Task:** F1, F2, F3

## Summary of Work

Added typed retrieval request/response models, an injectable SDK client for
network-free contract tests, an effective caller-side timeout, safe source
label rendering, and normalization for the deployed model's `results_json`
prediction envelope. Endpoint failures remain failures rather than empty results.

## Files Modified

* `agent_core/retriever_interface.py` - Typed contract, injected client, and timeout/error mapping.
* `ecommerce_agent/tools/search_policy_docs_tool.py` - Source-safe rendering.
* `tests/ecommerce_agent/test_retriever_contract.py` - Fake-client production contract tests.

## Testing

* **Test File:** `tests/ecommerce_agent/test_retriever_contract.py`
* **Status:** F1/F2 passed (16 tests); F3 remains in progress.
* **Execution Command:** `.\\.venv\\Scripts\\python.exe -m pytest tests/ecommerce_agent/test_retriever_contract.py -v`

## Additional Notes

Malformed envelopes now raise a typed runtime error instead of becoming an
empty retrieval. The SDK 0.120.0 query call receives only `name` and
`dataframe_split`; the caller-side timeout is effective but cannot cancel an
already-running SDK HTTP worker, so F3 remains open. The live endpoint
`search-and-rerank-endpoint` is `READY`/`NOT_UPDATING`, serves model v4, and
returned three non-empty chunks with parsed source and score fields.
