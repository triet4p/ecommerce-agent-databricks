"""Attach Lakebase Postgres resource to the Chat UI App."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import (
    App,
    AppResource,
    AppResourceApp,
    AppResourceAppAppPermission,
    AppResourcePostgres,
    AppResourcePostgresPostgresPermission,
)

w = WorkspaceClient(profile="Ecommerce-Agent")

resources = [
    AppResource(
        name="agent-app",
        app=AppResourceApp(
            name="ecommerce-agent-app",
            permission=AppResourceAppAppPermission.CAN_USE,
        ),
    ),
    AppResource(
        name="conversation-store",
        postgres=AppResourcePostgres(
            branch="projects/ecommerce-agent-conversations/branches/production",
            database="projects/ecommerce-agent-conversations/branches/production/databases/databricks-postgres",
            permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE,
        ),
    ),
]

wait = w.apps.create_update(
    app_name="ecommerce-agent-chat-ui",
    update_mask="resources",
    app=App(name="ecommerce-agent-chat-ui", resources=resources),
)
result = wait.result()
print(f"Update result: {result}")

# Verify the update was applied
updated = w.apps.get("ecommerce-agent-chat-ui")
print(f"Resources after update: {[r.name for r in updated.resources]}")
print("Successfully attached Lakebase postgres resource!")
