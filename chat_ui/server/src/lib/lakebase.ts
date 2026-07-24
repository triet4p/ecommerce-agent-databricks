import pg from "pg";
import { env } from "../env.js";
import { workspaceFetch } from "./workspace-auth.js";

interface DatabaseCredential {
	token: string;
	expire_time?: string;
}

let cachedCredential: { value: string; expiresAt: number } | null = null;

async function getDatabasePassword(): Promise<string> {
	const now = Date.now();
	if (cachedCredential && cachedCredential.expiresAt - 300_000 > now) {
		return cachedCredential.value;
	}

	if (!env.LAKEBASE_ENDPOINT) {
		throw new Error(
			"Lakebase requires LAKEBASE_ENDPOINT from a bound postgres resource",
		);
	}

	const response = await workspaceFetch("/api/2.0/postgres/credentials", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ endpoint: env.LAKEBASE_ENDPOINT }),
	});
	if (!response.ok) {
		throw new Error(
			`Lakebase credential generation failed with status ${response.status}`,
		);
	}

	const credential = (await response.json()) as DatabaseCredential;
	if (!credential.token) {
		throw new Error("Lakebase credential response did not contain a token");
	}

	const parsedExpiry = credential.expire_time
		? Date.parse(credential.expire_time)
		: Number.NaN;
	cachedCredential = {
		value: credential.token,
		expiresAt: Number.isFinite(parsedExpiry)
			? parsedExpiry
			: now + 50 * 60 * 1000,
	};
	return cachedCredential.value;
}

export function createLakebasePool(): pg.Pool {
	const base = {
		max: 5,
		idleTimeoutMillis: 30_000,
		connectionTimeoutMillis: 120_000,
		maxLifetimeSeconds: 1800,
		options: "-c search_path=conversations,$user,public",
	};

	if (env.DATABASE_URL) {
		return new pg.Pool({
			...base,
			connectionString: env.DATABASE_URL,
		});
	}

	if (!env.PGHOST || !env.PGDATABASE || !env.PGUSER) {
		throw new Error(
			"Lakebase requires PGHOST, PGDATABASE, and PGUSER from a bound postgres resource",
		);
	}

	return new pg.Pool({
		...base,
		host: env.PGHOST,
		database: env.PGDATABASE,
		user: env.PGUSER,
		port: env.PGPORT,
		password: getDatabasePassword,
		ssl: env.PGSSLMODE === "disable" ? false : { rejectUnauthorized: false },
	});
}
