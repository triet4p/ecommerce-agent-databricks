"""OAuth target-App resolution for the standalone Chat UI source bundle."""

import os
from typing import Any


def resolve_agent_app_url(client: Any) -> str:
    return client.apps.get(name=os.environ["AGENT_APP_NAME"]).url
