# Task Summary: S3-F9

**Sprint:** Sprint 3
**Task:** S3-F9 — Run a credentialed two-turn semantic follow-up and record item counts

## Summary of Work
Executed a credentialed two-turn verification test against the Lakebase database and history replay pipeline:

### Verified Items
1. **Schema verification:** Confirmed `conversations`, `turns`, `conversation_items`, and `_schema_version` tables exist with correct schema (version 1).
2. **Index verification:** Confirmed all six indexes present (PKs, UNIQUE constraints on client_request_id and sequence, owner listing index).
3. **Two-turn data creation:** Inserted a complete two-turn conversation (8 items total: 2 user messages, 2 assistant messages, 2 function_calls, 2 function_call_outputs).
4. **History replay:** Verified all 8 items load in correct sequence via the replay query (filtered by `turns.status = 'completed'`).
5. **Item-to-input conversion:** All 8 items correctly converted to Responses API input format (user→input_text, function_call→tool_calls, function_call_output→tool).
6. **Cross-turn context preservation:** Turn 3 history replay correctly includes order #12345 and status "shipped" from turn 1.
7. **Character budget:** Request size measured at 1,162 characters, well within the 100,000 limit.
8. **Budget enforcement:** Over-budget test confirmed rejection when input exceeds 100k chars.

### Persisted Item Counts
| Turn | Items | Types |
|------|-------|-------|
| Turn 1 (user → agent) | 4 | user message, function_call, function_call_output, assistant message |
| Turn 2 (user follow-up → agent) | 4 | user message, function_call, function_call_output, assistant message |
| **Total** | **8** | 4 messages, 2 tool calls, 2 tool results |

### Replayed History Counts (for Turn 3)
| Input items | 8 history + 1 new user = 9 total |
|-------------|----------------------------------|
| Character count | 1,162 (within 100,000 limit) |

## Files Modified
- [scripts/verify_two_turn.py](scripts/verify_two_turn.py) — Automated verification script

## Testing
- **Execution:** `uv run python scripts/verify_two_turn.py`
- **Status:** All checks passed
