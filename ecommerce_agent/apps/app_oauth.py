"""App-to-app OAuth helpers shared by the chat UI and MCP facade."""

from __future__ import annotations

import os
from typing import Any


def resolve_agent_app_url(client: Any) -> str:
    """Resolve the target App URL from its resource-injected name.

    Databricks App resources deliberately expose the target App *name*, not a
    hard-coded URL. The caller's service-principal credentials are discovered by
    ``WorkspaceClient`` and carry the resource's ``CAN_USE`` permission.
    """
    app_name = os.environ["AGENT_APP_NAME"]
    return client.apps.get(name=app_name).url
