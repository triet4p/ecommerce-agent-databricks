// =============================================================================
// Health check routes (S4-C7)
// =============================================================================
// Exposes App readiness, Lakebase connectivity, and Agent App reachability
// without exposing resource details.

import { type Request, type Response, Router } from "express";
import type pg from "pg";
import { getAgentAppUrl, getAuthHeaders } from "../lib/oauth.js";

export interface HealthStatus {
	healthy: boolean;
	database: boolean;
	agent: boolean;
}

type AgentProbe = () => Promise<boolean>;
interface HealthPool {
	query(text: string): Promise<{ rows: Array<{ ok?: number }> }>;
}

async function probeAgent(): Promise<boolean> {
	try {
		const url = await getAgentAppUrl();
		const response = await fetch(`${url}/api/health`, {
			headers: await getAuthHeaders(),
			signal: AbortSignal.timeout(5_000),
		});
		return response.ok;
	} catch {
		return false;
	}
}

export async function evaluateHealth(
	pool: HealthPool,
	agentProbe: AgentProbe = probeAgent,
): Promise<HealthStatus> {
	let database = false;
	try {
		const dbRes = await pool.query("SELECT 1 AS ok");
		database = dbRes.rows[0]?.ok === 1;
	} catch {
		database = false;
	}

	const agent = await agentProbe().catch(() => false);
	return {
		healthy: database && agent,
		database,
		agent,
	};
}

export function createHealthRoutes(pool: pg.Pool): Router {
	const router = Router();

	// GET /api/health
	router.get("/", async (_req: Request, res: Response) => {
		const status = await evaluateHealth(pool);
		res.status(status.healthy ? 200 : 503).json(status);
	});

	return router;
}
