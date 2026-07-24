"""Regression tests for the source-isolated MCP App Responses parser."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PARSERS = (ROOT / "ecommerce_agent" / "apps" / "mcp_server" / "response_output.py",)


def _parser(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract_response_text


@pytest.mark.parametrize("path", PARSERS)
def test_extracts_terminal_message_after_tool_items(path: Path):
    extract = _parser(path)
    payload = {
        "output": [
            {"type": "function_call", "name": "get_order_status", "arguments": "{}"},
            {"type": "function_call_output", "output": "{}"},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Order is pending."}],
            },
        ]
    }

    assert extract(payload) == "Order is pending."


@pytest.mark.parametrize("path", PARSERS)
def test_extracts_only_the_last_assistant_message(path: Path):
    extract = _parser(path)
    payload = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Intermediate."}],
            },
            {"type": "function_call", "name": "get_order_status"},
            {"type": "function_call_output", "output": "{}"},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Final line one."},
                    {"type": "output_text", "text": "Final line two."},
                ],
            },
        ]
    }

    assert extract(payload) == "Final line one.\nFinal line two."


@pytest.mark.parametrize("path", PARSERS)
def test_rejects_response_without_terminal_message(path: Path):
    with pytest.raises(ValueError, match="final assistant message"):
        _parser(path)({"output": [{"type": "function_call"}]})
