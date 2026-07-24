// =============================================================================
// Server environment configuration (S4-C6)
// =============================================================================

import { z } from "zod";
import "dotenv/config";

const envSchema = z.object({
	// Server
	PORT: z.coerce.number().default(4000),
	DATABRICKS_APP_PORT: z.coerce.number().optional(),
	NODE_ENV: z.enum(["development", "production"]).default("development"),
	APP_RUNTIME: z.enum(["development", "production"]).default("development"),

	// Databricks
	DATABRICKS_HOST: z.string().optional(),
	DATABRICKS_TOKEN: z.string().optional(),
	DATABRICKS_CLIENT_ID: z.string().optional(),
	DATABRICKS_CLIENT_SECRET: z.string().optional(),
	DATABRICKS_CONFIG_PROFILE: z.string().default("Ecommerce-Agent"),

	// Agent App
	AGENT_APP_NAME: z.string().default("ecommerce-agent-app"),

	// Lakebase (Postgres)
	DATABASE_URL: z.string().optional(),
	PGHOST: z.string().optional(),
	PGDATABASE: z.string().optional(),
	PGUSER: z.string().optional(),
	PGPORT: z.coerce.number().default(5432),
	PGSSLMODE: z.string().default("require"),
	// Injected by the bound Lakebase resource. Never bake a workspace endpoint
	// into the deployable artifact, because endpoint names are environment-scoped.
	LAKEBASE_ENDPOINT: z.string().min(1).optional(),

	// Serving endpoint (for query)
	DATABRICKS_SERVING_ENDPOINT: z
		.string()
		.default("deepseek-v4-streaming-agent-lab"),
});

function loadEnv() {
	const parsed = envSchema.parse(process.env);
	return {
		...parsed,
		PORT: parsed.DATABRICKS_APP_PORT ?? parsed.PORT,
	};
}

export const env = loadEnv();
