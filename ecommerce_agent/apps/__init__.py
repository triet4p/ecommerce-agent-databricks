"""ecommerce_agent.apps — deployable application implementations.

Target layout (Sprint 5):
  apps/agent_app/          FastAPI Agent (ResponsesAgent runtime)
  apps/mcp_facade/         Streamable HTTP MCP facade
  apps/chat_ui/            React chat UI (default)
  apps/streamlit_chat_ui/  Streamlit chat UI (demo fallback)

All apps share ecommerce_agent.conversation as their canonical persistence
layer; no app may duplicate it.
"""
