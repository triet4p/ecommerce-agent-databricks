// =============================================================================
// Turn routes — create, stream, cancel, retry (S4-C4, S4-C5)
// =============================================================================

import { type Request, type Response, Router } from "express";
import { v4 as uuidv4 } from "uuid";
import { z } from "zod";
import type {
	ConversationItem,
	ConversationRepository,
} from "../lib/conversation.js";
import { getAgentAppUrl, getAuthHeaders } from "../lib/oauth.js";

const AGENT_REQUEST_TIMEOUT_MS = 110_000;
const MAX_MESSAGE_CHARS = 20_000;
const MAX_REPLAY_ITEMS = 100;
const MAX_CONTEXT_CHARS = 80_000;

interface ActiveStream {
	controller: AbortController;
	cancellationRequested: boolean;
	cancelPromise: Promise<void> | null;
}

const activeControllers = new Set<AbortController>();

export function abortActiveStreams(): void {
	for (const controller of activeControllers) controller.abort();
}

export interface BackpressureResponse {
	destroyed: boolean;
	writableEnded: boolean;
	write(chunk: string): boolean;
	once(event: "drain" | "close", listener: () => void): unknown;
	off(event: "drain" | "close", listener: () => void): unknown;
}

type TurnRepository = Pick<
	ConversationRepository,
	"createTurn" | "getReplayItems" | "completeTurn" | "failTurn" | "cancelTurn"
>;

export interface TurnRouteDependencies {
	resolveAgentUrl: () => Promise<string>;
	resolveAuthHeaders: () => Promise<Record<string, string>>;
	fetchImpl: typeof fetch;
}

const defaultDependencies: TurnRouteDependencies = {
	resolveAgentUrl: getAgentAppUrl,
	resolveAuthHeaders: getAuthHeaders,
	fetchImpl: fetch,
};

class ClientDisconnectedError extends Error {
	constructor() {
		super("Client disconnected");
		this.name = "ClientDisconnectedError";
	}
}

export async function writeWithBackpressure(
	res: BackpressureResponse,
	chunk: string,
): Promise<void> {
	if (res.destroyed || res.writableEnded) throw new ClientDisconnectedError();
	if (res.write(chunk)) return;

	await new Promise<void>((resolve, reject) => {
		const cleanup = () => {
			res.off("drain", onDrain);
			res.off("close", onClose);
		};
		const onDrain = () => {
			cleanup();
			resolve();
		};
		const onClose = () => {
			cleanup();
			reject(new ClientDisconnectedError());
		};
		res.once("drain", onDrain);
		res.once("close", onClose);
	});
}

