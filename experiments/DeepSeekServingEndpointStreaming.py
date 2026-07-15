# Databricks notebook source
# MAGIC %md
# MAGIC # ChatDatabricks over a DeepSeek V4 custom Model Serving endpoint
# MAGIC
# MAGIC This isolated certification experiment tests the intended model route,
# MAGIC including the adapter that previously looked risky:
# MAGIC
# MAGIC Architecture:
# MAGIC
# MAGIC `LangChain agent/tool loop -> ChatDatabricks(use_responses_api=True) -> custom Model Serving endpoint -> MLflow ResponsesAgent adapter -> init_chat_model(provider="deepseek") -> DeepSeek API`
# MAGIC
# MAGIC Important boundaries:
# MAGIC
# MAGIC - The caller is `ChatDatabricks`, matching the intended application model
# MAGIC   interface. Its current Responses API mode is used instead of a legacy
# MAGIC   MLflow `ChatModel` or `ChatAgent` contract.
# MAGIC - This is **not** an External Model Endpoint. Databricks hosts a small CPU
# MAGIC   wrapper; the wrapper calls DeepSeek directly with `ChatDeepSeek`.
# MAGIC - The DeepSeek API key is never logged in the model. Model Serving injects
# MAGIC   it from `{{secrets/API_KEY/DEEPSEEK_API_KEY}}` at runtime.
# MAGIC - A `Small` endpoint with scale-to-zero still incurs Databricks Model
# MAGIC   Serving compute charges while active and has cold-start latency.
# MAGIC - The final test performs two user turns. Each prompt explicitly asks for
# MAGIC   a tool call, streams the endpoint response, sends the tool result back,
# MAGIC   and asserts both the call and a final answer. DeepSeek V4 thinking mode
# MAGIC   rejects the `tool_choice` parameter, so the test must not force it at the
# MAGIC   protocol level. This still exercises the exact `reasoning_content`
# MAGIC   round-trip that produces a 400 error when an adapter drops it.
# MAGIC
# MAGIC Current references (reviewed 2026-07-15):
# MAGIC
# MAGIC - [Deploy custom Python code](https://docs.databricks.com/aws/en/machine-learning/model-serving/deploy-custom-python-code)
# MAGIC - [Configure secret environment variables](https://docs.databricks.com/aws/en/machine-learning/model-serving/store-env-variable-model-serving)
# MAGIC - [Query a deployed ResponsesAgent](https://docs.databricks.com/aws/en/agents/agent-framework/query-agent)
# MAGIC - [MLflow ResponsesAgent](https://mlflow.org/docs/latest/genai/serving/responses-agent/)
# MAGIC - [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html)
# MAGIC - [DeepSeek V4 thinking mode](https://api-docs.deepseek.com/guides/thinking_mode)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Install the current, pinned lab dependencies
# MAGIC
# MAGIC `langchain-deepseek==1.1.0` is the provider-specific integration inside
# MAGIC the endpoint. `databricks-langchain==0.20.0` supplies the caller-side
# MAGIC `ChatDatabricks(use_responses_api=True)` adapter.

# COMMAND ----------

# MAGIC %pip install "mlflow[databricks]==3.14.0" "langchain==1.3.13" "langchain-deepseek==1.1.0" "databricks-langchain==0.20.0" "databricks-sdk==0.120.0" "pydantic==2.13.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configure the experiment
# MAGIC
# MAGIC Prerequisites:
# MAGIC
# MAGIC 1. Use a Unity Catalog-enabled workspace and a notebook identity that can
# MAGIC    create a UC model and create/update a serving endpoint.
# MAGIC 2. Create secret scope `API_KEY`, key `DEEPSEEK_API_KEY`, and grant the
# MAGIC    endpoint creator `READ` on that secret.
# MAGIC 3. Use a dedicated experiment endpoint name. Updating an existing endpoint
# MAGIC    replaces its served-entity list with this lab model.
# MAGIC 4. Set `deploy_endpoint` to `true` only after checking cost and the endpoint
# MAGIC    name. The endpoint is not free even though DeepSeek is external.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace", "UC catalog")
dbutils.widgets.text("schema", "gold_layer", "UC schema")
dbutils.widgets.text(
    "registered_model_basename",
    "deepseek_v4_streaming_agent",
    "Registered model basename",
)
dbutils.widgets.text(
    "endpoint_name",
    "deepseek-v4-streaming-agent-lab",
    "Serving endpoint name",
)
dbutils.widgets.text("deepseek_model", "deepseek-v4-flash", "DeepSeek model")
dbutils.widgets.dropdown("deploy_endpoint", "false", ["false", "true"], "Deploy endpoint")

