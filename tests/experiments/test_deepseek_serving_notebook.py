from pathlib import Path
import unittest


NOTEBOOK = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "DeepSeekServingEndpointStreaming.py"
)


class DeepSeekServingNotebookContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = NOTEBOOK.read_text(encoding="utf-8")

    def test_is_importable_databricks_source_notebook(self) -> None:
        self.assertTrue(self.source.startswith("# Databricks notebook source\n"))
        compile(self.source, str(NOTEBOOK), "exec")

    def test_embedded_model_source_compiles(self) -> None:
        marker = "agent_source = r'''\n"
        start = self.source.index(marker) + len(marker)
        end = self.source.index("\n'''.replace", start)
        agent_source = self.source[start:end].replace(
            "__DEEPSEEK_MODEL__", repr("deepseek-v4-flash")
        )
        compile(agent_source, "deepseek_responses_agent.py", "exec")

    def test_embedded_adapter_reconstructs_deepseek_reasoning(self) -> None:
        from mlflow.types.responses import ResponsesAgentRequest

        marker = "agent_source = r'''\n"
        start = self.source.index(marker) + len(marker)
        end = self.source.index("\n'''.replace", start)
        agent_source = self.source[start:end].replace(
            "__DEEPSEEK_MODEL__", repr("deepseek-v4-flash")
        )
        agent_source = agent_source.rsplit("\nset_model(DeepSeekStreamingAgent())", 1)[0]
        namespace: dict = {}
        exec(compile(agent_source, "deepseek_responses_agent.py", "exec"), namespace)

        request = ResponsesAgentRequest(
            input=[
                {
                    "type": "reasoning",
                    "id": "rs_tool",
                    "summary": [{"type": "summary_text", "text": "tool reasoning"}],
                },
                {
                    "type": "function_call",
                    "id": "fc_call_1",
                    "call_id": "call_1",
                    "name": "lookup_order_total",
                    "arguments": '{"order_id":"ORDER-1001"}',
                },
                {
                    "type": "function_call_output",
                    "call_id": "call_1",
                    "output": '{"total_usd":125.5}',
                },
                {
                    "type": "reasoning",
                    "id": "rs_final",
                    "summary": [{"type": "summary_text", "text": "final reasoning"}],
                },
                {"role": "assistant", "content": "The total is 125.50 USD."},
                {"role": "user", "content": "Check the next order."},
            ],
            tools=[
                {
                    "type": "function",
                    "name": "lookup_order_total",
                    "description": "Look up an order total.",
                    "parameters": {
                        "type": "object",
                        "properties": {"order_id": {"type": "string"}},
                        "required": ["order_id"],
                    },
                }
            ],
        )

        messages = namespace["_responses_input_to_deepseek_messages"](request.input)
        self.assertEqual(messages[0]["reasoning_content"], "tool reasoning")
        self.assertEqual(messages[0]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(messages[1]["role"], "tool")
        self.assertEqual(messages[2]["reasoning_content"], "final reasoning")
        self.assertEqual(messages[3], {"role": "user", "content": "Check the next order."})

        tools = namespace["_responses_tools_to_openai_tools"](request.tools)
        self.assertEqual(tools[0]["function"]["name"], "lookup_order_total")

    def test_uses_current_pinned_apis(self) -> None:
        required_fragments = (
            '"langchain==1.3.13"',
            '"langchain-deepseek==1.1.0"',
            '"databricks-langchain==0.20.0"',
            '"databricks-sdk==0.120.0"',
            'model_provider="deepseek"',
            "class DeepSeekStreamingAgent(ResponsesAgent)",
            "w.serving_endpoints.update_config(",
            "ServedEntityInput(",
            "from databricks_langchain import ChatDatabricks",
            "use_responses_api=True",
            "chat_databricks.bind_tools(",
            "request.tools",
            "self.create_reasoning_item(",
            'message["reasoning_content"]',
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)

    def test_secret_is_referenced_without_literal_api_key(self) -> None:
        self.assertIn(
            '"DEEPSEEK_API_KEY": "{{secrets/API_KEY/DEEPSEEK_API_KEY}}"',
            self.source,
        )
        self.assertNotIn("sk-", self.source)

    def test_rejects_retiring_deepseek_aliases(self) -> None:
        self.assertIn(
            'legacy_model_aliases = {"deepseek-chat", "deepseek-reasoner"}',
            self.source,
        )
        self.assertIn('"deepseek-v4-flash"', self.source)

    def test_stream_success_contract_is_executable(self) -> None:
        required_fragments = (
            "turn_1 = run_tool_turn(",
            "turn_2 = run_tool_turn(",
            'assert reasoning_tool_rounds > 0',
            'assert turn_1["visible_text_deltas"] > 0',
            'assert turn_2["visible_text_deltas"] > 0',
            "CHATDATABRICKS STREAMING + REASONING ROUND-TRIP OK",
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)

    def test_does_not_bypass_chatdatabricks_in_final_test(self) -> None:
        self.assertNotIn("DatabricksOpenAI", self.source)


if __name__ == "__main__":
    unittest.main()
