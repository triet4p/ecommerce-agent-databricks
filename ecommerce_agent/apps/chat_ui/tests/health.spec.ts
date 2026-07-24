import { EventEmitter } from "node:events";
import { expect, test } from "@playwright/test";
import { evaluateHealth } from "../server/src/routes/health";
import {
	type BackpressureResponse,
	writeWithBackpressure,
} from "../server/src/routes/turns";

function poolReturning(ok: boolean) {
	return {
		query: async () => ({ rows: [{ ok: ok ? 1 : 0 }] }),
	};
}

test.describe("readiness policy", () => {
	test("is healthy only when database and Agent are healthy", async () => {
		await expect(
			evaluateHealth(poolReturning(true), async () => true),
		).resolves.toEqual({
			healthy: true,
			database: true,
			agent: true,
		});
		await expect(
			evaluateHealth(poolReturning(true), async () => false),
		).resolves.toEqual({
			healthy: false,
			database: true,
			agent: false,
		});
		await expect(
			evaluateHealth(poolReturning(false), async () => true),
		).resolves.toEqual({
			healthy: false,
			database: false,
			agent: true,
		});
	});

	test("treats database and Agent probe errors as unavailable", async () => {
		const failingPool = {
			query: async () => {
				throw new Error("database unavailable");
			},
		};
		await expect(
			evaluateHealth(failingPool, async () => {
				throw new Error("Agent unavailable");
			}),
		).resolves.toEqual({
			healthy: false,
			database: false,
			agent: false,
		});
	});
});

class FakeResponse extends EventEmitter implements BackpressureResponse {
	destroyed = false;
	writableEnded = false;
	shouldDrain = false;

	write(): boolean {
		return !this.shouldDrain;
	}
}

test.describe("stream backpressure", () => {
	test("waits for drain before resolving a buffered write", async () => {
		const response = new FakeResponse();
		response.shouldDrain = true;
		let resolved = false;
		const write = writeWithBackpressure(response, "chunk").then(() => {
			resolved = true;
		});

		await Promise.resolve();
		expect(resolved).toBe(false);
		response.emit("drain");
		await write;
		expect(resolved).toBe(true);
	});

	test("rejects when the downstream closes before drain", async () => {
		const response = new FakeResponse();
		response.shouldDrain = true;
		const write = writeWithBackpressure(response, "chunk");
		response.destroyed = true;
		response.emit("close");
		await expect(write).rejects.toThrow("Client disconnected");
	});
});
