import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
	testDir: "./tests",
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: "html",
	use: {
		baseURL: process.env.BASE_URL || "http://127.0.0.1:3000",
		trace: "on-first-retry",
	},
	// Browser and credentialed server suites run against an explicit deployed or
	// developer-provided URL. The deterministic reducer tests remain runnable
	// without Lakebase, OAuth, or a local server process.
	testIgnore: [
		"components/**",
		...(process.env.BASE_URL ? [] : ["server.spec.ts", "e2e/**"]),
	],
	projects: [
		{
			name: "chromium",
			use: { ...devices["Desktop Chrome"] },
		},
	],
});
