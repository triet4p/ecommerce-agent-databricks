"""
apps.chat_ui.app
-------------------
Databricks App tối giản (Streamlit) — UI cho end-user, gọi thẳng `agent_app` (agent giờ
host trực tiếp trên Databricks Apps, không qua Model Serving nữa — xem
`agent_app/server.py`). KHÔNG chứa logic agent — chỉ query endpoint, đúng nguyên tắc
Thin Core/Fat Module.

NOTE (đã rà lại 2026-07, đổi theo current state): App gọi 1 App khác chưa được liệt kê
là resource dependency hỗ trợ sẵn trong databricks.yml (phải tự quản lý quyền + OAuth
token) — code dưới dùng `WorkspaceClient().config.authenticate()` để lấy header OAuth
tiêu chuẩn của Databricks SDK. Cách lấy token/header chính xác nhất nên verify lại với
tài liệu `Author an AI agent and deploy it on Databricks Apps` tại thời điểm deploy,
vì đây là phần docs công khai mô tả bằng ví dụ curl (Bearer token) chứ chưa có snippet
Python SDK đầy đủ cho trường hợp App-gọi-App.
"""

import os

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient

AGENT_APP_URL = os.environ["AGENT_APP_URL"]  # set qua app.yaml resources, vd https://<agent-app>.databricksapps.com

st.title("E-commerce support agent")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Hỏi về đơn hàng, chính sách..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    w = WorkspaceClient()
    headers = w.config.authenticate()  # OAuth header chuẩn của SDK — verify lại theo docs khi deploy thật
    response = requests.post(
        f"{AGENT_APP_URL}/responses",
        headers=headers,
        json={"input": [{"role": "user", "content": prompt}], "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    answer = response.json()["output"][0]["content"][0]["text"]

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)
