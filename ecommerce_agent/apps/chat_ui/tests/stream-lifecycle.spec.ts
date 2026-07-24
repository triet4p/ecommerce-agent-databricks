import { expect, test } from "@playwright/test";
import {
	accumulateOutputItems,
	extractTraceId,
} from "../server/src/routes/turns.js";

test.describe("stream persistence lifecycle", () => {
	test("persists output only after terminal completion and keeps trace", () => {
		const events = [
			{
				type: "response.output_item.done",
				item: { id: "msg-1", type: "message" },
			},
			{
				type: "response.completed",
				response: { id: "response-1", trace_id: "tr-1" },
			},
		];

		expect(accumulateOutputItems(events)).toEqual([
			{ id: "msg-1", type: "message" },
		]);
		expect(extractTraceId(events)).toBe("tr-1");
	});

	test("never persists partial output after an error or missing terminal event", () => {
		const output = { type: "response.output_item.done", item: { id: "msg-1" } };
		expect(accumulateOutputItems([output])).toEqual([]);
		expect(accumulateOutputItems([output, { type: "error" }])).toEqual([]);
	});
});
