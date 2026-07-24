import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import pg from "pg";
import {
	ConversationRepository,
	PayloadLimitError,
} from "../../server/src/lib/conversation";
import { migrateConversationSchema } from "../../server/src/lib/schema";

const required = [
	"S4B_PGHOST",
	"S4B_PGDATABASE",
	"S4B_PGUSER",
	"S4B_PGPASSWORD",
] as const;
const configured = required.every((name) => process.env[name]);

test.describe("isolated PostgreSQL repository", () => {
	test.skip(!configured, "isolated Lakebase credentials unavailable");

	test("proves sequencing, idempotency, isolation, redaction, and deletion", async () => {
		const pool = new pg.Pool({
			host: process.env.S4B_PGHOST,
			database: process.env.S4B_PGDATABASE,
			user: process.env.S4B_PGUSER,
			password: process.env.S4B_PGPASSWORD,
			ssl: { rejectUnauthorized: false },
			max: 12,
			options: "-c search_path=conversations,$user,public",
		});
		const repository = new ConversationRepository(pool);
		const owner = `node-s4b-${randomUUID()}@example.com`;
		const otherOwner = `node-other-${randomUUID()}@example.com`;

		try {
			await expect(migrateConversationSchema(pool)).resolves.toBe(2);
			const conversation = await repository.createConversation(
				owner,
				"S4B Node integration",
			);
			const turns = await Promise.all(
				Array.from({ length: 8 }, (_, index) =>
					repository.createTurn(
						conversation.id,
						owner,
						randomUUID().replace(String(index), "a"),
					),
				),
			);
			expect(
				turns.map((turn) => Number(turn.sequence)).sort((a, b) => a - b),
			).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);

			const requestId = randomUUID();
			const first = await repository.createTurn(
				conversation.id,
				owner,
				requestId,
			);
			const repeated = await repository.createTurn(
				conversation.id,
				owner,
				requestId,
			);
			expect(repeated.id).toBe(first.id);

			const output = [
				{
					type: "function_call",
					id: "fc-node-1",
					call_id: "call-node-1",
					name: "get_order_status",
					arguments: '{"order_id":"1","token":"secret"}',
					reasoning: "private",
				},
				{
					type: "function_call_output",
					call_id: "call-node-1",
					output: '{"status":"shipped","api_key":"secret"}',
				},
				{
					type: "message",
					id: "message-node-1",
					role: "assistant",
					content: [{ type: "output_text", text: "It shipped." }],
				},
			];
			await repository.completeTurn(
				first.id,
				conversation.id,
				owner,
				output,
				"trace-node-s4b",
				"Where is order 1?",
			);
			const repeatedCompletion = await repository.completeTurn(
				first.id,
				conversation.id,
				owner,
				[],
				"trace-node-s4b",
			);
			expect(repeatedCompletion.status).toBe("completed");

			await repository.failTurn(turns[0].id, conversation.id, owner);
			await repository.failTurn(turns[0].id, conversation.id, owner);
			await repository.cancelTurn(turns[1].id, conversation.id, owner);
			await repository.cancelTurn(turns[1].id, conversation.id, owner);

			await expect(
				repository.getConversation(conversation.id, otherOwner),
			).rejects.toThrow("not found");

			const replay = await repository.getReplayItems(conversation.id, owner);
			expect(replay.map((item) => item.item_type)).toEqual([
				"message",
				"function_call",
				"function_call_output",
				"message",
			]);
			const persisted = JSON.stringify(replay);
			expect(persisted).not.toContain("secret");
			expect(persisted).toContain("<redacted>");

			await expect(
				repository.completeTurn(
					turns[2].id,
					conversation.id,
					owner,
					Array.from({ length: 101 }, (_, index) => ({
						type: "message",
						id: String(index),
					})),
				),
			).rejects.toBeInstanceOf(PayloadLimitError);

			await repository.softDeleteConversation(conversation.id, owner);
			await expect(
				repository.getConversation(conversation.id, owner),
			).rejects.toThrow("not found");
			await expect(
				repository.createTurn(conversation.id, owner, randomUUID()),
			).rejects.toThrow("not found");
		} finally {
			await pool.query(
				"DELETE FROM conversations.conversations WHERE owner = $1",
				[owner],
			);
			await pool.end();
		}
	});
});
