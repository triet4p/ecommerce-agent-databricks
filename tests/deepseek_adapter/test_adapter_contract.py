import pytest
from mlflow.types.responses import ResponsesAgentRequest

from deepseek_adapter.adapter import (
    normalize_function_tools,
    responses_to_deepseek_messages,
)


def test_reasoning_tool_result_round_trip_is_preserved():
    request = ResponsesAgentRequest(
        input=[
            {
                "type": "reasoning",
                "id": "rs_1",
                "summary": [{"type": "summary_text", "text": "reason"}],
            },
            {
                "type": "function_call",
                "id": "fc_1",
                "call_id": "call_1",
                "name": "lookup",
                "arguments": "{}",
            },
            {"type": "function_call_output", "call_id": "call_1", "output": "ok"},
        ]
    )
    messages = responses_to_deepseek_messages(request.input)
    assert messages[0]["reasoning_content"] == "reason"
    assert messages[0]["tool_calls"][0]["id"] == "call_1"
    assert messages[1] == {"role": "tool", "tool_call_id": "call_1", "content": "ok"}


def test_tool_schema_and_unsupported_type_contract():
    assert (
        normalize_function_tools(
            [{"type": "function", "name": "lookup", "parameters": {"type": "object"}}]
        )[0]["function"]["name"]
        == "lookup"
    )
    with pytest.raises(ValueError, match="Unsupported tool type"):
        normalize_function_tools([{"type": "file_search"}])
