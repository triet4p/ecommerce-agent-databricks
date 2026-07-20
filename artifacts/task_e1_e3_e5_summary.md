# Task Summary: E1, E3, E5 Canonical UC functions

**Sprint:** Sprint 1
**Task:** E1, E3, E5

## Summary of Work

Unified production namespace references on
`ecommerce_agent.agent_layer` and `ecommerce_agent.gold_layer`. Completed the
seller-performance and shipping-delay SQL table functions against the actual
`order_summary` schema, then deployed and smoke-tested all four business
functions in the live workspace.

## Files Modified

* `ecommerce_agent/tools/sql_tools.py` - Canonical namespace and functions backed by `order_summary`.
* `tests/ecommerce_agent/test_sql_ddl.py` - Namespace and dynamic-limit contract tests.
* `ecommerce_agent/config.yaml` - Canonical UC function and Prompt Registry examples.
* `ecommerce_agent/driver.py` - Canonical AI Gateway catalog/schema.
* `ecommerce_agent/register_prompt.py` - Canonical Prompt Registry name.
* `agent_core/config_schema.py` - Canonical config examples.

## Testing

* **Test File:** `tests/ecommerce_agent/test_sql_ddl.py`
* **Status:** Passed (27 tests); live warehouse deployment and smoke tests passed.
* **Execution Command:** `.\\.venv\\Scripts\\python.exe -m pytest tests/ecommerce_agent/test_sql_ddl.py -v`

## Additional Notes

The active workspace has `ecommerce_agent.agent_layer` and
`ecommerce_agent.gold_layer`; the four functions are deployed under the former.
E4 remains open because no application service principal has yet been declared
for least-privilege grants.
