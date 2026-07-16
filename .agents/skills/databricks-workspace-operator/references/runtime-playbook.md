# Databricks Runtime Playbook

Last verified in this repository: 2026-07-15. Recheck official documentation
before relying on feature availability, SDK signatures, or preview status.

## Repository baseline

- `databricks-sdk==0.120.0`
- `databricks-langchain==0.20.0`
- `langchain==1.3.13`
- `mlflow==3.14.0`
- Unity Catalog invariant for the current project: `workspace`
- Production model caller: `ChatDatabricks`
- Provider-specific serving adapter: isolated experiment/custom model only

## Safe environment loading in PowerShell

Read only the required lines and put their values into the current process. Do
not echo `$env:DATABRICKS_TOKEN` and do not dump the environment.

```powershell
$pairs = Get-Content -LiteralPath '.env' |
  Where-Object { $_ -match '^\s*(DATABRICKS_HOST|DATABRICKS_TOKEN)\s*=' }

foreach ($pair in $pairs) {
  $parts = $pair -split '=', 2
  [Environment]::SetEnvironmentVariable(
    $parts[0].Trim(),
    $parts[1].Trim().Trim('"').Trim("'"),
    'Process'
  )
}
```

## Minimal preflight

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
me = w.current_user.me()
catalog = w.catalogs.get("workspace")

assert catalog.name == "workspace"
print("AUTH_OK")
print("USER=" + (me.user_name or me.display_name or "<unknown>"))
print("CATALOG=" + catalog.name)
```

Never print `w.config`, headers, or exception request bodies until checking that
they do not contain credentials.

## Serverless notebook job pattern

Current official examples use a notebook task without a cluster definition for
serverless Jobs:

```python
from databricks.sdk.service.jobs import NotebookTask, Source, Task

job = w.jobs.create(
    name="descriptive-debug-job",
    tasks=[
        Task(
            task_key="smoke",
            notebook_task=NotebookTask(
                notebook_path="/Users/me@example.com/project/smoke",
                source=Source.WORKSPACE,
                base_parameters={"catalog": "workspace"},
            ),
            timeout_seconds=1800,
        )
    ],
)
run = w.jobs.run_now(job_id=job.job_id)
```

Use the task run ID for `jobs.get_run_output()`. Add a structured notebook exit
when the result must be retrievable through the API:

```python
dbutils.notebook.exit(json.dumps({"status": "OK", "catalog": "workspace"}))
```

## Endpoint create/update pattern

```python
from datetime import timedelta
from databricks.sdk.errors import NotFound

def report_status(endpoint) -> None:
    print({
        "ready": str(endpoint.state.ready),
        "config_update": str(endpoint.state.config_update),
    })

try:
    existing = w.serving_endpoints.get(name=endpoint_name)
except NotFound:
    endpoint = w.serving_endpoints.create(
        name=endpoint_name,
        config=config,
    ).result(
        timeout=timedelta(minutes=30),
        callback=report_status,
    )
else:
    if not str(existing.state.config_update).endswith("NOT_UPDATING"):
        w.serving_endpoints.wait_get_serving_endpoint_not_updating(
            name=endpoint_name,
            timeout=timedelta(minutes=30),
            callback=report_status,
        )
    endpoint = w.serving_endpoints.update_config(
        name=endpoint_name,
        served_entities=served_entities,
    ).result(
        timeout=timedelta(minutes=30),
        callback=report_status,
    )

assert str(endpoint.state.ready).endswith("READY")
assert str(endpoint.state.config_update).endswith("NOT_UPDATING")
```

If the initial create call itself times out, check `get(name)` before retrying.
Never submit a duplicate create blindly.

## Secret environment variables

Use a reference in the served entity:

```python
environment_vars={
    "DEEPSEEK_API_KEY": "{{secrets/API_KEY/DEEPSEEK_API_KEY}}",
}
```

After deployment, inspect only `environment_vars.keys()` and assert the expected
key exists. An endpoint created through the UI can be ready yet lack the secret
reference needed by the custom model.

## MLflow ResponsesAgent runtime tools

MLflow 3.14.0's standard ResponsesAgent signature was observed to serialize the
`tools` column as `Array({type: string})`. Databricks Model Serving then rejected
the full function fields before invoking Python. This repository widens only
that column after logging:

```python
from mlflow.models import ModelSignature
from mlflow.types.responses import (
    RESPONSES_AGENT_INPUT_SCHEMA,
    RESPONSES_AGENT_OUTPUT_SCHEMA,
)
from mlflow.types.schema import AnyType, Array, ColSpec, Schema

inputs = Schema([
    ColSpec(Array(AnyType()), name="tools", required=False)
    if column.name == "tools"
    else column
    for column in RESPONSES_AGENT_INPUT_SCHEMA.inputs
])
signature = ModelSignature(inputs=inputs, outputs=RESPONSES_AGENT_OUTPUT_SCHEMA)
mlflow.models.set_signature(logged_model.model_uri, signature)
```

Re-evaluate this workaround when MLflow changes its standard signature. Do not
keep workaround code after upstream behavior is verified fixed.

## DeepSeek V4 thinking-mode contract

- It supports tool calls but rejects `tool_choice`.
- It requires assistant reasoning to be replayed after a tool call.
- Bind tools without `auto`, `required`, or a named choice.
- Preserve the reasoning item, function call, and tool result in order.
- Require a non-empty assistant content representation alongside tool calls when
  the provider contract requires it.
- Test at least two user turns and assert both a tool call and reasoning item.

The verified experiment is
`experiments/DeepSeekServingEndpointStreaming.py`. Keep it isolated from the
Databricks Apps production path.

## Official references

- Databricks SDK for Python: https://docs.databricks.com/aws/en/dev-tools/sdk-python
- Serverless Jobs: https://docs.databricks.com/aws/en/jobs/run-serverless-jobs
- Create/manage serving endpoints: https://docs.databricks.com/aws/en/machine-learning/model-serving/create-manage-serving-endpoints
- Secret environment variables: https://docs.databricks.com/aws/en/machine-learning/model-serving/store-env-variable-model-serving
- Query a deployed agent: https://docs.databricks.com/aws/en/agents/agent-framework/query-agent
- Databricks LangChain API: https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html
- MLflow ResponsesAgent: https://mlflow.org/docs/latest/genai/serving/responses-agent/
- DeepSeek thinking mode: https://api-docs.deepseek.com/guides/thinking_mode