export function createTurnRoutes(
	repo: TurnRepository,
	dependencies: TurnRouteDependencies = defaultDependencies,
): Router {
	const router = Router({ mergeParams: true });
	const activeStreams = new Map<string, ActiveStream>();

	// POST /api/conversations/:id/turns — create turn (idempotent)
	router.post("/", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const conversationId = req.params.id as string;

			const schema = z.object({
				clientRequestId: z.string().uuid(),
				userMessage: z.string().trim().min(1).max(MAX_MESSAGE_CHARS),
			});
			const { clientRequestId } = schema.parse(req.body) as {
				clientRequestId: string;
				userMessage: string;
			};

			const turn = await repo.createTurn(conversationId, user, clientRequestId);
			res.status(201).json(turn);
		} catch (err: unknown) {
			if (err instanceof z.ZodError) {
				res.status(400).json({
					error: { code: "BAD_REQUEST", message: "Invalid request body" },
				});
				return;
			}
			if (err instanceof Error && err.name === "ConversationNotFoundError") {
				res.status(404).json({
					error: { code: "NOT_FOUND", message: err.message },
				});
				return;
			}
			console.error("Failed to create turn:", err);
			res.status(500).json({
				error: { code: "INTERNAL_ERROR", message: "Failed to create turn" },
			});
		}
	});

	// POST /api/conversations/:id/turns/:turnId/stream — SSE stream
	router.post("/:turnId/stream", async (req: Request, res: Response) => {
		const user = req.user;
		const conversationId = req.params.id as string;
		const turnId = req.params.turnId as string;
		const streamKey = `${conversationId}:${turnId}`;
		let activeStream: ActiveStream | null = null;

		const requestCancellation = (): Promise<void> => {
			if (!activeStream) return Promise.resolve();
			activeStream.cancellationRequested = true;
			activeStream.controller.abort();
			activeStream.cancelPromise ??= repo.cancelTurn(
				turnId,
				conversationId,
				user,
			);
			return activeStream.cancelPromise;
		};
		const endCancelledResponse = async (): Promise<void> => {
			if (!res.destroyed && !res.writableEnded) {
				await writeWithBackpressure(res, "data: [DONE]\n\n").catch(
					() => undefined,
				);
				res.end();
			}
		};

		try {
			const schema = z.object({
				userMessage: z.string().trim().min(1).max(MAX_MESSAGE_CHARS),
			});
			const { userMessage } = schema.parse(req.body);

			// Set SSE headers
			res.setHeader("Content-Type", "text/event-stream");
			res.setHeader("Cache-Control", "no-cache");
			res.setHeader("Connection", "keep-alive");
			res.setHeader("X-Accel-Buffering", "no");

			// Build replay history from Sprint 3 data
			const replayItems = (
				await repo.getReplayItems(conversationId, user)
			).slice(-MAX_REPLAY_ITEMS);
			const inputItems = buildReplayRequest(replayItems, userMessage);

			// Resolve Agent App URL and authenticate
			const agentUrl = await dependencies.resolveAgentUrl();
			const authHeaders = await dependencies.resolveAuthHeaders();

			const requestBody = {
				input: inputItems,
				stream: true,
			};

			console.log(
				`[STREAM] Starting stream for turn ${turnId} with ${inputItems.length} input items`,
			);

			const upstreamAbort = new AbortController();
			activeStream = {
				controller: upstreamAbort,
				cancellationRequested: false,
				cancelPromise: null,
			};
			activeStreams.set(streamKey, activeStream);
			activeControllers.add(upstreamAbort);
			res.once("close", () => {
				if (!res.writableEnded) {
					void requestCancellation().catch((error) =>
						console.error(
							"[STREAM] Failed to cancel disconnected turn:",
							error,
						),
					);
				}
			});
			const agentRes = await dependencies.fetchImpl(
				`${agentUrl}/api/responses`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"x-mlflow-return-trace-id": "true",
						...authHeaders,
					},
					body: JSON.stringify(requestBody),
					signal: AbortSignal.any([
						upstreamAbort.signal,
						AbortSignal.timeout(AGENT_REQUEST_TIMEOUT_MS),
					]),
				},
			);

			if (!agentRes.ok) {
				const errBody = await agentRes.text();
				console.error(
					`[STREAM] Agent API returned ${agentRes.status}: ${errBody}`,
				);
				await writeWithBackpressure(
					res,
					`data: ${JSON.stringify({
						type: "error",
						code: "AGENT_ERROR",
						message: `Agent API error: ${agentRes.status}`,
					})}\n\n`,
				);
				// Mark turn as failed
				try {
					await repo.failTurn(turnId, conversationId, user);
				} catch (failErr) {
					console.error("[STREAM] Failed to mark turn as failed:", failErr);
				}
				await writeWithBackpressure(res, "data: [DONE]\n\n");
				res.end();
				return;
			}

			// Stream the Agent App response back to the browser
			const reader = agentRes.body?.getReader();
			if (!reader) {
				await writeWithBackpressure(
					res,
					`data: ${JSON.stringify({
						type: "error",
						code: "NO_BODY",
						message: "Agent response has no body",
					})}\n\n`,
				);
				await repo
					.failTurn(turnId, conversationId, user)
					.catch((error) =>
						console.error("[STREAM] Failed to mark missing body:", error),
					);
				await writeWithBackpressure(res, "data: [DONE]\n\n");
				res.end();
				return;
			}

			const decoder = new TextDecoder();
			const collectedEvents: unknown[] = [];
			let terminalSuccess = false;
			let hadError = false;
			let sseBuffer = "";

			try {
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					const text = decoder.decode(value, { stream: true });
					sseBuffer += text;
					const lines = sseBuffer.split("\n");
					sseBuffer = lines.pop() ?? "";
					for (const line of lines) {
						const trimmed = line.trim();
						if (trimmed.startsWith("data: ")) {
							const payload = trimmed.slice(6);
							if (payload === "[DONE]") {
								// The Agent may send DONE before trailing completion or
								// trace events. The proxy owns the downstream sentinel
								// and emits it only after terminal persistence.
								continue;
							}
							try {
								const event = JSON.parse(payload);
								collectedEvents.push(event);
								if (event.type === "response.completed") terminalSuccess = true;
								if (event.type === "error") hadError = true;
							} catch {
								// skip unparseable
							}
						}
						await writeWithBackpressure(res, `${line}\n`);
					}
				}
			} catch (err: unknown) {
				if (activeStream.cancellationRequested) {
					await activeStream.cancelPromise;
					await endCancelledResponse();
					return;
				}
				console.error("[STREAM] Read error:", err);
				// Send error to browser
				await writeWithBackpressure(
					res,
					`data: ${JSON.stringify({
						type: "error",
						code: "STREAM_ERROR",
						message: "Stream read error",
					})}\n\n`,
				);
				hadError = true;
			}

			if (activeStream.cancellationRequested) {
				await activeStream.cancelPromise;
				await endCancelledResponse();
				return;
			}

			// Persist before ending the response so a refresh observes a terminal turn.
			const outputItems = accumulateOutputItems(collectedEvents);
			if (terminalSuccess && !hadError) {
				try {
					await repo.completeTurn(
						turnId,
						conversationId,
						user,
						outputItems,
						extractTraceId(collectedEvents),
						userMessage,
					);
					console.log(`[STREAM] Turn ${turnId} completed successfully`);
				} catch (persistErr) {
					console.error(
						"[STREAM] Failed to persist completed turn:",
						persistErr,
					);
				}
			} else if (!terminalSuccess || hadError) {
				try {
					await repo.failTurn(turnId, conversationId, user);
					console.log(`[STREAM] Turn ${turnId} marked as failed`);
				} catch (failErr) {
					console.error("[STREAM] Failed to mark turn as failed:", failErr);
				}
			}
			await writeWithBackpressure(res, "data: [DONE]\n\n");
			res.end();
		} catch (err: unknown) {
			if (
				activeStream?.cancellationRequested ||
				err instanceof ClientDisconnectedError
			) {
				await requestCancellation().catch((cancelError) =>
					console.error(
						"[STREAM] Failed to persist cancellation:",
						cancelError,
					),
				);
				await endCancelledResponse();
				return;
			}
			if (err instanceof z.ZodError) {
				res.status(400).json({
					error: { code: "BAD_REQUEST", message: "Invalid request body" },
				});
				return;
			}
			if (err instanceof ContextBudgetError) {
				res.status(413).json({
					error: {
						code: "CONTEXT_BUDGET_EXCEEDED",
						message: err.message,
					},
				});
				return;
			}
			console.error("[STREAM] Unexpected error:", err);
			if (!res.headersSent) {
				res.status(500).json({
					error: { code: "INTERNAL_ERROR", message: "Stream error" },
				});
			} else {
				await repo
					.failTurn(turnId, conversationId, user)
					.catch((failError) =>
						console.error(
							"[STREAM] Failed to mark unexpected error:",
							failError,
						),
					);
				if (!res.destroyed && !res.writableEnded) {
					await writeWithBackpressure(
						res,
						`data: ${JSON.stringify({ type: "error", code: "STREAM_ERROR", message: "Stream error" })}\n\n`,
					).catch(() => undefined);
					await writeWithBackpressure(res, "data: [DONE]\n\n").catch(
						() => undefined,
					);
					res.end();
				}
			}
		} finally {
			if (activeStream) {
				activeStreams.delete(streamKey);
				activeControllers.delete(activeStream.controller);
			}
		}
	});

	// POST /api/conversations/:id/turns/:turnId/cancel
	router.post("/:turnId/cancel", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const conversationId = req.params.id as string;
			const turnId = req.params.turnId as string;
			const activeStream = activeStreams.get(`${conversationId}:${turnId}`);
			if (activeStream) {
				activeStream.cancellationRequested = true;
				activeStream.cancelPromise ??= repo.cancelTurn(
					turnId,
					conversationId,
					user,
				);
				activeStream.controller.abort();
				await activeStream.cancelPromise;
			} else {
				await repo.cancelTurn(turnId, conversationId, user);
			}
			res.status(200).json({ status: "cancelled" });
		} catch (err: unknown) {
			console.error("Failed to cancel turn:", err);
			res.status(500).json({
				error: { code: "INTERNAL_ERROR", message: "Failed to cancel turn" },
			});
		}
	});

	// POST /api/conversations/:id/turns/:turnId/retry
	router.post("/:turnId/retry", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const conversationId = req.params.id as string;
			const turnId = req.params.turnId as string;

			const schema = z.object({
				userMessage: z.string().trim().min(1).max(MAX_MESSAGE_CHARS),
			});
			const { userMessage } = schema.parse(req.body);

			// Create a new turn with fresh client request ID
			const clientRequestId = uuidv4();
			const turn = await repo.createTurn(conversationId, user, clientRequestId);

			res.status(201).json(turn);
		} catch (err: unknown) {
			if (err instanceof z.ZodError) {
				res.status(400).json({
					error: { code: "BAD_REQUEST", message: "Invalid request body" },
				});
				return;
			}
			console.error("Failed to retry turn:", err);
			res.status(500).json({
				error: { code: "INTERNAL_ERROR", message: "Failed to retry turn" },
			});
		}
	});

	// POST /api/conversations/:id/turns/:turnId/feedback (deferred slot)
	router.post("/:turnId/feedback", (_req: Request, res: Response) => {
		res.status(501).json({
			error: {
				code: "NOT_IMPLEMENTED",
				message: "Feedback not implemented yet",
			},
		});
	});

	return router;
}

