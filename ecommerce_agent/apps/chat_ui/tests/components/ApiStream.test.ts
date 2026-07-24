import { afterEach, describe, expect, test, vi } from "vitest";
import { startStream } from "../../client/src/lib/api";

function responseFromChunks(chunks: string[]): Response {
	const encoder = new TextEncoder();
	let index = 0;
	return new Response(
		new ReadableStream({
			pull(controller) {
				const chunk = chunks[index++];
				if (chunk === undefined) {
					controller.close();
					return;
				}
				controller.enqueue(encoder.encode(chunk));
			},
		}),
		{ status: 200, headers: { "Content-Type": "text/event-stream" } },
	);
}

describe("startStream", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	test("completes when the proxy sends terminal metadata before DONE", async () => {
		vi.stubGlobal(
			"fetch",
			vi
				.fn()
				.mockResolvedValue(
					responseFromChunks([
						'data: {"type":"response.output_text.delta","delta":"hello","item_id":"i1"}\n\n',
						'data: {"type":"response.completed","response":{"id":"r1","status":"completed","output":[]}}\n\n',
						'data: {"trace_id":"trace-1"}\n\n',
						"data: [DONE]\n\n",
					]),
				),
		);

		const onTextDelta = vi.fn();
		const onComplete = vi.fn();
		const onError = vi.fn();

		startStream("conversation-1", "turn-1", "hello", {
			onTextDelta,
			onOutputItemDone: vi.fn(),
			onError,
			onComplete,
		});

		await vi.waitFor(() => expect(onComplete).toHaveBeenCalledOnce());
		expect(onTextDelta).toHaveBeenCalledWith("hello", "i1");
		expect(onComplete).toHaveBeenCalledWith({
			id: "r1",
			status: "completed",
			output: [],
			trace_id: "trace-1",
		});
		expect(onError).not.toHaveBeenCalled();
	});
});
