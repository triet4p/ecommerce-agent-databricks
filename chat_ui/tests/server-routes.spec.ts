import type { AddressInfo } from "node:net";
import { expect, test } from "@playwright/test";
import express from "express";
import { identityMiddleware } from "../server/src/middleware/identity";
import {
	type TurnRouteDependencies,
	createTurnRoutes,
} from "../server/src/routes/turns";

function makeRepository() {
	let status: "active" | "completed" | "failed" | "cancelled" = "active";
	let cancelCalls = 0;
	let failCalls = 0;
	let completeCalls = 0;
	let completedTrace: string | null | undefined;
	let completedItems = 0;
	const turn = {
		id: "turn-1",
		conversation_id: "conversation-1",
		client_request_id: "00000000-0000-4000-8000-000000000001",
		sequence: 1,
		status: "active" as const,
		mlflow_trace_id: null,
		created_at: new Date(0).toISOString(),
		completed_at: null,
	};

	return {
		repository: {
			createTurn: async () => turn,
			getReplayItems: async () => [],
			completeTurn: async (
				_turnId: string,
				_conversationId: string,
				_owner: string,
				items: Record<string, unknown>[],
				traceId?: string | null,
			) => {
				completeCalls++;
				completedItems = items.length;
				completedTrace = traceId;
				status = "completed";
				return { ...turn, status: "completed" as const };
			},
			failTurn: async () => {
				failCalls++;
				if (status === "active") status = "failed";
			},
			cancelTurn: async () => {
				cancelCalls++;
				if (status === "active") status = "cancelled";
			},
		},
		snapshot: () => ({
			status,
			cancelCalls,
			failCalls,
			completeCalls,
			completedItems,
			completedTrace,
		}),
	};
}

async function startTestServer(
	repository: ReturnType<typeof makeRepository>["repository"],
	dependencies: TurnRouteDependencies,
) {
	const app = express();
	app.use(express.json());
	app.use("/api", identityMiddleware);
	app.use(
		"/api/conversations/:id/turns",
		createTurnRoutes(repository, dependencies),
	);
	const server = app.listen(0, "127.0.0.1");
	await new Promise<void>((resolve) => server.once("listening", resolve));
	const { port } = server.address() as AddressInfo;
	return {
		baseUrl: `http://127.0.0.1:${port}`,
		close: () =>
			new Promise<void>((resolve, reject) =>
				server.close((error) => (error ? reject(error) : resolve())),
			),
	};
}

test("turn routes reject requests without trusted identity", async () => {
	const state = makeRepository();
	const server = await startTestServer(state.repository, {
		resolveAgentUrl: async () => "https://agent.invalid",
		resolveAuthHeaders: async () => ({}),
		fetchImpl: fetch,
	});
	try {
		const response = await fetch(
			`${server.baseUrl}/api/conversations/conversation-1/turns`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					clientRequestId: "00000000-0000-4000-8000-000000000001",
					userMessage: "hello",
				}),
			},
		);
		expect(response.status).toBe(401);
	} finally {
		await server.close();
	}
});

test("cancel aborts the active upstream exactly once without failing the turn", async () => {
	const state = makeRepository();
	const fetchImpl: typeof fetch = async (_input, init) => {
		const signal = init?.signal;
		const body = new ReadableStream<Uint8Array>({
			start(controller) {
				controller.enqueue(
					new TextEncoder().encode(
						'data: {"type":"response.output_text.delta","delta":"hello","item_id":"m1","content_index":0,"output_index":0}\n\n',
					),
				);
				signal?.addEventListener(
					"abort",
					() =>
						controller.error(
							new DOMException("The operation was aborted", "AbortError"),
						),
					{ once: true },
				);
			},
		});
		return new Response(body, {
			status: 200,
			headers: { "Content-Type": "text/event-stream" },
		});
	};
	const server = await startTestServer(state.repository, {
		resolveAgentUrl: async () => "https://agent.invalid",
		resolveAuthHeaders: async () => ({ Authorization: "Bearer test" }),
		fetchImpl,
	});
	const headers = {
		"Content-Type": "application/json",
		"X-Forwarded-User": "owner@example.com",
	};

	try {
		const streamPromise = fetch(
			`${server.baseUrl}/api/conversations/conversation-1/turns/turn-1/stream`,
			{
				method: "POST",
				headers,
				body: JSON.stringify({ userMessage: "hello" }),
			},
		);
		const streamResponse = await streamPromise;
		expect(streamResponse.status).toBe(200);

		const cancelResponse = await fetch(
			`${server.baseUrl}/api/conversations/conversation-1/turns/turn-1/cancel`,
			{ method: "POST", headers },
		);
		expect(cancelResponse.status).toBe(200);
		await expect(streamResponse.text()).resolves.toContain("[DONE]");
		expect(state.snapshot()).toEqual({
			status: "cancelled",
			cancelCalls: 1,
			failCalls: 0,
			completeCalls: 0,
			completedItems: 0,
			completedTrace: undefined,
		});
	} finally {
		await server.close();
	}
});

