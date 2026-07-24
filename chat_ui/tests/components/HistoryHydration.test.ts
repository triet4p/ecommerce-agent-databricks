import type { ConversationItem } from "@ecommerce-agent/core";
import { describe, expect, test } from "vitest";
import { restoreMessages } from "../../client/src/hooks/useChat";

function item(
	sequence: number,
	itemType: ConversationItem["item_type"],
	payload: Record<string, unknown>,
): ConversationItem {
	return {
		id: `item-${sequence}`,
		conversation_id: "conversation-1",
		turn_id: "turn-1",
		sequence,
		item_type: itemType,
		role:
			itemType === "message"
				? ((payload.role as string | undefined) ?? null)
				: null,
		payload,
		item_key: `${itemType}:${sequence}`,
		mlflow_trace_id: "trace-1",
		created_at: new Date(0).toISOString(),
	};
}

describe("persisted history hydration", () => {
	test("restores messages, tool provenance, and trace ID", () => {
		const messages = restoreMessages([
			item(1, "message", {
				type: "message",
				role: "user",
				content: [{ type: "input_text", text: "Where is my order?" }],
			}),
			item(2, "function_call", {
				type: "function_call",
				id: "fc-1",
				call_id: "call-1",
				name: "get_order_status",
				arguments: '{"order_id":"order-1"}',
			}),
			item(3, "function_call_output", {
				type: "function_call_output",
				call_id: "call-1",
				output: '{"status":"shipped"}',
			}),
			item(4, "message", {
				type: "message",
				role: "assistant",
				content: [{ type: "output_text", text: '{"status":"shipped"}' }],
			}),
			item(5, "message", {
				type: "message",
				role: "assistant",
				content: [{ type: "output_text", text: "It shipped." }],
			}),
		]);

		expect(messages.map(({ role, content }) => ({ role, content }))).toEqual([
			{ role: "user", content: "Where is my order?" },
			{ role: "assistant", content: "It shipped." },
		]);
		const state = messages[1].persistedStreamState;
		expect(state?.traceId).toBe("trace-1");
		expect(state?.completedTools.get("call-1")).toBe("🔍 Order lookup");
		expect(state?.toolDetails.get("call-1")).toMatchObject({
			arguments: '{"order_id":"order-1"}',
			result: '{"status":"shipped"}',
		});
	});
});