# COMMAND ----------

import json
import os
from datetime import timedelta
from pathlib import Path

import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
from langchain.chat_models import init_chat_model
from mlflow.models import ModelSignature
from mlflow.types.responses import (
    RESPONSES_AGENT_INPUT_SCHEMA,
    RESPONSES_AGENT_OUTPUT_SCHEMA,
)
from mlflow.types.schema import AnyType, Array, ColSpec, Schema

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
MODEL_BASENAME = dbutils.widgets.get("registered_model_basename").strip()
endpoint_name = dbutils.widgets.get("endpoint_name").strip()
DEEPSEEK_MODEL = dbutils.widgets.get("deepseek_model").strip()
DEPLOY_ENDPOINT = dbutils.widgets.get("deploy_endpoint") == "true"

SECRET_SCOPE = "API_KEY"
SECRET_KEY = "DEEPSEEK_API_KEY"
DEEPSEEK_SECRET_REFERENCE = "{{secrets/API_KEY/DEEPSEEK_API_KEY}}"

model_name = f"{CATALOG}.{SCHEMA}.{MODEL_BASENAME}"

required_values = {
    "catalog": CATALOG,
    "schema": SCHEMA,
    "registered_model_basename": MODEL_BASENAME,
    "endpoint_name": endpoint_name,
    "deepseek_model": DEEPSEEK_MODEL,
}
missing = [name for name, value in required_values.items() if not value]
assert not missing, f"Empty required widgets: {missing}"
assert CATALOG == "workspace", (
    "This experiment is intentionally pinned to the 'workspace' catalog. "
    "Do not deploy the lab model into another catalog."
)

legacy_model_aliases = {"deepseek-chat", "deepseek-reasoner"}
assert DEEPSEEK_MODEL not in legacy_model_aliases, (
    "Use an explicit DeepSeek V4 model ID. The legacy aliases are scheduled "
    "for retirement on 2026-07-24."
)

