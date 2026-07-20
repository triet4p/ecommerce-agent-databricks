# Task Summary: C8 Managed MCP contracts

**Sprint:** Sprint 1
**Task:** C8

## Summary of Work

Discovery is isolated per configured server before allowlisting, duplicate tool
names are rejected, and failures identify the affected server. The locked MCP
client owns ephemeral session cleanup inside `get_tools()`; discovery does not
retain or leak direct sessions.

## Files Modified

* `agent_core/mcp_lifecycle.py` - Per-server discovery and duplicate detection.
* `tests/agent_core/test_mcp_lifecycle.py` - Discovery, isolation, auth, duplicate, and cleanup lifecycle contracts.

## Testing

* **Test File:** `tests/agent_core/test_mcp_lifecycle.py`
* **Status:** Passed
* **Execution Command:** `.\\.venv\\Scripts\\python.exe -m pytest tests/agent_core/test_mcp_lifecycle.py -q`

## Additional Notes

Managed MCP remains Preview; live discovery still requires a configured managed
MCP server and appropriate workspace entitlement/grants.