// ---------------------------------------------------------------------------
// History replay helpers — mirrors Sprint 3 replay.py semantics
// ---------------------------------------------------------------------------

export function buildReplayRequest(
	items: ConversationItem[],
	newMessage: string,
): unknown[] {
	const history: unknown[] = [];

	for (const item of items) {
		if (item.item_type === "message") {
			const role = item.payload?.role || item.role || "assistant";
			const content = extractItemText(item);
			if (content) {
				history.push({
					role,
					content: [{ type: "input_text", text: content }],
				});
			}
		}
		// function_call and function_call_output skipped per Sprint 3 semantics
	}

	history.push({
		role: "user",
		content: [{ type: "input_text", text: newMessage }],
	});

	const contextChars = history.reduce<number>(
		(total, item) => total + JSON.stringify(item).length,
		0,
	);
	if (contextChars > MAX_CONTEXT_CHARS) {
		throw new ContextBudgetError(MAX_CONTEXT_CHARS);
	}

	return history;
}

class ContextBudgetError extends Error {
	constructor(limit: number) {
		super(`Conversation context exceeds the ${limit}-character safety budget`);
		this.name = "ContextBudgetError";
	}
}

function extractItemText(item: ConversationItem): string | null {
	const payload = item.payload as {
		content?: Array<{ type?: string; text?: string }>;
	};
	const content = payload.content ?? [];
	const texts: string[] = [];

	for (const block of content) {
		if (
			block?.type === "output_text" ||
			block?.type === "input_text" ||
			block?.type === "text"
		) {
			if (block.text) texts.push(block.text);
		}
	}

	return texts.length > 0 ? texts.join("\n") : null;
}

export function accumulateOutputItems(
	events: unknown[],
): Record<string, unknown>[] {
	const items: Record<string, unknown>[] = [];
	let hadError = false;
	let completed = false;

	for (const event of events as Array<Record<string, unknown>>) {
		if (event.type === "error") {
			hadError = true;
			break;
		}
		if (event.type === "response.output_item.done" && isRecord(event.item)) {
			items.push(event.item);
		}
		if (event.type === "response.completed") {
			completed = true;
			break;
		}
	}

	if (hadError || !completed) return [];
	return items;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

export function extractTraceId(events: unknown[]): string | null {
	for (const event of events as Array<{
		response?: { id?: string; trace_id?: string };
		trace_id?: string;
	}>) {
		if (event.trace_id) return event.trace_id;
		if (event.response?.trace_id) return event.response.trace_id;
	}
	return null;
}