print(
    json.dumps(
        {
            "deepseek_model": DEEPSEEK_MODEL,
            "registered_model": model_name,
            "endpoint": endpoint_name,
            "secret_reference": DEEPSEEK_SECRET_REFERENCE,
            "deploy_endpoint": DEPLOY_ENDPOINT,
        },
        indent=2,
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Validate the secret and call DeepSeek directly
# MAGIC
# MAGIC This cell intentionally copies the secret into the driver process only for
# MAGIC the direct smoke test. It prints neither the key nor any reasoning text.
# MAGIC The served model receives the same environment variable from the secret
# MAGIC reference in the endpoint configuration, not from the notebook process.

# COMMAND ----------

deepseek_api_key = dbutils.secrets.get(scope=SECRET_SCOPE, key=SECRET_KEY)
assert deepseek_api_key, "The DeepSeek secret exists but is empty."
os.environ["DEEPSEEK_API_KEY"] = deepseek_api_key
del deepseek_api_key

print("Secret lookup succeeded; value was not printed.")

# COMMAND ----------

direct_model = init_chat_model(
    model=DEEPSEEK_MODEL,
    model_provider="deepseek",
    max_retries=6,
    timeout=120,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

direct_text_parts: list[str] = []
direct_chunk_count = 0
reasoning_metadata_seen = False

for chunk in direct_model.stream(
    "Give three short bullet points explaining why server-sent streaming is useful."
):
    direct_chunk_count += 1
    reasoning_metadata_seen = reasoning_metadata_seen or bool(
        chunk.additional_kwargs.get("reasoning_content")
    )
    if isinstance(chunk.content, str) and chunk.content:
        direct_text_parts.append(chunk.content)
        print(chunk.content, end="", flush=True)

direct_text = "".join(direct_text_parts).strip()
assert direct_chunk_count > 0, "DeepSeek returned no stream chunks."
assert direct_text, "DeepSeek streamed no final answer text."

print(
    "\n\nDirect streaming OK:",
    {
        "chunks": direct_chunk_count,
        "final_text_chars": len(direct_text),
        "reasoning_metadata_seen": reasoning_metadata_seen,
    },
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Package a ResponsesAgent model adapter for ChatDatabricks
# MAGIC
# MAGIC The generated model source is self-contained so this notebook can be
# MAGIC uploaded alone. The model lazily initializes the provider-specific
# MAGIC LangChain DeepSeek client after Model Serving injects the secret. It also:
# MAGIC
# MAGIC - forwards Responses API tool schemas into `ChatDeepSeek.bind_tools`;
# MAGIC - emits DeepSeek reasoning as a Responses reasoning item;
# MAGIC - reconstructs that item as `reasoning_content` on the next DeepSeek call;
# MAGIC - streams visible answer text without printing reasoning text.
# MAGIC
# MAGIC MLflow 3.14's standard `ResponsesAgent` signature describes each runtime
# MAGIC tool only as `{type: string}` even though the Pydantic `Tool` accepts the
# MAGIC function fields `name`, `description`, and `parameters`. Model Serving
# MAGIC enforces the serialized signature before invoking Python, so a
# MAGIC `ChatDatabricks.bind_tools(...)` request otherwise fails with HTTP 400.
# MAGIC After logging, this notebook widens only the `tools` column to
# MAGIC `Array(Any)`; request validation inside `ResponsesAgentRequest` remains the
# MAGIC source of truth for the actual tool payload.

# COMMAND ----------

agent_source = r'''
import json
from typing import Generator
from uuid import uuid4

from langchain.chat_models import init_chat_model
from mlflow.models import set_model
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)


def _content_as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    text_parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in {"text", "output_text"} and isinstance(
            block.get("text"), str
        ):
            text_parts.append(block["text"])
    return "".join(text_parts)


def _summary_as_text(summary: object) -> str:
    if not isinstance(summary, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in summary
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def _responses_input_to_deepseek_messages(items: list[object]) -> list[dict]:
    """Rebuild Chat Completions messages without losing DeepSeek reasoning."""
    messages: list[dict] = []
    pending_reasoning_parts: list[str] = []
    pending_tool_calls: dict[str, dict] = {}

    def flush_pending_tool_calls() -> None:
        if not pending_tool_calls:
            return
        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": list(pending_tool_calls.values()),
        }
        reasoning_content = "".join(pending_reasoning_parts)
        if reasoning_content:
            assistant_message["reasoning_content"] = reasoning_content
        messages.append(assistant_message)
        pending_reasoning_parts.clear()
        pending_tool_calls.clear()

    for item in items:
        data = item.model_dump(exclude_none=True) if hasattr(item, "model_dump") else dict(item)
        item_type = data.get("type")

        if item_type == "reasoning":
            reasoning_text = _summary_as_text(data.get("summary"))
            if reasoning_text:
                pending_reasoning_parts.append(reasoning_text)
            continue

        if item_type == "function_call":
            call_id = data["call_id"]
            pending_tool_calls[call_id] = {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": data["name"],
                    "arguments": data.get("arguments") or "{}",
                },
            }
            continue

        if item_type == "function_call_output":
            flush_pending_tool_calls()
            output = data.get("output", "")
            if not isinstance(output, str):
                output = json.dumps(output)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": data["call_id"],
                    "content": output,
                }
            )
            continue

        if item_type == "message":
            flush_pending_tool_calls()
            role = data["role"]
            message = {"role": role, "content": _content_as_text(data.get("content"))}
            if role == "assistant" and pending_reasoning_parts:
                message["reasoning_content"] = "".join(pending_reasoning_parts)
                pending_reasoning_parts.clear()
            messages.append(message)

    flush_pending_tool_calls()
    return messages


def _responses_tools_to_openai_tools(tools: list[object] | None) -> list[dict]:
    converted: list[dict] = []
    for tool in tools or []:
        data = tool.model_dump(exclude_none=True) if hasattr(tool, "model_dump") else dict(tool)
        if data.get("type") != "function":
            raise ValueError(f"Unsupported tool type: {data.get('type')!r}")
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "parameters": data.get("parameters", {"type": "object"}),
                },
            }
        )
    return converted


class DeepSeekStreamingAgent(ResponsesAgent):
    def __init__(self) -> None:
        self._chat_model = None

    def _get_chat_model(self):
        if self._chat_model is None:
            self._chat_model = init_chat_model(
                model=__DEEPSEEK_MODEL__,
                model_provider="deepseek",
                max_retries=6,
                timeout=120,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
            )
        return self._chat_model

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        output = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(
            output=output,
            custom_outputs=request.custom_inputs,
        )

    def predict_stream(
        self,
        request: ResponsesAgentRequest,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = _responses_input_to_deepseek_messages(request.input)
        tools = _responses_tools_to_openai_tools(request.tools)
        chat_model = self._get_chat_model()
        if tools:
            tool_choice = request.tool_choice
            if hasattr(tool_choice, "model_dump"):
                tool_choice = tool_choice.model_dump(exclude_none=True)
            if tool_choice is not None:
                raise ValueError(
                    "DeepSeek V4 thinking mode rejects the tool_choice parameter. "
                    "Bind tools without tool_choice and state the tool requirement "
                    "in the prompt."
                )
            bind_options = {}
            if request.parallel_tool_calls is not None:
                bind_options["parallel_tool_calls"] = request.parallel_tool_calls
            chat_model = chat_model.bind_tools(tools, **bind_options)

        item_id = f"msg_{uuid4().hex}"
        reasoning_id = f"rs_{uuid4().hex}"
        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        reasoning_emitted = False
        full_chunk = None

        for chunk in chat_model.stream(messages):
            full_chunk = chunk if full_chunk is None else full_chunk + chunk
            reasoning_text = chunk.additional_kwargs.get("reasoning_content")
            if isinstance(reasoning_text, str) and reasoning_text:
                reasoning_parts.append(reasoning_text)

            text = _content_as_text(chunk.content)
            if not text:
                continue
            if reasoning_parts and not reasoning_emitted:
                yield ResponsesAgentStreamEvent(
                    type="response.output_item.done",
                    item=self.create_reasoning_item(
                        id=reasoning_id,
                        reasoning_text="".join(reasoning_parts),
                    ),
                )
                reasoning_emitted = True
            text_parts.append(text)
            yield ResponsesAgentStreamEvent(
                **self.create_text_delta(delta=text, item_id=item_id)
            )

        if full_chunk is None:
            raise RuntimeError("DeepSeek returned no stream chunks.")

        if reasoning_parts and not reasoning_emitted:
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_reasoning_item(
                    id=reasoning_id,
                    reasoning_text="".join(reasoning_parts),
                ),
            )

        final_text = "".join(text_parts)
        if final_text:
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_text_output_item(text=final_text, id=item_id),
            )

        for tool_call in full_chunk.tool_calls:
            call_id = tool_call.get("id") or f"call_{uuid4().hex}"
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_function_call_item(
                    id=f"fc_{call_id}"[:64],
                    call_id=call_id,
                    name=tool_call["name"],
                    arguments=json.dumps(tool_call["args"]),
                ),
            )

        if not final_text and not full_chunk.tool_calls:
            raise RuntimeError("DeepSeek returned neither answer text nor tool calls.")


set_model(DeepSeekStreamingAgent())
'''.replace("__DEEPSEEK_MODEL__", repr(DEEPSEEK_MODEL))

agent_source_path = Path("/tmp/deepseek_responses_agent.py")
agent_source_path.write_text(agent_source, encoding="utf-8")
print(f"Generated model source: {agent_source_path}")

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")


def responses_agent_signature_with_runtime_tools() -> ModelSignature:
    """Keep the standard ResponsesAgent contract but allow full runtime tools."""
    inputs = Schema(
        [
            ColSpec(Array(AnyType()), name="tools", required=False)
            if column.name == "tools"
            else column
            for column in RESPONSES_AGENT_INPUT_SCHEMA.inputs
        ]
    )
    return ModelSignature(inputs=inputs, outputs=RESPONSES_AGENT_OUTPUT_SCHEMA)

input_example = {
    "input": [
        {
            "role": "user",
            "content": "Explain streaming in three short bullet points.",
        }
    ]
}

with mlflow.start_run(run_name="deepseek-v4-responses-streaming-lab"):
    logged_model = mlflow.pyfunc.log_model(
        name="deepseek_responses_agent",
        python_model=str(agent_source_path),
        input_example=input_example,
        pip_requirements=[
            "mlflow==3.14.0",
            "langchain==1.3.13",
            "langchain-deepseek==1.1.0",
            "pydantic==2.13.4",
        ],
    )

mlflow.models.set_signature(
    logged_model.model_uri,
    responses_agent_signature_with_runtime_tools(),
)
model_info = mlflow.models.get_model_info(logged_model.model_uri)
assert model_info.signature is not None, "MLflow did not record a model signature."
tools_column = next(
    column for column in model_info.signature.inputs.inputs if column.name == "tools"
)
assert str(tools_column.type) == "Array(Any)", tools_column
print("MLflow ResponsesAgent signature:", model_info.signature)

registered_model = mlflow.register_model(
    model_uri=logged_model.model_uri,
    name=model_name,
    await_registration_for=600,
)
model_version = str(registered_model.version)

print(
    json.dumps(
        {
            "model_uri": logged_model.model_uri,
            "registered_model": model_name,
            "model_version": model_version,
        },
        indent=2,
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create or update the dedicated serving endpoint
# MAGIC
# MAGIC This is the cost-incurring step. Set the `deploy_endpoint` widget to
# MAGIC `true` and rerun from the configuration cell. For an existing endpoint,
# MAGIC the required `update_config` call replaces its served-entity list.
# MAGIC
# MAGIC Model image builds commonly take longer than five minutes. `create()` and
# MAGIC `update_config()` return SDK waiters; submitting the request is not proof
# MAGIC that the endpoint is queryable. This cell waits up to 30 minutes, reports
# MAGIC status transitions, and verifies that the secret reference is present in
# MAGIC the active served-entity configuration before the ChatDatabricks test runs.

# COMMAND ----------

assert DEPLOY_ENDPOINT, (
    "Deployment is disabled. Confirm the dedicated endpoint name and cost, set "
    "the deploy_endpoint widget to true, then rerun the notebook from section 1."
)

w = WorkspaceClient()

served_entity = ServedEntityInput(
    entity_name=model_name,
    entity_version=model_version,
    workload_size="Small",
    scale_to_zero_enabled=True,
    environment_vars={
        "DEEPSEEK_API_KEY": "{{secrets/API_KEY/DEEPSEEK_API_KEY}}",
    },
)


def report_endpoint_status(endpoint) -> None:
    state = endpoint.state
    print(
        "Endpoint status:",
        {
            "ready": str(state.ready),
            "config_update": str(state.config_update),
        },
    )


def wait_after_create_timeout(create_timeout: TimeoutError):
    """Recover when create reached Databricks but the client timed out waiting."""
    try:
        w.serving_endpoints.get(name=endpoint_name)
    except NotFound:
        raise create_timeout

    print(
        "The create call timed out, but the endpoint now exists. "
        "Continuing with server-side readiness polling."
    )
    return w.serving_endpoints.wait_get_serving_endpoint_not_updating(
        name=endpoint_name,
        timeout=timedelta(minutes=30),
        callback=report_endpoint_status,
    )


try:
    existing_endpoint = w.serving_endpoints.get(name=endpoint_name)
except NotFound:
    print(f"Creating endpoint {endpoint_name!r}.")
    try:
        endpoint = w.serving_endpoints.create(
            name=endpoint_name,
            config=EndpointCoreConfigInput(
                name=endpoint_name,
                served_entities=[served_entity],
            ),
        ).result(
            timeout=timedelta(minutes=30),
            callback=report_endpoint_status,
        )
    except TimeoutError as create_timeout:
        endpoint = wait_after_create_timeout(create_timeout)
else:
    if not str(existing_endpoint.state.config_update).endswith("NOT_UPDATING"):
        print(
            f"Endpoint {endpoint_name!r} already has an update in progress; "
            "waiting before submitting this model version."
        )
        w.serving_endpoints.wait_get_serving_endpoint_not_updating(
            name=endpoint_name,
            timeout=timedelta(minutes=30),
            callback=report_endpoint_status,
        )
    print(f"Updating endpoint {endpoint_name!r}.")
    endpoint = w.serving_endpoints.update_config(
        name=endpoint_name,
        served_entities=[served_entity],
    ).result(
        timeout=timedelta(minutes=30),
        callback=report_endpoint_status,
    )

assert str(endpoint.state.ready).endswith("READY"), endpoint.state
assert str(endpoint.state.config_update).endswith("NOT_UPDATING"), endpoint.state

active_entity = next(
    entity
    for entity in endpoint.config.served_entities
    if entity.entity_name == model_name and str(entity.entity_version) == model_version
)
assert "DEEPSEEK_API_KEY" in (active_entity.environment_vars or {}), (
    "The active served entity has no DEEPSEEK_API_KEY secret reference. "
    "A model created through the UI must be updated with the notebook config."
)

print(
    "Endpoint is queryable with the expected served entity:",
    {
        "endpoint": endpoint_name,
        "model": model_name,
        "version": model_version,
        "secret_env_present": True,
    },
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Query through ChatDatabricks and verify reasoning round-trip
# MAGIC
# MAGIC `ChatDatabricks(use_responses_api=True)` is the actual model adapter under
# MAGIC test. The code asks for and asserts one tool call on each of two user turns.
# MAGIC It intentionally omits `tool_choice`, which DeepSeek V4 thinking mode
# MAGIC rejects. Each turn therefore requires at least two endpoint/DeepSeek calls:
# MAGIC
# MAGIC `user -> reasoning + tool call -> tool result -> reasoning + final answer`
# MAGIC
# MAGIC A healthy result has all of the following:
# MAGIC
# MAGIC - no HTTP/auth/provider exception, especially no DeepSeek `400` saying
# MAGIC   `reasoning_content` must be passed back;
# MAGIC - both turns contain a tool call and a non-empty final answer;
# MAGIC - the streamed AI message that requested each tool contains a Responses
# MAGIC   `reasoning` block, which `ChatDatabricks` sends back on the next call;
# MAGIC - visible text arrives in multiple stream chunks where the provider emits
# MAGIC   token-sized deltas.
# MAGIC
# MAGIC Several seconds or minutes before the first event can be normal after
# MAGIC scale-to-zero. The test never prints the reasoning text itself.

# COMMAND ----------

from typing import Any

from databricks_langchain import ChatDatabricks
from langchain_core.messages import HumanMessage, ToolMessage, message_chunk_to_message
from langchain_core.tools import tool


@tool
def lookup_order_total(order_id: str) -> dict[str, Any]:
    """Look up the deterministic total and status for a lab order ID."""
    orders = {
        "ORDER-1001": {"total_usd": 125.50, "status": "delivered"},
        "ORDER-1002": {"total_usd": 79.99, "status": "shipped"},
    }
    return orders.get(order_id, {"error": "order_not_found"})


chat_databricks = ChatDatabricks(
    endpoint=endpoint_name,
    use_responses_api=True,
    timeout=180,
    max_retries=3,
    stream_usage=True,
)
tool_model = chat_databricks.bind_tools([lookup_order_total])


def content_block_count(message, block_type: str) -> int:
    if not isinstance(message.content, list):
        return 0
    return sum(
        1
        for block in message.content
        if isinstance(block, dict) and block.get("type") == block_type
    )


def visible_text(message) -> str:
    if isinstance(message.content, str):
        return message.content
    if not isinstance(message.content, list):
        return ""
    return "".join(
        block.get("text", "")
        for block in message.content
        if isinstance(block, dict) and block.get("type") in {"text", "output_text"}
    )


def stream_message(model, history):
    full_chunk = None
    chunk_count = 0
    visible_delta_count = 0

    for chunk in model.stream(history):
        chunk_count += 1
        full_chunk = chunk if full_chunk is None else full_chunk + chunk
        chunk_text = visible_text(chunk)
        if chunk_text:
            visible_delta_count += 1
            print(chunk_text, end="", flush=True)

    assert full_chunk is not None, "ChatDatabricks returned no stream chunks."
    return message_chunk_to_message(full_chunk), chunk_count, visible_delta_count


def run_tool_turn(history: list, question: str) -> dict[str, Any]:
    history.append(HumanMessage(content=question))
    tool_calls = 0
    reasoning_tool_rounds = 0
    total_chunks = 0
    visible_deltas = 0

    for _ in range(6):
        ai_message, chunk_count, delta_count = stream_message(tool_model, history)
        history.append(ai_message)
        total_chunks += chunk_count
        visible_deltas += delta_count

        if ai_message.tool_calls:
            tool_calls += len(ai_message.tool_calls)
            if content_block_count(ai_message, "reasoning") > 0:
                reasoning_tool_rounds += 1

            for tool_call in ai_message.tool_calls:
                tool_result = lookup_order_total.invoke(tool_call["args"])
                history.append(
                    ToolMessage(
                        content=json.dumps(tool_result),
                        tool_call_id=tool_call["id"],
                    )
                )
            continue

        answer = visible_text(ai_message).strip()
        assert answer, "The tool loop ended without a final visible answer."
        assert tool_calls > 0, "DeepSeek did not call the required order tool."
        assert reasoning_tool_rounds > 0, (
            "The tool-call message had no reasoning item to round-trip."
        )
        return {
            "tool_calls": tool_calls,
            "reasoning_tool_rounds": reasoning_tool_rounds,
            "stream_chunks": total_chunks,
            "visible_text_deltas": visible_deltas,
            "final_answer_chars": len(answer),
        }

    raise RuntimeError("DeepSeek exceeded six tool-loop model calls in one user turn.")


conversation: list = []
turn_1 = run_tool_turn(
    conversation,
    "You must use lookup_order_total to tell me the total and status of ORDER-1001.",
)
print("\n")
turn_2 = run_tool_turn(
    conversation,
    "Now use the same tool for ORDER-1002 and compare its total with the previous order.",
)

assert turn_1["visible_text_deltas"] > 0
assert turn_2["visible_text_deltas"] > 0

print(
    "\n\nCHATDATABRICKS STREAMING + REASONING ROUND-TRIP OK:",
    {"turn_1": turn_1, "turn_2": turn_2},
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Interpreting failures
# MAGIC
# MAGIC - `RESOURCE_DOES_NOT_EXIST` for the secret: create scope `API_KEY` and key
# MAGIC   `DEEPSEEK_API_KEY`.
# MAGIC - `PERMISSION_DENIED` during deployment: the recorded endpoint creator
# MAGIC   needs UC grants on the registered model and `READ` on the secret.
# MAGIC - Image build failure mentioning `mlflow-skinny`: confirm the logged model
# MAGIC   has the explicit `mlflow==3.14.0` pip requirement.
# MAGIC - `429`: DeepSeek quota/rate limiting; the model retries six times, but an
# MAGIC   exhausted retry is a provider-capacity failure, not a successful stream.
# MAGIC - `400` mentioning `reasoning_content`: the experiment has reproduced the
# MAGIC   adapter failure. Inspect the last tool-call AI message and confirm that it
# MAGIC   contains a `reasoning` content block before the tool result is appended.
# MAGIC - `400` saying thinking mode does not support `tool_choice`: bind tools
# MAGIC   without `required`, `auto`, or a named choice. DeepSeek V4 thinking mode
# MAGIC   decides tool use from the prompt and tool descriptions.
# MAGIC - `400` saying tool properties `name`, `description`, or `parameters` are
# MAGIC   not defined in the schema: the deployed model predates the
# MAGIC   `Array(Any)` runtime-tools signature; log and deploy a new model version.
# MAGIC - Tool call succeeds but `reasoning_tool_rounds == 0`: streaming works, but
# MAGIC   the route has not preserved DeepSeek's thinking payload and is unsafe for
# MAGIC   the intended thinking-mode agent loop.
# MAGIC - Final answers arrive with `visible_text_deltas == 1`: functionally valid,
# MAGIC   but the provider or endpoint buffered the visible text into one chunk.
