import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
	esbuild: {
		jsx: "automatic",
	},
	resolve: {
		alias: {
			"@ecommerce-agent/core": path.resolve(
				__dirname,
				"packages/core/src/index.ts",
			),
		},
	},
	test: {
		environment: "jsdom",
		include: ["tests/components/**/*.test.{ts,tsx}"],
		setupFiles: ["./tests/components/setup.ts"],
	},
});
