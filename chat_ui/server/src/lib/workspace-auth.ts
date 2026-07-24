import { env } from "../env.js";

interface OAuthTokenResponse {
	access_token: string;
	expires_in?: number;
}

let cachedToken: { value: string; expiresAt: number } | null = null;

function workspaceHost(): string {
	if (!env.DATABRICKS_HOST) {
		throw new Error("DATABRICKS_HOST is required");
	}
	const host = env.DATABRICKS_HOST.replace(/\/+$/, "");
	return /^https?:\/\//i.test(host) ? host : `https://${host}`;
}

export async function getWorkspaceAccessToken(): Promise<string> {
	if (env.DATABRICKS_TOKEN) {
		return env.DATABRICKS_TOKEN;
	}

	const now = Date.now();
	if (cachedToken && cachedToken.expiresAt - 60_000 > now) {
		return cachedToken.value;
	}

	if (!env.DATABRICKS_CLIENT_ID || !env.DATABRICKS_CLIENT_SECRET) {
		throw new Error(
			"Databricks OAuth credentials are unavailable in the App runtime",
		);
	}

	const basic = Buffer.from(
		`${env.DATABRICKS_CLIENT_ID}:${env.DATABRICKS_CLIENT_SECRET}`,
	).toString("base64");
	const response = await fetch(`${workspaceHost()}/oidc/v1/token`, {
		method: "POST",
		headers: {
			Authorization: `Basic ${basic}`,
			"Content-Type": "application/x-www-form-urlencoded",
		},
		body: new URLSearchParams({
			grant_type: "client_credentials",
			scope: "all-apis",
		}),
	});

	if (!response.ok) {
		throw new Error(`Databricks OAuth failed with status ${response.status}`);
	}

	const token = (await response.json()) as OAuthTokenResponse;
	if (!token.access_token) {
		throw new Error(
			"Databricks OAuth response did not contain an access token",
		);
	}

	cachedToken = {
		value: token.access_token,
		expiresAt: now + (token.expires_in ?? 3600) * 1000,
	};
	return cachedToken.value;
}

export async function workspaceFetch(
	path: string,
	init: RequestInit = {},
): Promise<Response> {
	const token = await getWorkspaceAccessToken();
	const headers = new Headers(init.headers);
	headers.set("Authorization", `Bearer ${token}`);
	return fetch(`${workspaceHost()}${path}`, { ...init, headers });
}
