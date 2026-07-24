import { expect, test } from "@playwright/test";
import { sanitizePayload } from "../server/src/lib/conversation.js";

test.describe("conversation persistence policy", () => {
	test("redacts credentials and reasoning recursively", () => {
		const payload = sanitizePayload({
			type: "function_call",
			reasoning: "private chain",
			arguments: JSON.stringify({ order_id: "O-1", api_key: "secret" }),
			nested: { refresh_token: "never persist" },
		});

		expect(payload.reasoning).toBe("<redacted>");
		expect(payload.nested).toEqual({ refresh_token: "<redacted>" });
		expect(JSON.parse(payload.arguments as string)).toEqual({
			order_id: "O-1",
			api_key: "<redacted>",
		});
	});

	test("does not redact unrelated field names", () => {
		const payload = sanitizePayload({ monkey_type: "capuchin" });
		expect(payload).toEqual({ monkey_type: "capuchin" });
	});
});
