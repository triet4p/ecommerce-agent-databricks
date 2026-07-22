# Sprint 3 — Remaining Deployment Steps

These steps require the Databricks CLI to be available for write operations.
Run them when the CLI classifier permits `databricks bundle deploy`.

## Manual Steps

```bash
# 1. Deploy the Bundle (adds Lakebase postgres resource to Chat UI App)
cd f:/ai-ml/ecommerce-agent-databricks
databricks bundle deploy -t dev -p Ecommerce-Agent

# 2. Start / restart the Chat UI App
databricks apps start ecommerce-agent-chat-ui -p Ecommerce-Agent

# 3. Verify deployment
databricks apps get ecommerce-agent-chat-ui -p Ecommerce-Agent -o json

# 4. Verify Lakebase binding (check environment variables in App logs)
databricks apps logs ecommerce-agent-chat-ui -p Ecommerce-Agent
```

## Post-Deployment Verification

1. Open the Chat UI App URL.
2. Create a new conversation.
3. Send a message (e.g., "Where is my order?").
4. Verify the conversation persists after page refresh.
5. Create a second turn and verify the agent receives prior context.
6. Check App logs for credential leakage.

## Rollback

If deployment fails, the previous app state is preserved (deployments are
snapshot-based). Revert `databricks.yml` to remove the Lakebase resource
and redeploy.
