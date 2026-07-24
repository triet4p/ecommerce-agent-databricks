"""Static contracts for the OAuth-protected Databricks App API path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_agent_server_exposes_databricks_apps_api_responses_route() -> None:
    source = (ROOT / "ecommerce_agent" / "apps" / "agent_app" / "server.py").read_text(
        encoding="utf-8"
    )

    assert '@app.post("/api/responses")' in source


def test_agent_server_exposes_authenticated_health_route() -> None:
    source = (ROOT / "ecommerce_agent" / "apps" / "agent_app" / "server.py").read_text(
        encoding="utf-8"
    )

    assert '@app.get("/api/health")' in source


def test_agent_server_registers_warmup_on_supported_router_lifecycle() -> None:
    source = (ROOT / "ecommerce_agent" / "apps" / "agent_app" / "server.py").read_text(
        encoding="utf-8"
    )

    assert "app.router.on_startup.append(_retriever_warmup.start)" in source
    assert "app.router.on_shutdown.append(_retriever_warmup.stop)" in source
    assert "\n    app.add_event_handler(" not in source


def test_agent_runtime_execs_uvicorn_for_sigterm_delivery() -> None:
    app_config = (ROOT / "app.yaml").read_text(encoding="utf-8")

    assert "exec uv run --frozen uvicorn" in app_config


def test_app_to_app_consumers_use_authenticated_api_prefix() -> None:
    for relative_path in ("ecommerce_agent/apps/mcp_facade/server.py",):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert '"{agent_app_url}/api/responses"' in source
        assert '"{agent_app_url}/responses"' not in source


def test_retriever_budget_fits_inside_databricks_apps_proxy_limit() -> None:
    """Retrieval must leave time for the model/tool loop under the 120s proxy."""
    config = (ROOT / "ecommerce_agent" / "config.yaml").read_text(encoding="utf-8")
    assert "timeout_seconds: 45" in config
    assert "cold_start_retry_attempts: 0" in config

    for relative_path in ("ecommerce_agent/apps/mcp_facade/server.py",):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "AGENT_REQUEST_TIMEOUT_SECONDS = 180" in source
        assert "timeout=AGENT_REQUEST_TIMEOUT_SECONDS" in source
