// =============================================================================
// Sprint 3-adapted conversation repository for Node.js (S4-C2)
// =============================================================================
// Preserves the exact Sprint 3 schema and semantics:
// - Tables: conversations, turns, conversation_items
// - Owner-scoped operations via X-Forwarded-User
// - Idempotent turn creation via client_request_id
// - Status lifecycle: active -> completed/failed/cancelled
// - Soft-delete for conversations
// - Failed turns excluded from history replay
//
// This adapts the Sprint 3 Python repository to the Node server runtime
// without changing persisted schema or semantics.

import pg from "pg";
import { v4 as uuidv4 } from "uuid";

const { Pool } = pg;

const MAX_ITEMS_PER_TURN = 100;
const MAX_PAYLOAD_BYTES = 50_000;
const REDACTED_EXACT_KEYS = new Set([
	"authorization",
	"credential",
	"credentials",
	"password",
	"secret",
	"token",
	"access_token",
	"refresh_token",
	"api_key",
	"private_key",
	"reasoning_content",
	"reasoning",
	"x-forwarded-user",
	"cookie",
	"mlflow_trace_id",
]);
const REDACTED_SUFFIXES = [
	"_token",
	"_secret",
	"_password",
	"_api_key",
	"_credential",
	"_key",
];
const STRUCTURED_STRING_FIELDS = new Set(["arguments", "output"]);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Conversation {
	id: string;
	owner: string;
	title: string;
	created_at: string;
	updated_at: string;
	deleted_at: string | null;
}

export interface ConversationSummary {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
}

export type TurnStatus = "active" | "completed" | "failed" | "cancelled";

export interface Turn {
	id: string;
	conversation_id: string;
	client_request_id: string;
	sequence: number;
	status: TurnStatus;
	mlflow_trace_id: string | null;
	created_at: string;
	completed_at: string | null;
}

export interface ConversationItem {
	id: string;
	conversation_id: string;
	turn_id: string;
	sequence: number;
	item_type: string;
	role: string | null;
	payload: Record<string, unknown>;
	item_key: string | null;
	mlflow_trace_id: string | null;
	created_at: string;
}

// ---------------------------------------------------------------------------
// Repository
// ---------------------------------------------------------------------------

export class ConversationRepository {
	private pool: pg.Pool;

	constructor(pool: pg.Pool) {
		this.pool = pool;
	}

	// -- C1: Create conversation -----------------------------------------------

	async createConversation(
		owner: string,
		title = "New conversation",
	): Promise<Conversation> {
		const id = uuidv4();
		const now = new Date().toISOString();
		const truncatedTitle = title.slice(0, 500);

		const res = await this.pool.query(
			`INSERT INTO conversations (id, owner, title, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, owner, title, created_at, updated_at, deleted_at`,
			[id, owner, truncatedTitle, now, now],
		);

		return res.rows[0];
	}

	// -- C2: List conversations -------------------------------------------------

	async listConversations(
		owner: string,
		includeDeleted = false,
		limit = 50,
		offset = 0,
	): Promise<ConversationSummary[]> {
		let query = `SELECT id, title, created_at, updated_at
                 FROM conversations
                 WHERE owner = $1`;
		const params: Array<string | number> = [owner];

		if (!includeDeleted) {
			query += " AND deleted_at IS NULL";
		}

		query += " ORDER BY updated_at DESC LIMIT $2 OFFSET $3";
		params.push(limit, offset);

		const res = await this.pool.query(query, params);
		return res.rows;
	}

	// -- C3: Get conversation with items ----------------------------------------

	async getConversation(
		conversationId: string,
		owner: string,
	): Promise<Conversation> {
		const res = await this.pool.query(
			`SELECT id, owner, title, created_at, updated_at, deleted_at
       FROM conversations WHERE id = $1 AND owner = $2 AND deleted_at IS NULL`,
			[conversationId, owner],
		);

		if (res.rows.length === 0) {
			throw new ConversationNotFoundError(conversationId, owner);
		}

		return res.rows[0];
	}

	async getConversationWithItems(
		conversationId: string,
		owner: string,
	): Promise<{ conversation: Conversation; items: ConversationItem[] }> {
		const conversation = await this.getConversation(conversationId, owner);

		const res = await this.pool.query(
			`SELECT ci.id, ci.conversation_id, ci.turn_id, ci.sequence,
              ci.item_type, ci.role, ci.payload, ci.item_key, ci.created_at,
              t.mlflow_trace_id
       FROM conversation_items ci
       JOIN conversations c ON c.id = ci.conversation_id
       JOIN turns t ON t.id = ci.turn_id
       WHERE ci.conversation_id = $1 AND c.owner = $2 AND c.deleted_at IS NULL
       ORDER BY ci.sequence ASC`,
			[conversationId, owner],
		);

		return {
			conversation,
			items: res.rows.map((row) => ({
				...row,
				payload:
					typeof row.payload === "string"
						? JSON.parse(row.payload)
						: row.payload,
			})),
		};
	}

