import type pg from "pg";

const SCHEMA_VERSION = 2;

const VERSION_2_STATEMENTS = [
	"UPDATE conversations.conversation_items SET item_key = 'legacy:' || id::text WHERE item_key IS NULL OR item_key = ''",
	"ALTER TABLE conversations.conversations ADD CONSTRAINT conversations_owner_length CHECK (char_length(owner) BETWEEN 1 AND 255)",
	"ALTER TABLE conversations.turns ADD CONSTRAINT turns_sequence_positive CHECK (sequence > 0)",
	"ALTER TABLE conversations.turns ADD CONSTRAINT turns_status_valid CHECK (status IN ('active', 'completed', 'failed', 'cancelled'))",
	"ALTER TABLE conversations.turns ADD CONSTRAINT turns_request_id_length CHECK (char_length(client_request_id) BETWEEN 1 AND 255)",
	"ALTER TABLE conversations.turns ADD CONSTRAINT turns_trace_id_length CHECK (mlflow_trace_id IS NULL OR char_length(mlflow_trace_id) BETWEEN 1 AND 255)",
	"ALTER TABLE conversations.conversation_items ADD CONSTRAINT items_sequence_positive CHECK (sequence > 0)",
	"ALTER TABLE conversations.conversation_items ADD CONSTRAINT items_type_valid CHECK (item_type IN ('message', 'function_call', 'function_call_output'))",
	"ALTER TABLE conversations.conversation_items ADD CONSTRAINT items_role_valid CHECK (role IS NULL OR role IN ('user', 'assistant', 'tool', 'system'))",
	"ALTER TABLE conversations.conversation_items ADD CONSTRAINT items_key_required CHECK (char_length(item_key) BETWEEN 1 AND 255)",
	"ALTER TABLE conversations.conversation_items ADD CONSTRAINT items_turn_key_unique UNIQUE (turn_id, item_key)",
] as const;

export async function migrateConversationSchema(
	pool: pg.Pool,
): Promise<number> {
	const client = await pool.connect();
	try {
		await client.query("BEGIN");
		await client.query(
			"SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
			["ecommerce-agent-databricks-schema-migration"],
		);

		const versionResult = await client.query<{ version: number | null }>(
			"SELECT MAX(version) AS version FROM conversations._schema_version",
		);
		const currentVersion = versionResult.rows[0]?.version ?? 0;

		if (currentVersion < 2) {
			for (const statement of VERSION_2_STATEMENTS) {
				await client.query(statement);
			}
			await client.query(
				"INSERT INTO conversations._schema_version (version, applied_by) VALUES ($1, $2)",
				[2, "react-chat-ui"],
			);
		}

		await client.query("COMMIT");
		return SCHEMA_VERSION;
	} catch (error) {
		await client.query("ROLLBACK");
		throw error;
	} finally {
		client.release();
	}
}
