import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import Composer from "../../client/src/components/Composer";

describe("Composer", () => {
	test("sends a trimmed message and clears the input", () => {
		const onSend = vi.fn();
		render(<Composer onSend={onSend} onStop={vi.fn()} isStreaming={false} />);
		const input = screen.getByLabelText("Message input");
		fireEvent.change(input, { target: { value: "  order status  " } });
		fireEvent.click(screen.getByRole("button", { name: "Send message" }));

		expect(onSend).toHaveBeenCalledWith("order status");
		expect(input).toHaveValue("");
	});

	test("shows Stop while streaming and delegates cancellation", () => {
		const onStop = vi.fn();
		render(<Composer onSend={vi.fn()} onStop={onStop} isStreaming={true} />);
		fireEvent.click(screen.getByRole("button", { name: "Stop generation" }));
		expect(onStop).toHaveBeenCalledOnce();
	});
});
