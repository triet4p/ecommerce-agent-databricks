// =============================================================================
// Tests for display policy — tool names, phase labels, sanitization (S4-E2)
// =============================================================================

import {
	derivePhaseLabel,
	sanitizeOutput,
	toolDisplayName,
	truncateArguments,
} from "@ecommerce-agent/core";
import { expect, test } from "@playwright/test";

test.describe("Tool display names", () => {
	test("known tools get friendly labels", () => {
		expect(toolDisplayName("get_order_status")).toBe("🔍 Order lookup");
		expect(toolDisplayName("get_customer_order_history")).toBe(
			"📋 Order history",
		);
		expect(toolDisplayName("search_policy_docs")).toBe("📄 Policy search");
		expect(
			toolDisplayName("ecommerce_agent__agent_layer__get_order_status"),
		).toBe("🔍 Order lookup");
	});

	test("unknown tools get generic label", () => {
		expect(toolDisplayName("unknown_tool")).toBe("🔧 unknown_tool");
	});
});

test.describe("Output sanitization", () => {
	test("short output is unchanged", () => {
		expect(sanitizeOutput("Hello", 1000)).toBe("Hello");
	});

	test("long output is truncated", () => {
		const long = "a".repeat(2000);
		const result = sanitizeOutput(long, 1000);
		expect(result.length).toBe(1001); // 1000 chars + "…"
		expect(result.endsWith("…")).toBe(true);
	});
});

test.describe("Argument truncation", () => {
	test("short args are unchanged", () => {
		expect(truncateArguments('{"a": 1}', 500)).toBe('{"a": 1}');
	});

	test("long args are truncated", () => {
		const long = "a".repeat(600);
		const result = truncateArguments(long, 500);
		expect(result.length).toBe(501);
		expect(result.endsWith("…")).toBe(true);
	});
});

test.describe("Phase label derivation", () => {
	test("composing when only text", () => {
		const label = derivePhaseLabel({
			hasTextDelta: true,
			hasPendingToolCall: false,
			hasToolResult: false,
			isMultiStep: false,
			isError: false,
		});
		expect(label).toBe("🤖 Composing…");
	});

	test("analyzing when text and pending tool", () => {
		const label = derivePhaseLabel({
			hasTextDelta: true,
			hasPendingToolCall: true,
			hasToolResult: false,
			isMultiStep: false,
			isError: false,
		});
		expect(label).toBe("🔍 Analyzing…");
	});

	test("running tool when pending without text", () => {
		const label = derivePhaseLabel({
			hasTextDelta: false,
			hasPendingToolCall: true,
			hasToolResult: false,
			isMultiStep: false,
			isError: false,
		});
		expect(label).toBe("🔧 Running tool…");
	});

	test("tool complete on result", () => {
		const label = derivePhaseLabel({
			hasTextDelta: false,
			hasPendingToolCall: false,
			hasToolResult: true,
			isMultiStep: false,
			isError: false,
		});
		expect(label).toBe("✅ Tool complete");
	});

	test("error state", () => {
		const label = derivePhaseLabel({
			hasTextDelta: false,
			hasPendingToolCall: false,
			hasToolResult: false,
			isMultiStep: false,
			isError: true,
		});
		expect(label).toBe("❌ Error");
	});
});
