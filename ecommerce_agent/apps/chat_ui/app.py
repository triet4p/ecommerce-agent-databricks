"""
apps.chat_ui.app
-------------------
Databricks App for the Streamlit chat UI with durable conversation history.
Calls the main agent App through Databricks OAuth with a streaming SSE
request and renders text, tool calls, phase labels, and errors in real-time.

Sprint 3 adds Lakebase-backed persistence on top of the Sprint 2 rendering.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient

from app_oauth import resolve_agent_app_url
from conversation.connection import create_pool
from conversation.schema import migrate
from conversation.service import ConversationService
from display_policy import derive_phase_label, sanitize_output, tool_display_name
from sse_parser import JSONEventParser
from stream_types import (
    ErrorEvent,
    OutputItemDoneEvent,
    TextDeltaEvent,
    parse_stream_event,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    _h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(_h)

AGENT_REQUEST_TIMEOUT_SECONDS = 180

st.title("E-commerce support agent")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tool_stream_state" not in st.session_state:
    st.session_state.tool_stream_state: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Persistent background event loop for async DB operations
# ---------------------------------------------------------------------------
if "bg_loop" not in st.session_state:
    _bg_loop = asyncio.new_event_loop()
    _bg_thread = threading.Thread(target=_bg_loop.run_forever, daemon=True)
    _bg_thread.start()
    st.session_state.bg_loop = _bg_loop

# ---------------------------------------------------------------------------
# Conversation service (persistence layer)
# ---------------------------------------------------------------------------
if "conversation_service" not in st.session_state:
    svc = None
    try:
        pool = create_pool()
        # Use the persistent background loop so pool ops work with _run_async
        bg: asyncio.AbstractEventLoop = st.session_state.bg_loop
        asyncio.run_coroutine_threadsafe(pool.open(), bg).result()
        asyncio.run_coroutine_threadsafe(migrate(pool), bg).result()
        svc = ConversationService(pool)
        logger.info("Lakebase connected")
    except Exception as exc:
        logger.warning("Lakebase unavailable: %s", exc)
    st.session_state.conversation_service = svc

if "current_conv_id" not in st.session_state:
    st.session_state.current_conv_id = None

if "current_turn_id" not in st.session_state:
    st.session_state.current_turn_id = None

# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine on the persistent background loop."""
    loop: asyncio.AbstractEventLoop = st.session_state.bg_loop
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


