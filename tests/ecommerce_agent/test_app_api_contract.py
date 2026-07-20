"""Static contracts for the OAuth-protected Databricks App API path."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_agent_server_exposes_databricks_apps_api_responses_route() -> None:
    source = (ROOT / "ecommerce_agent" / "agent_app" / "server.py").read_text(
        encoding="utf-8"
    )

    assert '@app.post("/api/responses")' in source


def test_app_to_app_consumers_use_authenticated_api_prefix() -> None:
    for relative_path in (
        "ecommerce_agent/apps/chat_ui/app.py",
        "ecommerce_agent/apps/mcp_server/server.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert '"{agent_app_url}/api/responses"' in source
        assert '"{agent_app_url}/responses"' not in source


def test_app_to_app_timeout_exceeds_retriever_retry_budget() -> None:
    """Two 60-second attempts plus backoff must fit inside the caller budget."""
    for relative_path in (
        "ecommerce_agent/apps/chat_ui/app.py",
        "ecommerce_agent/apps/mcp_server/server.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "AGENT_REQUEST_TIMEOUT_SECONDS = 180" in source
        assert "timeout=AGENT_REQUEST_TIMEOUT_SECONDS" in source
