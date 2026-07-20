"""
apps.chat_ui.app
-------------------
Databricks App for the Streamlit chat UI. Calls the main agent App through
Databricks OAuth (``WorkspaceClient().config.authenticate()``).

The target App URL is set via the ``AGENT_APP_URL`` environment variable
(configured in the App's resource definition in ``databricks.yml``).
"""

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient

from app_oauth import resolve_agent_app_url
from response_output import extract_response_text

AGENT_REQUEST_TIMEOUT_SECONDS = 180

st.title("E-commerce support agent")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask about orders, policies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    w = WorkspaceClient()
    agent_app_url = resolve_agent_app_url(w)
    headers = (
        w.config.authenticate()
    )  # OAuth header — verify against Databricks docs at deploy time
    response = requests.post(
        f"{agent_app_url}/api/responses",
        headers=headers,
        json={"input": [{"role": "user", "content": prompt}], "stream": False},
        # The retriever can spend up to two 60-second attempts warming from
        # scale-to-zero. Keep the outer App-to-App budget above that bound plus
        # model/tool-loop overhead so the bounded retry can actually complete.
        timeout=AGENT_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    answer = extract_response_text(response.json())

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)