def _get_or_create_conv(svc: ConversationService | None, user: str) -> str | None:
    """Return the current conversation ID, creating one if needed."""
    if svc is None:
        logger.info("No service, returning None")
        return None
    if st.session_state.current_conv_id:
        logger.info("Using existing conv: %s", st.session_state.current_conv_id[:8])
        return st.session_state.current_conv_id
    try:
        conv = _run_async(svc.create_conversation(user))
        st.session_state.current_conv_id = str(conv.id)
        logger.info("Created new conv: %s", str(conv.id)[:8])
        return str(conv.id)
    except Exception as exc:
        logger.warning("Failed to create conversation: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Conversations")
    if st.button("➕ New conversation", use_container_width=True):
        logger.info("New conversation button clicked")
        st.session_state.current_conv_id = None
        st.session_state.messages = []
        st.rerun()
    svc = st.session_state.get("conversation_service")
    if svc is None:
        st.caption("⚠️ Lakebase unavailable — session-only mode")
    elif st.session_state.get("current_conv_id"):
        st.caption(f"Active: {st.session_state.current_conv_id[:8]}...")

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
    collected_events: list[dict] = []

    # --- Persistence: resolve service and turn ---
    svc: ConversationService | None = st.session_state.conversation_service
    user = "unknown@unknown"
    conv_id = _get_or_create_conv(svc, user)
    turn_id = None
    if svc and conv_id:
        try:
            turn = _run_async(svc.create_turn(uuid.UUID(conv_id), user, str(uuid.uuid4())))
            turn_id = str(turn.id)
        except Exception as exc:
            logger.warning("Turn creation failed: %s", exc)

    # --- Build replay history or just the new message ---
    input_items = None
    if svc and conv_id:
        try:
            replay = _run_async(svc.build_replay(uuid.UUID(conv_id), user, prompt))
            if replay.within_budget and replay.input_items:
                input_items = replay.input_items
        except Exception:
            pass
    if input_items is None:
        input_items = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]

    logger.info("TURN input_items=%s", json.dumps(input_items, ensure_ascii=False)[:2000])

    # Resolve agent app URL and get OAuth headers
    w = WorkspaceClient()
    agent_app_url = resolve_agent_app_url(w)
    headers = w.config.authenticate()

    try:
        request_body = {"input": input_items, "stream": True}
        resp = requests.post(
            f"{agent_app_url}/api/responses",
            headers=headers,
            json=request_body,
            stream=True,
            timeout=AGENT_REQUEST_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            error_body = resp.text[:2000] if resp.text else "(empty)"
            logger.warning("API %d body=%s input=%s", resp.status_code, error_body, json.dumps(input_items, ensure_ascii=False)[:2000])
            resp.raise_for_status()

        logger.info("STREAM-01: HTTP 200, starting to read chunks...")
        parser = JSONEventParser()
        stream_done = False
        chunk_n = 0

        for raw_chunk in resp.iter_content(chunk_size=None):
            if stream_done:
                break
            chunk_n += 1
            if chunk_n <= 3 or chunk_n % 10 == 0:
                raw_str = raw_chunk.decode('utf-8', errors='replace') if isinstance(raw_chunk, bytes) else str(raw_chunk)
                logger.info("STREAM-CHUNK: #%d size=%d data=%.200s", chunk_n, len(raw_chunk), raw_str.replace('\n','\\n'))
            parsed_events = list(parser.feed(raw_chunk))
            if not parsed_events:
                continue
            for parsed in parsed_events:
                if parsed == "[DONE]":
                    logger.info("STREAM-02: [DONE] after %d chunks, %d events total", chunk_n, len(collected_events))
                    stream_done = True
                    break

                if not isinstance(parsed, dict):
                    continue

                collected_events.append(parsed)
                logger.info("STREAM-EVT: event#%d full=%s", len(collected_events)+1, json.dumps(parsed, ensure_ascii=False)[:500])

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
                            st.status(f"\U0001f527 {label}", state="running")

                    elif item.type == "function_call_output":
                        call_id = item.call_id
                        event_has_tool_result = True
                        tool_name = tool_state.get(call_id, "Unknown tool")
                        label = tool_display_name(tool_name)
                        sanitize_output(item.output)

                        with tool_placeholder.container():
                            st.status(f"✅ {label}", state="complete")

                # --- Error event ---
                elif isinstance(event, ErrorEvent):
                    received_error = True
                    text_placeholder.error(f"❌ {event.message or 'An error occurred'}")
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
        logger.info("STREAM OK: events=%d text=%d chars", len(collected_events), len(accumulated_text))

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

    # --- Persistence: record turn outcome ---
    if svc and turn_id and conv_id and not received_error:
        try:
            _run_async(
                svc.complete_turn(
                    uuid.UUID(turn_id), uuid.UUID(conv_id), user,
                    collected_events, user_message=prompt,
                )
            )
        except Exception as exc:
            logger.warning("Turn persist failed: %s", exc)

    # Retry button on error
    if received_error:
        if st.button("\U0001f504 Retry", key=f"retry_{len(st.session_state.messages)}"):
            st.rerun()

    # Save the final assistant message only if we got meaningful content
    if accumulated_text and not received_error:
        st.session_state.messages.append(
            {"role": "assistant", "content": accumulated_text}
        )

    # Reset per-turn tool state
    st.session_state.tool_stream_state = {}
