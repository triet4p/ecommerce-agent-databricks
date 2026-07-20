"""Credentialed Databricks Apps Responses API contract.

The test requires an OAuth token scoped to the target App. A workspace PAT is
deliberately not accepted by the Apps ingress and must not be copied here.
"""

from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.databricks


@pytest.mark.skipif(
    not (
        os.getenv("RUN_DATABRICKS_TESTS") == "1"
        and os.getenv("DATABRICKS_AGENT_APP_OAUTH_TOKEN")
    ),
    reason=(
        "set RUN_DATABRICKS_TESTS=1 and DATABRICKS_AGENT_APP_OAUTH_TOKEN "
        "to a token audience-scoped for ecommerce-agent-app"
    ),
)
def test_agent_app_responses_api_streams_over_oauth() -> None:
    """Exercise the platform-required ``/api`` ingress without logging a token."""
    import requests
    from databricks.sdk import WorkspaceClient

    app = WorkspaceClient().apps.get(name="ecommerce-agent-app")
    response = requests.post(
        f"{app.url}/api/responses",
        headers={
            "Authorization": f"Bearer {os.environ['DATABRICKS_AGENT_APP_OAUTH_TOKEN']}"
        },
        json={
            "input": [{"role": "user", "content": "Reply with APP_API_SMOKE_OK."}],
            "stream": True,
        },
        stream=True,
        timeout=180,
    )
    assert response.status_code == 200, response.text[:500]
    events = [
        line[6:]
        for line in response.iter_lines(decode_unicode=True)
        if line and line.startswith("data: ")
    ]
    assert len(events) > 1
    assert events[-1] == "[DONE]"
