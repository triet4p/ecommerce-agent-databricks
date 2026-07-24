import { describe, expect, test } from "vitest";
import { deriveConversationTitle } from "../../client/src/pages/ChatPage";

describe("deriveConversationTitle", () => {
	test("normalizes whitespace and truncates the first prompt", () => {
		expect(deriveConversationTitle("  Check   my order  ")).toBe(
			"Check my order",
		);
		expect(deriveConversationTitle("x".repeat(60), 12)).toBe("xxxxxxxxxxx…");
	});
});
