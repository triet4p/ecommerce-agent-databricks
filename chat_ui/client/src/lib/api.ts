// =============================================================================
// Typed API client — calls same-origin Chat UI server endpoints (S4-B3)
// =============================================================================

import type {
	Conversation,
	ConversationSummary,
	ConversationWithItems,
	HealthResponse,
	Turn,
	WhoAmIResponse,
} from "@ecommerce-agent/core";

const BASE = "/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

class ApiRequestError extends Error {
	code: string;
	status: number;

	constructor(code: string, message: string, status: number) {
		super(message);
		this.name = "ApiRequestError";
		this.code = code;
		this.status = status;
	}
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		headers: {
			"Content-Type": "application/json",
			...options.headers,
		},
		...options,
	});

	if (!res.ok) {
		let code = "UNKNOWN";
		let message = `HTTP ${res.status}`;
		try {
			const body = await res.json();
			code = body?.error?.code ?? code;
			message = body?.error?.message ?? message;
		} catch {
			// use defaults
		}
		throw new ApiRequestError(code, message, res.status);
	}

	if (res.status === 204) return undefined as T;
	return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export async function listConversations(): Promise<ConversationSummary[]> {
	return request<ConversationSummary[]>("/conversations");
}

export async function createConversation(
	title?: string,
): Promise<Conversation> {
	return request<Conversation>("/conversations", {
		method: "POST",
		body: JSON.stringify({ title }),
	});
}

export async function getConversation(
	id: string,
): Promise<ConversationWithItems> {
	return request<ConversationWithItems>(`/conversations/${id}`);
}

export async function updateConversation(
	id: string,
	title: string,
): Promise<Conversation> {
	return request<Conversation>(`/conversations/${id}`, {
		method: "PATCH",
		body: JSON.stringify({ title }),
	});
}

export async function deleteConversation(id: string): Promise<void> {
	await request<void>(`/conversations/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Turns
// ---------------------------------------------------------------------------

export async function createTurn(
	conversationId: string,
	clientRequestId: string,
	userMessage: string,
): Promise<Turn> {
	return request<Turn>(`/conversations/${conversationId}/turns`, {
		method: "POST",
		body: JSON.stringify({ clientRequestId, userMessage }),
	});
}

export async function cancelTurn(
	conversationId: string,
	turnId: string,
): Promise<void> {
	await request<void>(
		`/conversations/${conversationId}/turns/${turnId}/cancel`,
		{
			method: "POST",
		},
	);
}

// ---------------------------------------------------------------------------
// Streaming — returns an AbortController and event stream
// ---------------------------------------------------------------------------

export interface StreamCallbacks {
	onTextDelta: (delta: string, itemId: string) => void;
	onOutputItemDone: (item: unknown) => void;
	onError: (code: string, message: string) => void;
	onComplete: (response: {
		id: string;
		status: "completed";
		output: unknown[];
		trace_id?: string;
	}) => void;
}

export function startStream(
	conversationId: string,
	turnId: string,
	userMessage: string,
	callbacks: StreamCallbacks,
): AbortController {
	const controller = new AbortController();

	(async () => {
		try {
			const res = await fetch(
				`${BASE}/conversations/${conversationId}/turns/${turnId}/stream`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ userMessage }),
					signal: controller.signal,
				},
			);

			if (!res.ok) {
				let message = `HTTP ${res.status}`;
				try {
					const body = await res.json();
					message = body?.error?.message ?? message;
				} catch {
					// use default
				}
				callbacks.onError("STREAM_ERROR", message);
				return;
			}

			const reader = res.body?.getReader();
			if (!reader) {
				callbacks.onError("NO_BODY", "Response has no body");
				return;
			}

			const decoder = new TextDecoder();
			let buffer = "";
			let completionResponse:
				| Parameters<StreamCallbacks["onComplete"]>[0]
				| null = null;
			let streamHadError = false;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split("\n");
				buffer = lines.pop() ?? "";

				for (const line of lines) {
					const trimmed = line.trim();
					if (!trimmed) continue;
					if (!trimmed.startsWith("data: ")) continue;

					const payload = trimmed.slice(6);

					if (payload === "[DONE]") {
						if (completionResponse) {
							callbacks.onComplete(completionResponse);
						} else if (!streamHadError) {
							callbacks.onError(
								"INCOMPLETE_STREAM",
								"Stream ended without a completion event",
							);
						}
						return;
					}

					try {
						const event = JSON.parse(payload);
						if (event.trace_id && completionResponse) {
							completionResponse.trace_id = event.trace_id;
						}
						switch (event.type) {
							case "response.output_text.delta":
								callbacks.onTextDelta(event.delta, event.item_id);
								break;
							case "response.output_item.done":
								callbacks.onOutputItemDone(event.item);
								break;
							case "error":
								streamHadError = true;
								callbacks.onError(event.code, event.message);
								break;
							case "response.completed":
								completionResponse = event.response;
								break;
						}
					} catch {
						// skip unparseable lines
					}
				}
			}
			if (completionResponse) {
				callbacks.onComplete(completionResponse);
			} else if (!streamHadError) {
				callbacks.onError(
					"INCOMPLETE_STREAM",
					"Stream ended without a completion event",
				);
			}
		} catch (err: unknown) {
			if (err instanceof Error && err.name === "AbortError") return;
			callbacks.onError(
				"STREAM_ERROR",
				err instanceof Error ? err.message : "Stream failed",
			);
		}
	})();

	return controller;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<HealthResponse> {
	return request<HealthResponse>("/health");
}

export async function getCurrentUser(): Promise<WhoAmIResponse> {
	return request<WhoAmIResponse>("/whoami");
}
