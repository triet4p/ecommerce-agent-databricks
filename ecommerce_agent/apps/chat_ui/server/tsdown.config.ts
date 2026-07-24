import { defineConfig } from "tsdown";

export default defineConfig({
	entry: ["./src/index.ts"],
	format: "esm",
	target: "node20",
	clean: true,
	dts: false,
	external: [
		"@databricks/databricks-sdk",
		"@ecommerce-agent/core",
		"cors",
		"dotenv",
		"express",
		"pg",
		"uuid",
		"zod",
	],
});