test("upstream HTTP errors propagate and fail the turn without partial persistence", async () => {
	const state = makeRepository();
	const server = await startTestServer(state.repository, {
		resolveAgentUrl: async () => "https://agent.invalid",
		resolveAuthHeaders: async () => ({ Authorization: "Bearer test" }),
		fetchImpl: async () => new Response("unavailable", { status: 503 }),
	});
	try {
		const response = await fetch(
			`${server.baseUrl}/api/conversations/conversation-1/turns/turn-1/stream`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"X-Forwarded-User": "owner@example.com",
				},
				body: JSON.stringify({ userMessage: "hello" }),
			},
		);
		expect(response.status).toBe(200);
		const body = await response.text();
		expect(body).toContain('"code":"AGENT_ERROR"');
		expect(body).toContain("[DONE]");
		expect(state.snapshot()).toMatchObject({
			status: "failed",
			failCalls: 1,
			completeCalls: 0,
		});
	} finally {
		await server.close();
	}
});

test("fragmented completion is proxied with OAuth and persisted with trace", async () => {
	const state = makeRepository();
	let authorization: string | null = null;
	let returnTraceId: string | null = null;
	const encoder = new TextEncoder();
	const chunks = [
		'data: {"type":"response.output_item.done","item":{"type":"message","id":"m1",',
		'"role":"assistant","content":[{"type":"output_text","text":"done"}]},"output_index":0}\n\n',
		"data: [DONE]\n\n",
		'data: {"type":"response.completed","response":{"id":"r1",',
		'"status":"completed","output":[]}}\n\ndata: {"trace_id":"trace-1"}\n\n',
	];
	const fetchImpl: typeof fetch = async (_input, init) => {
		const headers = new Headers(init?.headers);
		authorization = headers.get("Authorization");
		returnTraceId = headers.get("x-mlflow-return-trace-id");
		return new Response(
			new ReadableStream<Uint8Array>({
				start(controller) {
					for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
					controller.close();
				},
			}),
			{ status: 200, headers: { "Content-Type": "text/event-stream" } },
		);
	};
	const server = await startTestServer(state.repository, {
		resolveAgentUrl: async () => "https://agent.invalid",
		resolveAuthHeaders: async () => ({ Authorization: "Bearer app-token" }),
		fetchImpl,
	});
	try {
		const response = await fetch(
			`${server.baseUrl}/api/conversations/conversation-1/turns/turn-1/stream`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"X-Forwarded-User": "owner@example.com",
				},
				body: JSON.stringify({ userMessage: "hello" }),
			},
		);
		expect(response.status).toBe(200);
		const body = await response.text();
		expect(body).toContain("response.completed");
		expect(body.indexOf("response.completed")).toBeLessThan(
			body.indexOf("[DONE]"),
		);
		expect(authorization).toBe("Bearer app-token");
		expect(returnTraceId).toBe("true");
		expect(state.snapshot()).toMatchObject({
			status: "completed",
			failCalls: 0,
			completeCalls: 1,
			completedItems: 1,
			completedTrace: "trace-1",
		});
	} finally {
		await server.close();
	}
});
