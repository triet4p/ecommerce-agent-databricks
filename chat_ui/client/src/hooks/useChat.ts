// =============================================================================
// Custom chat hook — consumes Sprint 2 event contract via streaming proxy
// =============================================================================

import {
	type ChatUIStreamEvent,
	type OutputItem,
	type StreamState,
	createInitialStreamState,
	reduceStreamEvent,
} from "@ecommerce-agent/core";
import type { ConversationItem, Turn } from "@ecommerce-agent/core";
import { useCallback, useEffect, useRef, useState } from "react";
import { cancelTurn, createTurn, startStream } from "../lib/api";
import type { StreamCallbacks } from "../lib/api";

export type ChatMessage = {
	id: string;
	role: "user" | "assistant";
	content: string;
	persistedStreamState?: StreamState;
};
const EMPTY_ITEMS: ConversationItem[] = [];

export function restoreMessages(items: ConversationItem[]): ChatMessage[] {
	const toolItemsByTurn = new Map<string, OutputItem[]>();
	const traceByTurn = new Map<string, string>();

	for (const item of items) {
		if (
			(item.item_type === "function_call" ||
				item.item_type === "function_call_output") &&
			isOutputItem(item.payload)
		) {
			const outputs = toolItemsByTurn.get(item.turn_id) ?? [];
			outputs.push(item.payload);
			toolItemsByTurn.set(item.turn_id, outputs);
		}
		if (item.mlflow_trace_id) {
			traceByTurn.set(item.turn_id, item.mlflow_trace_id);
		}
	}

	return items.flatMap((item) => {
		if (item.item_type !== "message") return [];
		const payload = item.payload as {
			role?: "user" | "assistant";
			content?: Array<{ text?: string }>;
		};
		const content =
			payload.content?.map((part) => part.text ?? "").join("") ?? "";
		const role = payload.role ?? item.role;
		if (role !== "user" && role !== "assistant") return [];
		if (
			role === "assistant" &&
			toolItemsByTurn.has(item.turn_id) &&
			isJsonOnly(content)
		) {
			return [];
		}

		const message: ChatMessage = { id: item.id, role, content };
		if (role === "assistant") {
			const output = toolItemsByTurn.get(item.turn_id) ?? [];
			const traceId = traceByTurn.get(item.turn_id);
			if (output.length > 0 || traceId) {
				let persistedState = createInitialStreamState();
				for (const toolItem of output) {
					persistedState = reduceStreamEvent(persistedState, {
						type: "response.output_item.done",
						item: toolItem,
						output_index: 0,
					});
				}
				message.persistedStreamState = reduceStreamEvent(persistedState, {
					type: "response.completed",
					response: {
						id: traceId ?? "",
						trace_id: traceId,
						status: "completed",
						output,
					},
				});
			}
		}
		return [message];
	});
}

