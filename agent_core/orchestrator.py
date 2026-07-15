"""
agent_core.orchestrator
-------------------------
Project-agnostic tool-calling loop, wrapped as an MLflow ResponsesAgent so any Fat
Module can `mlflow.pyfunc.log_model` it directly (Databricks Mosaic AI Agent Framework
convention). Built once from an AgentConfig — Agent Core never imports a project package.
"""

from __future__ import annotations

from typing import Any, Generator
from uuid import uuid4
import mlflow
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)

from agent_core.config_schema import AgentConfig
from agent_core.prompt_registry import resolve_system_prompt
from agent_core.skill_interface import SkillLibrary, build_skill_tools, render_rules
from agent_core.tool_interface import build_tools


def _build_graph(config: AgentConfig):
    llm = init_chat_model(
        model=config.llm.model_name,
        model_provider=config.llm.provider,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
    )
    tools = build_tools(config)

    # Rules: always-loaded, appended once to the system prompt at build time.
    # Base prompt may come from MLflow Prompt Registry (see prompt_registry.py) or inline.
    system_prompt = resolve_system_prompt(config)
    if config.rules is not None and config.rules.paths:
        system_prompt = f"{system_prompt}\n\n{render_rules(config.rules)}"

    # Skills: progressive disclosure — agent decides at runtime whether to load one.
    if config.skills is not None:
        library = SkillLibrary(config.skills)
        tools = tools + build_skill_tools(library)

    return create_agent(model=llm, tools=tools, system_prompt=system_prompt)


class CoreAgent(ResponsesAgent):
    """Wraps the LangGraph react-agent loop behind MLflow's ResponsesAgent contract
    (predict / predict_stream), which is what `agents.deploy` expects."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.graph = _build_graph(config)

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # Build từ predict_stream để 2 method không bao giờ lệch hành vi với nhau.
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(
            id=str(uuid4()),
            output=outputs,
            custom_outputs=request.custom_inputs,
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        cc_msgs = to_chat_completions_input([i.model_dump() for i in request.input])
        thread_id = str(uuid4())

        # stream_mode=["updates"] (thay vì "messages") để lấy được đủ tool-call/
        # tool-result/reasoning items, không chỉ text token delta.
        for _, events in self.graph.stream(
            {"messages": cc_msgs},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=["updates"],
        ):
            for node_data in events.values():
                yield from output_to_responses_items_stream(node_data["messages"])

def build_agent(config: AgentConfig) -> CoreAgent:
    """Single entrypoint every Fat Module's agent.py should call."""
    return CoreAgent(config)