	// -- C4: Update title -------------------------------------------------------

	async updateTitle(
		conversationId: string,
		owner: string,
		title: string,
	): Promise<Conversation> {
		const truncated = title.slice(0, 500);
		const now = new Date().toISOString();

		const res = await this.pool.query(
			`UPDATE conversations SET title = $1, updated_at = $2
       WHERE id = $3 AND owner = $4 AND deleted_at IS NULL
       RETURNING id, owner, title, created_at, updated_at, deleted_at`,
			[truncated, now, conversationId, owner],
		);

		if (res.rows.length === 0) {
			throw new ConversationNotFoundError(conversationId, owner);
		}

		return res.rows[0];
	}

	// -- C5: Soft delete --------------------------------------------------------

	async softDeleteConversation(
		conversationId: string,
		owner: string,
	): Promise<void> {
		const now = new Date().toISOString();

		const res = await this.pool.query(
			`UPDATE conversations SET deleted_at = $1, updated_at = $2
       WHERE id = $3 AND owner = $4 AND deleted_at IS NULL`,
			[now, now, conversationId, owner],
		);

		if (res.rowCount === 0) {
			throw new ConversationNotFoundError(conversationId, owner);
		}
	}

	// -- C6: Idempotent turn creation -------------------------------------------

	async createTurn(
		conversationId: string,
		owner: string,
		clientRequestId: string,
	): Promise<Turn> {
		const client = await this.pool.connect();

		try {
			await client.query("BEGIN");

			// Verify ownership and lock the conversation
			const convRes = await client.query(
				`SELECT id FROM conversations
         WHERE id = $1 AND owner = $2 AND deleted_at IS NULL
         FOR UPDATE`,
				[conversationId, owner],
			);

			if (convRes.rows.length === 0) {
				await client.query("ROLLBACK");
				throw new ConversationNotFoundError(conversationId, owner);
			}

			// Allocate next sequence
			const seqRes = await client.query(
				`SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq
         FROM turns WHERE conversation_id = $1`,
				[conversationId],
			);
			const nextSeq = seqRes.rows[0].next_seq;

			// Try insert
			const turnId = uuidv4();
			const now = new Date().toISOString();

			const insertRes = await client.query(
				`INSERT INTO turns (id, conversation_id, client_request_id, sequence, status, created_at)
         VALUES ($1, $2, $3, $4, 'active', $5)
         ON CONFLICT (conversation_id, client_request_id) DO NOTHING
         RETURNING id, conversation_id, client_request_id, sequence, status,
                   mlflow_trace_id, created_at, completed_at`,
				[turnId, conversationId, clientRequestId, nextSeq, now],
			);

			let turn: Turn;
			if (insertRes.rows.length === 0) {
				// Idempotent: turn already exists, fetch it
				const existingRes = await client.query(
					`SELECT id, conversation_id, client_request_id, sequence, status,
                  mlflow_trace_id, created_at, completed_at
           FROM turns
           WHERE conversation_id = $1 AND client_request_id = $2`,
					[conversationId, clientRequestId],
				);
				turn = existingRes.rows[0];
			} else {
				turn = insertRes.rows[0];
			}

			// Touch conversation updated_at
			await client.query(
				"UPDATE conversations SET updated_at = $1 WHERE id = $2",
				[now, conversationId],
			);

			await client.query("COMMIT");
			return turn;
		} catch (err) {
			await client.query("ROLLBACK");
			throw err;
		} finally {
			client.release();
		}
	}

	// -- C7: Complete turn ------------------------------------------------------

