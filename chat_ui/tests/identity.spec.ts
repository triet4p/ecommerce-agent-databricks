import type { AddressInfo } from "node:net";
import { expect, test } from "@playwright/test";
import express from "express";
import { identityMiddleware } from "../server/src/middleware/identity";
import { createIdentityRoutes } from "../server/src/routes/identity";

test("whoami returns trusted user and truthful execution identity", async () => {
	const app = express();
	app.use("/api", identityMiddleware);
	app.use("/api/whoami", createIdentityRoutes());
	const server = app.listen(0, "127.0.0.1");

	try {
		await new Promise<void>((resolve) => server.once("listening", resolve));
		const { port } = server.address() as AddressInfo;
		const response = await fetch(`http://127.0.0.1:${port}/api/whoami`, {
			headers: { "X-Forwarded-User": "  Owner@Example.com " },
		});

		expect(response.status).toBe(200);
		await expect(response.json()).resolves.toEqual({
			user: "owner@example.com",
			execution_identity: "app_service_principal",
		});
	} finally {
		await new Promise<void>((resolve, reject) =>
			server.close((error) => (error ? reject(error) : resolve())),
		);
	}
});
