import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { useChat } from "../../client/src/hooks/useChat";

const createTurnMock = vi.fn();

vi.mock("../../client/src/lib/api", () => ({
	createTurn: (...args: unknown[]) => createTurnMock(...args),
	startStream: vi.fn(),
	cancelTurn: vi.fn(),
}));

describe("useChat create-turn errors", () => {
	beforeEach(() => {
		createTurnMock.mockReset();
		createTurnMock.mockRejectedValue(new Error("Invalid request body"));
	});

	test("renders an assistant error and retry does not duplicate the user message", async () => {
		const { result } = renderHook(() => useChat("conversation-1"));

		await act(async () => {
			await result.current.sendMessage("oversized message");
		});

		expect(result.current.streamState.hasError).toBe(true);
		expect(result.current.messages).toEqual([
			expect.objectContaining({
				role: "user",
				content: "oversized message",
			}),
			expect.objectContaining({
				role: "assistant",
				content: "Error: Invalid request body",
			}),
		]);

		await act(async () => {
			result.current.retry("oversized message");
		});

		await vi.waitFor(() => expect(createTurnMock).toHaveBeenCalledTimes(2));
		expect(
			result.current.messages.filter((message) => message.role === "user"),
		).toHaveLength(1);
	});

	test("does not promote a failed assistant response into normal history", async () => {
		const { result } = renderHook(() => useChat("conversation-1"));

		await act(async () => {
			await result.current.sendMessage("first request");
		});
		await act(async () => {
			await result.current.sendMessage("second request");
		});

		expect(
			result.current.messages.filter(
				(message) =>
					message.role === "assistant" &&
					message.content === "Error: Invalid request body",
			),
		).toHaveLength(1);
		expect(
			result.current.messages.filter((message) => message.role === "user"),
		).toHaveLength(2);
	});
});
