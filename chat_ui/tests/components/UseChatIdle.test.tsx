import type { ConversationItem } from "@ecommerce-agent/core";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { useChat } from "../../client/src/hooks/useChat";

const NO_ITEMS: ConversationItem[] = [];

describe("useChat idle lifecycle", () => {
	test("a loaded conversation starts idle and allows sending", async () => {
		const { result } = renderHook(() => useChat("conversation-1", NO_ITEMS));

		await waitFor(() => {
			expect(result.current.streamState.isStreaming).toBe(false);
		});
	});
});
