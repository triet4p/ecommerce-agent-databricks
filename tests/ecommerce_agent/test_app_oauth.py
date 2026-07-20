from types import SimpleNamespace

from ecommerce_agent.apps.app_oauth import resolve_agent_app_url


def test_target_app_url_is_resolved_from_resource_injected_name(monkeypatch):
    monkeypatch.setenv("AGENT_APP_NAME", "ecommerce-agent-app")
    client = SimpleNamespace(
        apps=SimpleNamespace(
            get=lambda *, name: SimpleNamespace(
                name=name,
                url="https://ecommerce-agent-app.example.databricksapps.com",
            )
        )
    )

    assert resolve_agent_app_url(client) == (
        "https://ecommerce-agent-app.example.databricksapps.com"
    )
