"""Pure MLflow AgentServer handler adapters.

Keeping request parsing and serialization here makes the public App contract
testable without importing the production server, which constructs workspace
clients at module startup.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from mlflow.types.responses import ResponsesAgentRequest


def _as_agent_request(
    request: dict[str, Any] | ResponsesAgentRequest,
) -> ResponsesAgentRequest:
    """Accept direct handler dictionaries and AgentServer-validated requests."""
    if isinstance(request, ResponsesAgentRequest):
        return request
    return ResponsesAgentRequest(**request)


def invoke_agent(
    agent: Any, request: dict[str, Any] | ResponsesAgentRequest
) -> dict[str, Any]:
    """Validate an AgentServer request and serialize the agent response."""
    agent_request = _as_agent_request(request)
    return agent.predict(agent_request).model_dump()


def stream_agent(
    agent: Any, request: dict[str, Any] | ResponsesAgentRequest
) -> Generator[dict[str, Any], None, None]:
    """Validate an AgentServer request and serialize each SSE event."""
    agent_request = _as_agent_request(request)
    for event in agent.predict_stream(agent_request):
        yield event.model_dump()
