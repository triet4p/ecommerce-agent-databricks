// =============================================================================
// Unit tests for the event reducer and duplicate suppression (S4-E1)
// =============================================================================
// These tests verify the core stream reducer logic without a browser.

import {
	createInitialStreamState,
	reduceStreamEvent,
} from "@ecommerce-agent/core";
import type { ChatUIStreamEvent } from "@ecommerce-agent/core";
import { expect, test } from "@playwright/test";

test.describe("Stream reducer", () => {
	test("initial state has no text and is streaming", () => {
		const state = createInitialStreamState();
		expect(state.text).toBe("");
		expect(state.isStreaming).toBe(true);
		expect(state.hasError).toBe(false);
		expect(state.isComplete).toBe(false);
	});

	test("idle state is not streaming", () => {
		const state = createInitialStreamState(false);
		expect(state.text).toBe("");
		expect(state.isStreaming).toBe(false);
		expect(state.hasError).toBe(false);
		expect(state.isComplete).toBe(false);
	});

	test("text delta appends content", () => {
		let state = createInitialStreamState();

		state = reduceStreamEvent(state, {
			type: "response.output_text.delta",
			item_id: "msg_1",
			delta: "Hello",
			content_index: 0,
			output_index: 0,
		});

		expect(state.text).toBe("Hello");

		state = reduceStreamEvent(state, {
			type: "response.output_text.delta",
			item_id: "msg_1",
			delta: " world",
			content_index: 0,
			output_index: 0,
		});

		expect(state.text).toBe("Hello world");
	});

	test("completion event marks stream as complete", () => {
		let state = createInitialStreamState();

		state = reduceStreamEvent(state, {
			type: "response.output_text.delta",
			item_id: "msg_1",
			delta: "Done",
			content_index: 0,
			output_index: 0,
		});
		expect(state.phaseLabel).toBe("🤖 Composing…");

		state = reduceStreamEvent(state, {
			type: "response.completed",
			response: { id: "resp_1", status: "completed", output: [] },
		});

		expect(state.isComplete).toBe(true);
		expect(state.isStreaming).toBe(false);
		expect(state.hasError).toBe(false);
		expect(state.phaseLabel).toBe("");
	});

	test("error event marks stream as errored", () => {
		let state = createInitialStreamState();

		state = reduceStreamEvent(state, {
			type: "error",
			code: "INTERNAL_ERROR",
			message: "Something went wrong",
		});

		expect(state.hasError).toBe(true);
		expect(state.errorMessage).toBe("Something went wrong");
		expect(state.isStreaming).toBe(false);
	});

	test("function_call adds pending tool", () => {
		let state = createInitialStreamState();

		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "function_call",
				id: "fc_1",
				call_id: "call_1",
				name: "get_order_status",
				arguments: '{"order_id": "o-123"}',
			},
			output_index: 0,
		});

		expect(state.pendingTools.size).toBe(1);
		expect(state.pendingTools.get("call_1")).toBe("🔍 Order lookup");
		expect(state.completedTools.size).toBe(0);
	});

	test("function_call_output moves pending to completed", () => {
		let state = createInitialStreamState();

		// First: function call
		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "function_call",
				id: "fc_1",
				call_id: "call_1",
				name: "get_order_status",
				arguments: '{"order_id": "o-123"}',
			},
			output_index: 0,
		});

		// Then: function call output
		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "function_call_output",
				call_id: "call_1",
				output: '{"status": "shipped"}',
			},
			output_index: 1,
		});

		expect(state.pendingTools.size).toBe(0);
		expect(state.completedTools.size).toBe(1);
		expect(state.completedTools.get("call_1")).toBe("🔍 Order lookup");
	});

	test("multiple tool calls render as multi-step", () => {
		let state = createInitialStreamState();

		// Two concurrent function calls
		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "function_call",
				id: "fc_1",
				call_id: "call_1",
				name: "get_order_status",
				arguments: "{}",
			},
			output_index: 0,
		});

		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "function_call",
				id: "fc_2",
				call_id: "call_2",
				name: "get_customer_order_history",
				arguments: "{}",
			},
			output_index: 1,
		});

		expect(state.pendingTools.size).toBe(2);
		expect(state.phaseLabel).toBe("🔄 Multi-step…");
	});

	test("unknown tool name gets generic label", () => {
		let state = createInitialStreamState();

		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "function_call",
				id: "fc_1",
				call_id: "call_1",
				name: "custom_unregistered_tool",
				arguments: "{}",
			},
			output_index: 0,
		});

		expect(state.pendingTools.get("call_1")).toBe(
			"🔧 custom_unregistered_tool",
		);
	});

	test("message output item sets text", () => {
		let state = createInitialStreamState();

		state = reduceStreamEvent(state, {
			type: "response.output_item.done",
			item: {
				type: "message",
				id: "msg_1",
				role: "assistant",
				content: [
					{ type: "output_text", text: "Final answer", annotations: [] },
				],
			},
			output_index: 0,
		});

		expect(state.text).toBe("Final answer");
	});

	test("duplicate tool events do not duplicate correlated state", () => {
		const call = {
			type: "response.output_item.done" as const,
			item: {
				type: "function_call" as const,
				id: "fc_duplicate",
				call_id: "call_duplicate",
				name: "get_order_status",
				arguments: "{}",
			},
			output_index: 0,
		};
		const result = {
			type: "response.output_item.done" as const,
			item: {
				type: "function_call_output" as const,
				call_id: "call_duplicate",
				output: '{"status":"shipped"}',
			},
			output_index: 1,
		};
		let state = reduceStreamEvent(createInitialStreamState(), call);
		state = reduceStreamEvent(state, call);
		state = reduceStreamEvent(state, result);
		state = reduceStreamEvent(state, result);

		expect(state.pendingTools.size).toBe(0);
		expect(state.completedTools.size).toBe(1);
		expect(state.toolDetails.size).toBe(1);
	});

	test("completion preserves the trace identifier", () => {
		const state = reduceStreamEvent(createInitialStreamState(), {
			type: "response.completed",
			response: {
				id: "response-1",
				trace_id: "trace-1",
				status: "completed",
				output: [],
			},
		});
		expect(state.traceId).toBe("trace-1");
	});
});
