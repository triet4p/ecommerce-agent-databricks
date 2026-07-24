# Databricks Apps Redeployment Runbook

Use this runbook to rebuild, validate, deploy, start, verify, switch, and restore
the three project Databricks Apps.

## Scope and safety

- Select the Databricks CLI profile explicitly; never rely on an implicit
  default.
- The canonical catalog is `ecommerce_agent`.
- The bundle declares exactly three Apps. React and Streamlit share the
  `ecommerce-agent-chat-ui` resource and are not deployed simultaneously.
- Do not run `databricks bundle destroy` for a redeployment.
- Do not create temporary Model Serving endpoints. The two endpoint names in
  `databricks.yml` are existing singleton dependencies.

Examples below use:

```text
Profile: Ecommerce-Agent
Target:  dev
```

Replace them only after confirming the intended workspace and target.

## 1. Preflight

From the repository root:

```powershell
databricks --version
databricks auth profiles
databricks current-user me --profile Ecommerce-Agent
git status --short
```

Expected project identity is the workspace user that owns the bundle root.
Stop if the profile points to another workspace or the working tree contains
unreviewed changes.

## 2. Run local gates

```powershell
uv sync --all-groups
uv run pytest -q
uv run python -m compileall agent_core ecommerce_agent data-processing scripts
uvx ruff check .
uvx ruff format --check .

Set-Location ecommerce_agent/apps/chat_ui
npm ci
npm run build
npm run typecheck
npm run lint
npm test
Set-Location ../../..
```

Integration tests that require Databricks or PostgreSQL credentials remain
separately gated. Do not convert an environment skip into an unconditional test.

## 3. Build isolated App sources

This step is mandatory after every source, manifest, dependency, or lockfile
change:

```powershell
uv run python scripts/build_apps.py
```

Verify the four roots:

```powershell
Get-ChildItem .build/apps
```

| Artifact | Root dependency mechanism |
|---|---|
| `agent_app` | `pyproject.toml` + `uv.lock`; starts with `uv run --frozen` |
| `chat_ui` | root `package.json` + `package-lock.json` |
| `mcp_facade` | component-owned `requirements.txt` |
| `streamlit_chat_ui` | component-owned `requirements.txt` |

Do not deploy directly from `ecommerce_agent/apps/*`. Databricks flattens each
`source_code_path`; the generated roots are the tested runtime contract.

## 4. Validate the bundle

Validate warnings as errors:

```powershell
databricks bundle validate --strict -t dev --profile Ecommerce-Agent
databricks bundle validate --strict -t prod --profile Ecommerce-Agent
```

Validate the Streamlit override separately:

```powershell
databricks bundle validate --strict -t dev --profile Ecommerce-Agent `
  --var chat_ui_source=.build/apps/streamlit_chat_ui
```

Resolve every strict-validation warning before deployment.

## 5. Deploy the default React topology

```powershell
databricks bundle deploy -t dev --profile Ecommerce-Agent
```

Start or restart the Agent and Chat UI resources:

```powershell
databricks bundle run ecommerce_agent -t dev --profile Ecommerce-Agent
databricks bundle run ecommerce_agent_chat_ui -t dev --profile Ecommerce-Agent
```

The MCP facade is optional. Start it only when the integration surface is
required:

```powershell
databricks bundle run ecommerce_agent_mcp_facade -t dev `
  --profile Ecommerce-Agent
```

## 6. Verify status and logs

```powershell
databricks apps get ecommerce-agent-app --profile Ecommerce-Agent -o json
databricks apps get ecommerce-agent-chat-ui --profile Ecommerce-Agent -o json
databricks apps get ecommerce-agent-mcp-facade --profile Ecommerce-Agent -o json
```

For started Apps, require:

```text
active_deployment.status.state = SUCCEEDED
app_status.state                = RUNNING
compute_status.state            = ACTIVE
```

Inspect logs:

```powershell
databricks apps logs ecommerce-agent-app --profile Ecommerce-Agent
databricks apps logs ecommerce-agent-chat-ui --profile Ecommerce-Agent
```

`databricks apps logs` requires OAuth authentication. If the profile uses a PAT,
use `apps get` for status and reauthenticate with OAuth before requesting logs.

## 7. Browser smoke test

Open the URL returned by `databricks apps get ecommerce-agent-chat-ui`.

Verify:

1. trusted user identity and healthy Agent/Lakebase status;
2. existing owner-scoped conversation history;
3. incremental response progress and final assistant text;
4. tool arguments/results when the prompt requires a tool;
5. Markdown rendering;
6. reload hydration and a second turn;
7. retry, Stop/cancel, error, rename, and delete behavior as applicable.

Use [browser-verification.md](browser-verification.md) for the full parity
checklist.

## 8. Switch the Chat UI slot to Streamlit

Build and validate first, then deploy and run with the same override:

```powershell
uv run python scripts/build_apps.py

databricks bundle validate --strict -t dev --profile Ecommerce-Agent `
  --var chat_ui_source=.build/apps/streamlit_chat_ui

databricks bundle deploy -t dev --profile Ecommerce-Agent `
  --var chat_ui_source=.build/apps/streamlit_chat_ui

databricks bundle run ecommerce_agent_chat_ui -t dev `
  --profile Ecommerce-Agent `
  --var chat_ui_source=.build/apps/streamlit_chat_ui
```

In the authenticated browser, verify existing history and complete one new
turn. Record the deployment ID before restoring React.

## 9. Restore React after the Streamlit demo

Omitting `chat_ui_source` restores the default React artifact:

```powershell
uv run python scripts/build_apps.py
databricks bundle deploy -t dev --profile Ecommerce-Agent
databricks bundle run ecommerce_agent_chat_ui -t dev `
  --profile Ecommerce-Agent
```

Verify that React reads both pre-switch history and the Streamlit-created turn.
Delete only the temporary smoke conversation.

## 10. Recovery

If a new deployment fails:

1. keep unrelated Apps and platform resources unchanged;
2. inspect `databricks apps logs <app-name>`;
3. check that `.build/apps/<app>/app.yaml` and root dependency files match the
   intended runtime;
4. rebuild from the last known-good Git commit;
5. rerun strict validation, deploy, and the relevant `bundle run` command.

Databricks App deployments are snapshots, but source-controlled rebuild and
redeploy is the canonical recovery procedure because it is reproducible and
auditable.

## Common failures

| Symptom | Likely cause | Action |
|---|---|---|
| Old Streamlit/Node runtime starts | stale or wrong `chat_ui_source` | rebuild, inspect bundle summary, deploy with the intended variable |
| `ModuleNotFoundError` after deploy | imports assume repository root instead of flattened artifact root | reproduce import from `.build/apps/<app>` and fix packaging |
| App listens on localhost | framework default host | bind `0.0.0.0` and `DATABRICKS_APP_PORT` |
| App starts but has no database | missing `conversation-store` binding | inspect App resources and `LAKEBASE_ENDPOINT` |
| Agent source preparation fails before logs | conflicting root dependency entry points | keep Agent on `pyproject.toml` + `uv.lock`; no root `requirements.txt` |
| App remains stopped after bundle deploy | deployment updated source but compute was not started | run the matching `databricks bundle run <resource-key>` |

