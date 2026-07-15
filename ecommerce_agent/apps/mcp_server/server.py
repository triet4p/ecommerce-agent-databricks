"""
apps.mcp_server.server
--------------------------
Custom MCP server, deploy như 1 Databricks App riêng. Expose agent (giờ host trực tiếp
trên Databricks Apps — `agent_app/server.py`, không qua Model Serving) như 1 MCP tool
duy nhất, để agent khác (multi-agent supervisor, Claude Code lúc dev...) gọi qua chuẩn
MCP thay vì gọi thẳng REST.

NOTE (đã rà lại 2026-07, đổi theo current state): cùng caveat với chat_ui — App gọi
App chưa có resource wiring sẵn trong databricks.yml, dùng OAuth header từ
`WorkspaceClient().config.authenticate()`; verify lại cách lấy token chính xác nhất
theo docs tại thời điểm deploy.
"""

import os

import requests
from databricks.sdk import WorkspaceClient
from mcp.server.fastmcp import FastMCP

AGENT_APP_URL = os.environ["AGENT_APP_URL"]

mcp = FastMCP("ecommerce-support-agent")


@mcp.tool()
def ask_ecommerce_support(question: str) -> str:
    """Hỏi agent hỗ trợ khách hàng e-commerce (đơn hàng, chính sách, hoàn tiền).
    question: câu hỏi bằng ngôn ngữ tự nhiên, có thể kèm order_id/customer_id nếu có."""
    w = WorkspaceClient()
    headers = w.config.authenticate()
    response = requests.post(
        f"{AGENT_APP_URL}/responses",
        headers=headers,
        json={"input": [{"role": "user", "content": question}], "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["output"][0]["content"][0]["text"]


if __name__ == "__main__":
    # Databricks Apps chạy container HTTP — dùng streamable-http transport, không phải stdio.
    mcp.run(transport="streamable-http")
