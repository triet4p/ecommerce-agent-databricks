"""
agent_app.server
--------------------
Host agent TRỰC TIẾP trên Databricks Apps qua endpoint `/responses` (OpenAI Responses
API schema) — đây là path Databricks hiện khuyến nghị cho use case mới (docs gọi
`agents.deploy()` -> Model Serving là hướng "legacy" cho agent mới, dù vẫn support đầy
đủ). Xem `../driver.py` cho hướng Model Serving cũ (giữ lại, không xoá).

Khác biệt so với hướng cũ: KHÔNG log model qua mlflow.pyfunc + agents.deploy nữa —
`CoreAgent` (agent_core.orchestrator) được build thẳng trong process của app, request
tới thẳng đây, không qua Model Serving.

NOTE: Databricks có sẵn 1 template chính thức (`agent-openai-agents-sdk` trong
databricks/app-templates) với `agent_server` package cung cấp decorator `@invoke`/
`@stream`, chat UI bundle sẵn, và evaluate_agent.py — implementation ở đây tự viết lại
phần cốt lõi (route `/responses` theo đúng contract) bằng FastAPI thuần để không phụ
thuộc nội dung chi tiết của package đó (chưa verify được hết). Nếu muốn bám sát 100%
template chính thức, cân nhắc chạy `databricks apps` generator để lấy template gốc rồi
ghép agent_core vào, thay vì dùng file này.
"""

import json
import time
import uuid

import yaml
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_core.config_schema import AgentConfig
from agent_core.orchestrator import build_agent
from agent_core.tool_interface import register_custom_tool_factory
from agent_core.retriever_interface import Retriever
from projects.ecommerce_support.tools.search_policy_docs_tool import make_search_policy_docs_tool

app = FastAPI()

with open("config.yaml") as f:
    _raw_config = yaml.safe_load(f)
_config = AgentConfig.model_validate(_raw_config)

if _config.retriever is not None:
    _retriever = Retriever(_config.retriever)
    register_custom_tool_factory(
        "search_policy_docs",
        lambda tool_config: make_search_policy_docs_tool(_retriever, tool_config),
    )

AGENT = build_agent(_config)  # build 1 lần lúc app khởi động, dùng lại cho mọi request


class ResponsesRequest(BaseModel):
    input: list[dict]
    stream: bool = False


@app.post("/responses")
def responses(request: ResponsesRequest):
    from mlflow.types.responses import ResponsesAgentRequest

    agent_request = ResponsesAgentRequest(input=request.input)

    if not request.stream:
        result = AGENT.predict(agent_request)
        return result.model_dump()

    def event_stream():
        item_id = str(uuid.uuid4())
        for event in AGENT.predict_stream(agent_request):
            yield f"data: {json.dumps(event.model_dump())}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok", "use_case": _config.use_case, "ts": time.time()}


if __name__ == "__main__":
    # Local dev: uvicorn projects.ecommerce_support.agent_app.server:app --reload
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
