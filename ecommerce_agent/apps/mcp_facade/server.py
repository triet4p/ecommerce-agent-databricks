"""
apps.mcp_facade.server
--------------------------
Custom MCP server deployed as a separate Databricks App. Exposes the e-commerce
support agent as a single MCP tool for multi-agent supervision or developer
tooling.

Uses OAuth app-to-app authentication.
"""

import requests
from databricks.sdk import WorkspaceClient
from mcp.server.fastmcp import FastMCP

from app_oauth import resolve_agent_app_url
from response_output import extract_response_text

mcp = FastMCP("ecommerce-support-agent")
AGENT_REQUEST_TIMEOUT_SECONDS = 180


@mcp.tool()
def ask_ecommerce_support(question: str) -> str:
    """Ask the e-commerce support agent about orders, policies, or refunds.

    Args:
        question: Natural language question, may include order_id or customer_id.
    """
    w = WorkspaceClient()
    agent_app_url = resolve_agent_app_url(w)
    headers = w.config.authenticate()
    response = requests.post(
        f"{agent_app_url}/api/responses",
        headers=headers,
        json={"input": [{"role": "user", "content": question}], "stream": False},
        # The retriever can spend up to two 60-second attempts warming from
        # scale-to-zero. Keep the outer App-to-App budget above that bound plus
        # model/tool-loop overhead so the bounded retry can actually complete.
        timeout=AGENT_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return extract_response_text(response.json())


if __name__ == "__main__":
    # Databricks Apps run container HTTP — use streamable-http transport.
    mcp.run(transport="streamable-http")
