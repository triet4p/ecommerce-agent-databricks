// =============================================================================
// Server integration tests — identity, health, streaming proxy (S4-E3)
// =============================================================================

import { expect, test } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:4000";

test.describe("Health check", () => {
	test("returns 200 with healthy status", async ({ request }) => {
		const res = await request.get(`${BASE_URL}/api/health`);
		expect(res.ok()).toBeTruthy();

		const body = await res.json();
		expect(body).toHaveProperty("healthy");
		expect(body).toHaveProperty("database");
		expect(body).toHaveProperty("agent");
	});
});

test.describe("Authentication", () => {
	test("returns 401 without X-Forwarded-User header", async ({ request }) => {
		const res = await request.get(`${BASE_URL}/api/conversations`, {
			headers: {},
		});
		expect(res.status()).toBe(401);

		const body = await res.json();
		expect(body.error.code).toBe("UNAUTHORIZED");
	});

	test("returns conversation list with valid user header", async ({
		request,
	}) => {
		const res = await request.get(`${BASE_URL}/api/conversations`, {
			headers: { "X-Forwarded-User": "test@example.com" },
		});
		expect(res.status()).toBe(200);

		const body = await res.json();
		expect(Array.isArray(body)).toBe(true);
	});
});

test.describe("Conversation CRUD", () => {
	const USER = "test@example.com";

	test("POST /api/conversations creates a conversation", async ({
		request,
	}) => {
		const res = await request.post(`${BASE_URL}/api/conversations`, {
			headers: { "X-Forwarded-User": USER },
			data: { title: "Test conversation" },
		});

		expect(res.status()).toBe(201);
		const body = await res.json();
		expect(body).toHaveProperty("id");
		expect(body.title).toBe("Test conversation");
		expect(body.owner).toBe(USER);

		const cleanup = await request.delete(
			`${BASE_URL}/api/conversations/${body.id}`,
			{ headers: { "X-Forwarded-User": USER } },
		);
		expect(cleanup.status()).toBe(204);
	});

	test("DELETE /api/conversations/:id returns 401 without auth", async ({
		request,
	}) => {
		const res = await request.delete(`${BASE_URL}/api/conversations/some-id`, {
			headers: {},
		});
		expect(res.status()).toBe(401);
	});
});

test.describe("Turn creation", () => {
	const USER = "test@example.com";

	test("POST turn without auth returns 401", async ({ request }) => {
		const res = await request.post(
			`${BASE_URL}/api/conversations/conv-id/turns`,
			{ headers: {}, data: { clientRequestId: "abc", userMessage: "hello" } },
		);
		expect(res.status()).toBe(401);
	});

	test("POST turn with auth validates request body", async ({ request }) => {
		const res = await request.post(
			`${BASE_URL}/api/conversations/conv-id/turns`,
			{
				headers: { "X-Forwarded-User": USER },
				data: { clientRequestId: "", userMessage: "" },
			},
		);
		expect(res.status()).toBe(400);
	});
});
