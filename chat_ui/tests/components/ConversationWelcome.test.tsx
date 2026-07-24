import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import ConversationWelcome from "../../client/src/components/ConversationWelcome";

describe("ConversationWelcome", () => {
	test("offers purposeful governed-commerce starters", () => {
		const onSelect = vi.fn();
		render(<ConversationWelcome onSelect={onSelect} />);

		expect(
			screen.getByText("Resolve order questions with context, not guesswork."),
		).toBeVisible();
		fireEvent.click(
			screen.getByRole("button", {
				name: /Track an order: Check status, timing, and delivery progress/,
			}),
		);
		expect(onSelect).toHaveBeenCalledWith(
			"Help me check the current status of an order.",
		);
	});
});