	async completeTurn(
		turnId: string,
		conversationId: string,
		owner: string,
		items: Record<string, unknown>[],
		mlflowTraceId?: string | null,
		userMessage?: string | null,
	): Promise<Turn> {
		if (items.length > MAX_ITEMS_PER_TURN) {
			throw new PayloadLimitError(
				`A turn may persist at most ${MAX_ITEMS_PER_TURN} output items`,
			);
		}
		const client = await this.pool.connect();

		try {
			await client.query("BEGIN");

			// Lock owned conversation
			const convRes = await client.query(
				`SELECT id FROM conversations
         WHERE id = $1 AND owner = $2 AND deleted_at IS NULL
         FOR UPDATE`,
				[conversationId, owner],
			);

			if (convRes.rows.length === 0) {
				await client.query("ROLLBACK");
				throw new ConversationNotFoundError(conversationId, owner);
			}

			// Update turn to completed
			const now = new Date().toISOString();
			const turnRes = await client.query(
				`UPDATE turns SET status = 'completed', completed_at = $1,
                mlflow_trace_id = COALESCE($2, mlflow_trace_id)
         WHERE id = $3 AND conversation_id = $4 AND status = 'active'
         RETURNING id, conversation_id, client_request_id, sequence, status,
                   mlflow_trace_id, created_at, completed_at`,
				[now, mlflowTraceId ?? null, turnId, conversationId],
			);

			if (turnRes.rows.length === 0) {
				// Check if already completed
				const existingRes = await client.query(
					`SELECT t.id, t.conversation_id, t.client_request_id, t.sequence,
                  t.status, t.mlflow_trace_id, t.created_at, t.completed_at
	           FROM turns t JOIN conversations c ON c.id = t.conversation_id
	           WHERE t.id = $1 AND t.conversation_id = $2
	             AND c.owner = $3 AND c.deleted_at IS NULL`,
					[turnId, conversationId, owner],
				);
				if (
					existingRes.rows.length > 0 &&
					existingRes.rows[0].status === "completed"
				) {
					await client.query("COMMIT");
					return existingRes.rows[0];
				}
				await client.query("ROLLBACK");
				throw new Error(`Turn ${turnId} is not active`);
			}

			// Get next item sequence
			const seqRes = await client.query(
				`SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq
         FROM conversation_items WHERE conversation_id = $1`,
				[conversationId],
			);
			let nextItemSeq = seqRes.rows[0].next_seq;

			// Insert user message as first item if provided
			if (userMessage) {
				const payload = validatePayload({
					type: "message",
					role: "user",
					content: [{ type: "input_text", text: userMessage }],
				});
				await client.query(
					`INSERT INTO conversation_items
           (id, conversation_id, turn_id, sequence, item_type, role, payload, item_key)
           VALUES ($1, $2, $3, $4, 'message', 'user', $5::jsonb, 'message:user')`,
					[
						uuidv4(),
						conversationId,
						turnId,
						nextItemSeq,
						JSON.stringify(payload),
					],
				);
				nextItemSeq++;
			}

			// Insert output items
			for (let i = 0; i < items.length; i++) {
				const item = items[i];
				const itemType = inferItemType(item);
				const payload = JSON.stringify(validatePayload(item));
				const itemId =
					typeof item.id === "string"
						? item.id
						: typeof item.call_id === "string"
							? item.call_id
							: String(i);
				const itemKey = `${itemType}:${itemId}`;

				await client.query(
					`INSERT INTO conversation_items
           (id, conversation_id, turn_id, sequence, item_type, role, payload, item_key)
           VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
           ON CONFLICT (turn_id, item_key) DO NOTHING`,
					[
						uuidv4(),
						conversationId,
						turnId,
						nextItemSeq + i,
						itemType,
						typeof item.role === "string" ? item.role : null,
						payload,
						itemKey,
					],
				);
			}

			// Touch conversation
			await client.query(
				"UPDATE conversations SET updated_at = $1 WHERE id = $2",
				[now, conversationId],
			);

			await client.query("COMMIT");
			return turnRes.rows[0];
		} catch (err) {
			await client.query("ROLLBACK");
			throw err;
		} finally {
			client.release();
		}
	}

	// -- C8: Fail turn ----------------------------------------------------------

	async failTurn(
		turnId: string,
		conversationId: string,
		owner: string,
	): Promise<void> {
		const now = new Date().toISOString();

		const res = await this.pool.query(
			`UPDATE turns SET status = 'failed', completed_at = $1
       WHERE id = $2 AND conversation_id = $3 AND status = 'active'
       AND EXISTS (SELECT 1 FROM conversations c
                   WHERE c.id = $3 AND c.owner = $4 AND c.deleted_at IS NULL)`,
			[now, turnId, conversationId, owner],
		);

		if (
			res.rowCount === 0 &&
			!(await this.isOwnedTerminalTurn(turnId, conversationId, owner, "failed"))
		) {
			throw new Error(
				`Active turn ${turnId} not found for conversation ${conversationId}`,
			);
		}

		await this.touchConversation(conversationId);
	}

	// -- C9: Cancel turn --------------------------------------------------------