export function useChat(
	conversationId: string | null,
	persistedItems: ConversationItem[] = EMPTY_ITEMS,
) {
	const [streamState, setStreamState] = useState<StreamState>(
		createInitialStreamState(false),
	);
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const abortRef = useRef<AbortController | null>(null);
	const activeTurnRef = useRef<Turn | null>(null);

	useEffect(() => {
		// A route change is a reset boundary even when both conversations have
		// an empty persisted item list.
		void conversationId;
		abortRef.current?.abort();
		abortRef.current = null;
		activeTurnRef.current = null;
		setStreamState(createInitialStreamState(false));
		setMessages(restoreMessages(persistedItems));
	}, [conversationId, persistedItems]);

	const sendMessage = useCallback(
		async (userMessage: string, isRetry = false) => {
			if (!conversationId) return;

			// Reset stream state
			setStreamState(createInitialStreamState());
			if (!isRetry) {
				setMessages((prev) => {
					// A failed/partial assistant response is not persisted and must
					// not become a normal-looking answer when a later turn starts.
					const stableMessages =
						streamState.hasError && prev.at(-1)?.role === "assistant"
							? prev.slice(0, -1)
							: prev;
					return [
						...stableMessages,
						{ id: crypto.randomUUID(), role: "user", content: userMessage },
					];
				});
			}

			let assistantIndex = -1;

			try {
				// Create turn with idempotent client request ID
				const turn = await createTurn(
					conversationId,
					crypto.randomUUID(),
					userMessage,
				);

				activeTurnRef.current = turn;
				setMessages((prev) => {
					assistantIndex = prev.length;
					return [
						...prev,
						{ id: crypto.randomUUID(), role: "assistant", content: "" },
					];
				});

				// Start streaming
				const callbacks: StreamCallbacks = {
					onTextDelta: (delta: string) => {
						setStreamState((prev) => {
							const next = reduceStreamEvent(prev, {
								type: "response.output_text.delta",
								item_id: "",
								delta,
								content_index: 0,
								output_index: 0,
							});
							setMessages((msgs) => {
								const updated = [...msgs];
								if (assistantIndex < 0 || !updated[assistantIndex]) return msgs;
								updated[assistantIndex] = {
									...updated[assistantIndex],
									content: next.text,
								};
								return updated;
							});
							return next;
						});
					},
					onOutputItemDone: (item: unknown) => {
						if (!isOutputItem(item)) return;
						setStreamState((prev) => {
							const next = reduceStreamEvent(prev, {
								type: "response.output_item.done",
								item,
								output_index: 0,
							});
							return next;
						});
					},
					onError: (code: string, message: string) => {
						setStreamState((prev) => {
							const next = reduceStreamEvent(prev, {
								type: "error",
								code,
								message,
							});
							setMessages((msgs) => {
								const updated = [...msgs];
								if (updated[assistantIndex]) {
									updated[assistantIndex] = {
										...updated[assistantIndex],
										content: next.text || `Error: ${message}`,
									};
								}
								return updated;
							});
							return next;
						});
					},
					onComplete: (response) => {
						setStreamState((prev) => {
							const next = reduceStreamEvent(prev, {
								type: "response.completed",
								response: {
									id: response.id,
									trace_id: response.trace_id,
									status: "completed",
									output: response.output.filter(isOutputItem),
								},
							});
							return next;
						});
						activeTurnRef.current = null;
						abortRef.current = null;
					},
				};

				abortRef.current = startStream(
					conversationId,
					turn.id,
					userMessage,
					callbacks,
				);
			} catch (err: unknown) {
				const msg =
					err instanceof Error ? err.message : "Failed to start stream";
				setMessages((prev) => {
					const updated = [...prev];
					if (assistantIndex >= 0 && updated[assistantIndex]) {
						updated[assistantIndex] = {
							...updated[assistantIndex],
							content: `Error: ${msg}`,
						};
					} else {
						updated.push({
							id: crypto.randomUUID(),
							role: "assistant",
							content: `Error: ${msg}`,
						});
					}
					return updated;
				});
				setStreamState((prev) =>
					reduceStreamEvent(prev, {
						type: "error",
						code: "STREAM_FAILED",
						message: msg,
					}),
				);
			}
		},
		[conversationId, streamState.hasError],
	);

	const stop = useCallback(async () => {
		if (abortRef.current) {
			abortRef.current.abort();
			abortRef.current = null;
		}
		const turn = activeTurnRef.current;
		if (conversationId && turn?.status === "active") {
			try {
				await cancelTurn(conversationId, turn.id);
			} catch (error) {
				console.error("Failed to cancel turn", error);
			}
		}
		activeTurnRef.current = null;
		setStreamState((state) => ({ ...state, isStreaming: false }));
	}, [conversationId]);

	const retry = useCallback(
		(lastMessage: string) => {
			// Remove the last assistant message and retry
			setMessages((prev) =>
				prev.at(-1)?.role === "assistant" ? prev.slice(0, -1) : prev,
			);
			void sendMessage(lastMessage, true);
		},
		[sendMessage],
	);

	return {
		messages,
		streamState,
		sendMessage,
		stop,
		retry,
	};
}

function isOutputItem(item: unknown): item is OutputItem {
	return typeof item === "object" && item !== null && "type" in item;
}

function isJsonOnly(content: string): boolean {
	const trimmed = content.trim();
	if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return false;
	try {
		JSON.parse(trimmed);
		return true;
	} catch {
		return false;
	}
}
