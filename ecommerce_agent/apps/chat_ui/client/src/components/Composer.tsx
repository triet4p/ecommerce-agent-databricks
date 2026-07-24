// =============================================================================
// Message composer — input field with send action (S4-D1)
// =============================================================================

import { CornerDownLeft, Send, Square } from "lucide-react";
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { Button } from "./ui/Button";

interface ComposerProps {
	onSend: (message: string) => void;
	onStop: () => void;
	isStreaming: boolean;
	disabled?: boolean;
}

export default function Composer({
	onSend,
	onStop,
	isStreaming,
	disabled,
}: ComposerProps) {
	const [input, setInput] = useState("");
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	// Auto-resize textarea
	useEffect(() => {
		const el = textareaRef.current;
		if (el) {
			el.style.height = "auto";
			el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
		}
	});

	const handleSubmit = (e?: React.FormEvent) => {
		e?.preventDefault();
		const trimmed = input.trim();
		if (!trimmed || disabled || isStreaming) return;
		onSend(trimmed);
		setInput("");
	};

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	};

	return (
		<form
			onSubmit={handleSubmit}
			className="sticky bottom-0 z-20 bg-gradient-to-t from-background via-background to-transparent px-3 pb-3 pt-6 sm:px-6 sm:pb-5"
		>
			<div className="mx-auto w-full max-w-4xl">
				<div className="flex items-end gap-2 rounded-2xl border bg-background p-2 shadow-[0_12px_36px_-20px_hsl(var(--foreground)/0.45)] transition focus-within:border-primary/50 focus-within:ring-4 focus-within:ring-primary/10">
					<textarea
						ref={textareaRef}
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder="Ask about an order, refund, seller, or policy..."
						rows={1}
						disabled={disabled}
						aria-label="Message input"
						className="max-h-[200px] min-h-11 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-5 placeholder:text-muted-foreground focus-visible:outline-none disabled:opacity-50"
					/>
					{isStreaming ? (
						<Button
							type="button"
							variant="destructive"
							onClick={onStop}
							aria-label="Stop generation"
							className="h-11 shrink-0 rounded-xl px-3"
						>
							<Square className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
							Stop
						</Button>
					) : (
						<Button
							type="submit"
							size="icon"
							disabled={!input.trim() || disabled}
							aria-label="Send message"
							className="h-11 w-11 shrink-0 rounded-xl"
						>
							<Send className="h-4 w-4" aria-hidden="true" />
						</Button>
					)}
				</div>
				<div className="mt-2 flex items-center justify-between px-1 text-[11px] text-muted-foreground">
					<span>
						AI-generated · verify important order and refund decisions
					</span>
					<span className="hidden items-center gap-1 sm:flex">
						<CornerDownLeft className="h-3 w-3" aria-hidden="true" />
						Enter to send · Shift+Enter for a new line
					</span>
				</div>
			</div>
		</form>
	);
}
