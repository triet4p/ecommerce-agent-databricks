// =============================================================================
// Chat UI Server — Express.js with API routes and static file serving (S4-C6)
// =============================================================================
//
// In Databricks Apps (production), the Express server serves both the API
// and the production React build from client/dist/. In development, Vite's
// dev server proxies /api requests to this server.
//
// Architecture:
//   Browser → Chat UI Server (Express) → Agent App (via App-to-App OAuth)
//                ↓
//          Lakebase (Postgres via pg)

import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import { env } from "./env.js";
import { ConversationRepository } from "./lib/conversation.js";
import { createLakebasePool } from "./lib/lakebase.js";
import { migrateConversationSchema } from "./lib/schema.js";
import { identityMiddleware } from "./middleware/identity.js";
import { createConversationRoutes } from "./routes/conversations.js";
import { createHealthRoutes } from "./routes/health.js";
import { createIdentityRoutes } from "./routes/identity.js";
import { abortActiveStreams, createTurnRoutes } from "./routes/turns.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
	// -----------------------------------------------------------------------
	// PostgreSQL / Lakebase connection
	// -----------------------------------------------------------------------
	const pool = createLakebasePool();

	const schemaVersion = await migrateConversationSchema(pool);
	console.log(`[DB] Connected to Lakebase (schema v${schemaVersion})`);

	// -----------------------------------------------------------------------
	// Express app
	// -----------------------------------------------------------------------
	const app = express();
	app.use(express.json({ limit: "256kb" }));

	// Trust Databricks Apps proxy headers
	app.set("trust proxy", true);

	// Identity middleware (extracts X-Forwarded-User)
	app.use("/api", identityMiddleware);

	// -----------------------------------------------------------------------
	// Repository
	// -----------------------------------------------------------------------
	const repo = new ConversationRepository(pool);

	// -----------------------------------------------------------------------
	// Routes
	// -----------------------------------------------------------------------
	app.use("/api/conversations", createConversationRoutes(repo));
	app.use("/api/conversations/:id/turns", createTurnRoutes(repo));
	app.use("/api/health", createHealthRoutes(pool));
	app.use("/api/whoami", createIdentityRoutes());

	// -----------------------------------------------------------------------
	// Static file serving (production)
	// -----------------------------------------------------------------------
	if (env.APP_RUNTIME === "production") {
		const clientDist = path.resolve(__dirname, "../../client/dist");
		app.use(express.static(clientDist));

		// SPA fallback: serve index.html for all non-API routes
		app.get("*", (_req, res) => {
			res.sendFile(path.join(clientDist, "index.html"));
		});

		console.log(`[Server] Serving static files from ${clientDist}`);
	}

	// -----------------------------------------------------------------------
	// Start
	// -----------------------------------------------------------------------
	const server = app.listen(env.PORT, "0.0.0.0", () => {
		console.log(`[Server] Chat UI server running on port ${env.PORT}`);
		console.log(`[Server] Runtime: ${env.APP_RUNTIME}`);
	});

	// Graceful shutdown
	let shuttingDown = false;
	const shutdown = async (signal: string) => {
		if (shuttingDown) return;
		shuttingDown = true;
		console.log(`[Server] Shutting down after ${signal}...`);

		const forceExit = setTimeout(() => {
			console.error("[Server] Graceful shutdown deadline exceeded");
			process.exit(1);
		}, 12_000);
		forceExit.unref();

		abortActiveStreams();
		server.closeIdleConnections();
		const forceConnections = setTimeout(() => {
			server.closeAllConnections();
		}, 5_000);
		forceConnections.unref();

		const serverClosed = new Promise<void>((resolve, reject) => {
			server.close((error) => {
				if (error) reject(error);
				else resolve();
			});
		});

		const results = await Promise.allSettled([serverClosed, pool.end()]);
		clearTimeout(forceConnections);
		clearTimeout(forceExit);
		const failed = results.find(
			(result): result is PromiseRejectedResult => result.status === "rejected",
		);
		if (failed) {
			console.error("[Server] Graceful shutdown failed:", failed.reason);
			process.exit(1);
		}
		console.log("[Server] Shutdown complete");
		process.exit(0);
	};

	process.on("SIGTERM", () => void shutdown("SIGTERM"));
	process.on("SIGINT", () => void shutdown("SIGINT"));
}

main().catch((err) => {
	console.error("[Server] Fatal error:", err);
	process.exit(1);
});
