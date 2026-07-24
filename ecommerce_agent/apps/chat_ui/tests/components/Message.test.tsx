import {
	createInitialStreamState,
	reduceStreamEvent,
} from "@ecommerce-agent/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import Message from "../../client/src/components/Message";

function completedToolState() {
	let state = createInitialStreamState();
	state = reduceStreamEvent(state, {
		type: "response.output_item.done",
		output_index: 0,
		item: {
			type: "function_call",
			id: "call-item-1",
			call_id: "call-1",
			name: "get_order_status",
			arguments: '{"order_id":"order-1"}',
		},
	});
	state = reduceStreamEvent(state, {
		type: "response.output_item.done",
		output_index: 1,
		item: {
			type: "function_call_output",
			call_id: "call-1",
			output: '{"status":"shipped"}',
		},
	});
	return reduceStreamEvent(state, {
		type: "response.completed",
		response: {
			id: "response-1",
			trace_id: "trace-1",
			status: "completed",
			output: [],
		},
	});
}

describe("Message", () => {
	test("renders GFM Markdown while ignoring raw HTML", () => {
		const { container } = render(
			<Message
				messageRole="assistant"
				content={
					"**Shipped**\n\n- Carrier confirmed\n\n<script>alert(1)</script>"
				}
			/>,
		);

		expect(screen.getByText("Shipped").tagName).toBe("STRONG");
		expect(screen.getByText("Carrier confirmed").tagName).toBe("LI");
		expect(container.querySelector("script")).toBeNull();
	});

	test("reveals correlated tool arguments and result", () => {
		render(
			<Message
				messageRole="assistant"
				content="Your order shipped."
				streamState={completedToolState()}
			/>,
		);

		fireEvent.click(screen.getByRole("button", { name: /Order lookup/ }));
		expect(screen.getByText(/"order_id": "order-1"/)).toBeVisible();
		expect(screen.getByText(/"status": "shipped"/)).toBeVisible();
		expect(screen.getByText(/AI-generated from governed/)).toBeVisible();
	});

	test("renders a terminal stream error", () => {
		const errorState = reduceStreamEvent(createInitialStreamState(), {
			type: "error",
			code: "UPSTREAM_ERROR",
			message: "Agent unavailable",
		});
		render(
			<Message messageRole="assistant" content="" streamState={errorState} />,
		);
		expect(screen.getByText("Agent unavailable")).toBeVisible();
		expect(screen.getByText("The assistant could not finish.")).toBeVisible();
	});
});
