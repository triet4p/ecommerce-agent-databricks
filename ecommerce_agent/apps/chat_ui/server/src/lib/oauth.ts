// =============================================================================
// App-to-App OAuth client for the Agent App (S4-C3)
// =============================================================================
// The Chat UI server authenticates to the Agent App using Databricks
// App-to-App OAuth. The browser never receives the downstream token.
//
// In Databricks Apps, the SDK authenticates via the injected service
// principal environment. In local development, it uses the configured
// profile or DATABRICKS_HOST/DATABRICKS_TOKEN.

import { env } from "../env.js";
import { getWorkspaceAccessToken, workspaceFetch } from "./workspace-auth.js";

/**
 * Resolve the Agent App URL from the Databricks workspace.
 * Uses environment variable AGENT_APP_NAME to look up the app.
 */

let _agentAppUrl: string | null = null;

export async function getAgentAppUrl(): Promise<string> {
	if (_agentAppUrl) return _agentAppUrl;

	const response = await workspaceFetch(
		`/api/2.0/apps/${encodeURIComponent(env.AGENT_APP_NAME)}`,
	);
	if (!response.ok) {
		throw new Error(`Agent App lookup failed with status ${response.status}`);
	}
	const app = (await response.json()) as { url?: string };
	if (!app.url) {
		throw new Error("Agent App lookup returned no URL");
	}
	_agentAppUrl = app.url;
	return _agentAppUrl;
}

/**
 * Get OAuth headers for the Agent App request.
 * In Databricks Apps, the SDK handles authentication automatically.
 * For now, we use bearer token-based authentication.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
	return {
		Authorization: `Bearer ${await getWorkspaceAccessToken()}`,
	};
}
