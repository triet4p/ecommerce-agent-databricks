"""
apps.chat_ui.app
-------------------
Databricks App for the Streamlit chat UI. Calls the main agent App through
Databricks OAuth (``WorkspaceClient().config.authenticate()``) with a streaming
SSE request and renders text, tool calls, phase labels, and errors in
real-time.

The target App URL is set via the ``AGENT_APP_URL`` environment variable
(configured in the App's resource definition in ``databricks.yml``).
"""

from __future__ import annotations

import logging

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient

from app_oauth import resolve_agent_app_url
from display_policy import derive_phase_label, sanitize_output, tool_display_name
from sse_parser import JSONEventParser
from stream_types import (
    ErrorEvent,
    OutputItemDoneEvent,
    TextDeltaEvent,
    parse_stream_event,
)

logger = logging.getLogger(__name__)

AGENT_REQUEST_TIMEOUT_SECONDS = 180

st.title("E-commerce support agent")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tool_stream_state" not in st.session_state:
    # Tracks tool call_id -> display_name for status-card correlation
    st.session_state.tool_stream_state: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Render existing messages from prior turns
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ---------------------------------------------------------------------------
# Handle user input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask about orders, policies..."):
    # Append and render user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Prepare assistant area — create placeholders before streaming starts
    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        tool_placeholder = st.empty()
        phase_placeholder = st.empty()

    accumulated_text = ""
    tool_state: dict[str, str] = {}  # call_id -> display_name
    event_has_text = False
    event_has_pending_tool = False
    event_has_tool_result = False
    event_multi_step = False
    received_error = False

    # Resolve agent app URL and get OAuth headers
    w = WorkspaceClient()
    agent_app_url = resolve_agent_app_url(w)
    headers = w.config.authenticate()

    try:
        with requests.post(
            f"{agent_app_url}/api/responses",
            headers=headers,
            json={
                "input": [{"role": "user", "content": prompt}],
                "stream": True,
            },
            stream=True,
            timeout=AGENT_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()

            parser = JSONEventParser()
            stream_done = False

            for raw_chunk in response.iter_content(chunk_size=None):
                if stream_done:
                    break
                for parsed in parser.feed(raw_chunk):
                    if parsed == "[DONE]":
                        stream_done = True
                        break

                    if not isinstance(parsed, dict):
                        continue

                    event = parse_stream_event(parsed)
                    if event is None:
                        continue

                    # --- Text delta ---
                    if isinstance(event, TextDeltaEvent):
                        accumulated_text += event.delta
                        text_placeholder.markdown(f"{accumulated_text}✔\n\n▌")
                        event_has_text = True

                    # --- Output item done ---
                    elif isinstance(event, OutputItemDoneEvent):
                        item = event.item

                        if item.type == "message":
                            if item.text:
                                accumulated_text = item.text
                                text_placeholder.markdown(item.text)

                        elif item.type == "function_call":
                            call_id = item.call_id
                            label = tool_display_name(item.name)
                            tool_state[call_id] = item.name
                            event_has_pending_tool = True

                            with tool_placeholder.container():
                                st.status(
                                    f"\U0001f527 {label}",
                                    state="running",
                                )

                        elif item.type == "function_call_output":
                            call_id = item.call_id
                            event_has_tool_result = True
                            tool_name = tool_state.get(call_id, "Unknown tool")
                            label = tool_display_name(tool_name)
                            truncated = sanitize_output(item.output)

                            with tool_placeholder.container():
                                st.status(
                                    f"✅ {label}",
                                    state="complete",
                                )

                    # --- Error event ---
                    elif isinstance(event, ErrorEvent):
                        received_error = True
                        text_placeholder.error(
                            f"❌ {event.message or 'An error occurred'}"
                        )
                        stream_done = True
                        break

            # --- Post-stream UI update ---
            if not received_error:
                if tool_state:
                    with tool_placeholder.container():
                        for call_id, name in tool_state.items():
                            label = tool_display_name(name)
                            st.status(f"✅ {label}", state="complete")

            phase = derive_phase_label(
                has_text_delta=event_has_text,
                has_pending_tool_call=event_has_pending_tool,
                has_tool_result=event_has_tool_result,
                is_multi_step=event_multi_step,
                is_error=received_error,
            )
            phase_placeholder.caption(phase)

    except requests.exceptions.Timeout:
        logger.warning(
            "Streaming request timed out after %ss", AGENT_REQUEST_TIMEOUT_SECONDS
        )
        text_placeholder.error(
            "⏰ Request timed out after "
            f"{AGENT_REQUEST_TIMEOUT_SECONDS} seconds. "
            "Please try again."
        )
        received_error = True

    except requests.exceptions.RequestException as exc:
        logger.warning("Streaming request failed: %s", exc)
        text_placeholder.error(f"❌ Connection error: {exc}")
        received_error = True

    # Retry button on error
    if received_error:
        if st.button("\U0001f504 Retry", key=f"retry_{len(st.session_state.messages)}"):
            # Re-run by clearing placeholder state — Streamlit re-runs on widget
            # interaction, so the button click alone triggers a re-run that will
            # re-prompt the user.
            st.rerun()

    # Save the final assistant message only if we got meaningful content
    if accumulated_text and not received_error:
        st.session_state.messages.append(
            {"role": "assistant", "content": accumulated_text}
        )

    # Reset per-turn tool state
    st.session_state.tool_stream_state = {}
