"""
agent_app.server
--------------------
Host agent on Databricks Apps using MLflow ``AgentServer`` (ResponsesAgent
invoke/stream registration). This is the Databricks-recommended hosting path
for new custom agents.

The ``CoreAgent`` (agent_core.orchestrator) is built directly in the App
process; requests go to this App, not through Model Serving.

See Also:
    - Databricks docs: "Author an AI agent on Databricks Apps"
    - MLflow 3 ``AgentServer`` API (mlflow.genai.agent_server)
"""

from __future__ import annotations

import logging
import os

from fastapi import Request
from mlflow.genai.agent_server.server import AgentServer, invoke, stream

from agent_core import Retriever, ToolRegistry, build_agent, load_config
from ecommerce_agent.agent_app.handlers import invoke_agent, stream_agent
from ecommerce_agent.agent_app.retriever_warmup import RetrieverWarmup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Build the agent once at startup. The config file path is resolved relative
# to this source file so that the App works regardless of the working directory.
# ---------------------------------------------------------------------------

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
_config = load_config(_CONFIG_PATH)

_registry = ToolRegistry()
_retriever_warmup: RetrieverWarmup | None = None

if _config.retriever is not None:
    _retriever = Retriever(_config.retriever)
    _retriever_warmup = RetrieverWarmup(
        _retriever.search,
        interval_seconds=float(
            os.environ.get("RETRIEVER_WARM_INTERVAL_SECONDS", "900")
        ),
    )
    from ecommerce_agent.tools.search_policy_docs_tool import (
        make_search_policy_docs_tool,
    )

    _registry.register_serving_factory(
        "search_policy_docs",
        lambda tool_config: make_search_policy_docs_tool(_retriever, tool_config),
    )

AGENT = build_agent(_config, registry=_registry)

# ---------------------------------------------------------------------------
# Register invoke/stream handlers for the MLflow AgentServer
# ---------------------------------------------------------------------------


@invoke()
def agent_invoke(request: dict) -> dict:
    """Non-streaming ResponsesAgent invoke handler."""
    return invoke_agent(AGENT, request)


@stream()
def agent_stream(request: dict):
    """SSE streaming ResponsesAgent handler."""
    yield from stream_agent(AGENT, request)


# ---------------------------------------------------------------------------
# Create the AgentServer with the registered handlers.
# ---------------------------------------------------------------------------

agent_server = AgentServer(agent_type="ResponsesAgent")
app = agent_server.app

if _retriever_warmup is not None:
    # FastAPI 0.128 no longer exposes ``app.add_event_handler``; AgentServer's
    # router still owns the startup/shutdown handler lists used by its lifespan.
    app.router.on_startup.append(_retriever_warmup.start)
    app.router.on_shutdown.append(_retriever_warmup.stop)


@app.get("/api/health")
async def app_api_health() -> dict[str, bool]:
    """Report that the AgentServer process is ready to accept API requests."""
    return {"healthy": True}


@app.post("/api/responses")
async def app_api_responses(request: Request):
    """Expose the Responses API through Databricks Apps' authenticated API prefix.

    Databricks Apps accepts bearer-token API calls at ``/api/<endpoint>``.  Keep
    MLflow's native ``/responses`` route for local/standard AgentServer clients,
    while routing App-to-App OAuth calls through the platform-supported path.
    """
    return await agent_server._handle_invocations_request(request)


# ---------------------------------------------------------------------------
# Local dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