	async cancelTurn(
		turnId: string,
		conversationId: string,
		owner: string,
	): Promise<void> {
		const now = new Date().toISOString();

		const res = await this.pool.query(
			`UPDATE turns SET status = 'cancelled', completed_at = $1
       WHERE id = $2 AND conversation_id = $3 AND status = 'active'
       AND EXISTS (SELECT 1 FROM conversations c
                   WHERE c.id = $3 AND c.owner = $4 AND c.deleted_at IS NULL)`,
			[now, turnId, conversationId, owner],
		);

		if (
			res.rowCount === 0 &&
			!(await this.isOwnedTerminalTurn(
				turnId,
				conversationId,
				owner,
				"cancelled",
			))
		) {
			throw new Error(`Active turn ${turnId} not found`);
		}

		await this.touchConversation(conversationId);
	}

	// -- R1: Get replay items ---------------------------------------------------

	async getReplayItems(
		conversationId: string,
		owner: string,
	): Promise<ConversationItem[]> {
		const res = await this.pool.query(
			`SELECT ci.id, ci.conversation_id, ci.turn_id, ci.sequence,
              ci.item_type, ci.role, ci.payload, ci.item_key, ci.created_at
       FROM conversation_items ci
       JOIN conversations c ON c.id = ci.conversation_id
       JOIN turns t ON t.id = ci.turn_id
       WHERE ci.conversation_id = $1 AND c.owner = $2
         AND c.deleted_at IS NULL AND t.status = 'completed'
       ORDER BY ci.sequence ASC`,
			[conversationId, owner],
		);

		return res.rows.map((row) => ({
			...row,
			payload:
				typeof row.payload === "string" ? JSON.parse(row.payload) : row.payload,
		}));
	}

	// -- Helpers ----------------------------------------------------------------

	private async touchConversation(conversationId: string): Promise<void> {
		const now = new Date().toISOString();
		await this.pool.query(
			"UPDATE conversations SET updated_at = $1 WHERE id = $2",
			[now, conversationId],
		);
	}

	private async isOwnedTerminalTurn(
		turnId: string,
		conversationId: string,
		owner: string,
		status: "failed" | "cancelled",
	): Promise<boolean> {
		const res = await this.pool.query(
			`SELECT 1 FROM turns t JOIN conversations c ON c.id = t.conversation_id
			 WHERE t.id = $1 AND t.conversation_id = $2 AND t.status = $3
			   AND c.owner = $4 AND c.deleted_at IS NULL`,
			[turnId, conversationId, status, owner],
		);
		return res.rowCount === 1;
	}
}

// ---------------------------------------------------------------------------
// Exceptions
// ---------------------------------------------------------------------------

export class ConversationNotFoundError extends Error {
	constructor(conversationId: string, owner: string) {
		super(`Conversation ${conversationId} not found for owner ${owner}`);
		this.name = "ConversationNotFoundError";
	}
}

export class PayloadLimitError extends Error {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function inferItemType(item: Record<string, unknown>): string {
	const type = item.type as string;
	if (type === "message") return "message";
	if (type === "function_call") return "function_call";
	if (type === "function_call_output") return "function_call_output";
	return "message";
}

function validatePayload(
	payload: Record<string, unknown>,
): Record<string, unknown> {
	const sanitized = sanitizePayload(payload);
	if (
		Buffer.byteLength(JSON.stringify(sanitized), "utf8") > MAX_PAYLOAD_BYTES
	) {
		throw new PayloadLimitError(
			`Conversation item exceeds the ${MAX_PAYLOAD_BYTES}-byte safety limit`,
		);
	}
	return sanitized;
}

export function sanitizePayload(
	value: Record<string, unknown>,
): Record<string, unknown> {
	return sanitizeValue(value) as Record<string, unknown>;
}

function sanitizeValue(value: unknown): unknown {
	if (Array.isArray(value)) return value.map(sanitizeValue);
	if (typeof value !== "object" || value === null) return value;
	const sanitized: Record<string, unknown> = {};
	for (const [key, child] of Object.entries(value)) {
		const normalized = key.toLowerCase();
		if (
			REDACTED_EXACT_KEYS.has(normalized) ||
			REDACTED_SUFFIXES.some((suffix) => normalized.endsWith(suffix))
		) {
			sanitized[key] = "<redacted>";
		} else if (
			typeof child === "string" &&
			STRUCTURED_STRING_FIELDS.has(normalized)
		) {
			sanitized[key] = sanitizeStructuredString(child);
		} else {
			sanitized[key] = sanitizeValue(child);
		}
	}
	return sanitized;
}

function sanitizeStructuredString(value: string): string {
	try {
		const parsed: unknown = JSON.parse(value);
		if (typeof parsed === "object" && parsed !== null) {
			return JSON.stringify(sanitizeValue(parsed));
		}
	} catch {
		// Non-JSON tool values are valid opaque strings.
	}
	return value;
}
