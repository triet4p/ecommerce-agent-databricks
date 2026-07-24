// =============================================================================
// Playwright E2E tests — streaming, tool use, history, navigation (S4-E4, S4-E5)
// =============================================================================

import { expect, test } from "@playwright/test";

test.describe("Chat UI basics", () => {
	test("shows empty state message on root", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByText("What would you like to know?")).toBeVisible();
	});

	test("has a composer input", async ({ page }) => {
		await page.goto("/");
		const input = page.getByPlaceholder("Ask about orders, policies...");
		await expect(input).toBeVisible();
	});
});

test.describe("Navigation", () => {
	test("sidebar toggles with Ctrl+\\", async ({ page }) => {
		await page.goto("/");
		const sidebar = page.locator('[aria-label="Conversations sidebar"]');

		// Sidebar should be visible initially
		await expect(sidebar).toBeVisible();

		// Toggle with Ctrl+Backslash
		await page.keyboard.press("Control+\\");
		await expect(sidebar).not.toBeVisible();

		// Toggle again
		await page.keyboard.press("Control+\\");
		await expect(sidebar).toBeVisible();
	});

	test("new conversation button is visible", async ({ page }) => {
		await page.goto("/");
		const newBtn = page.locator('[aria-label="New conversation"]');
		await expect(newBtn).toBeVisible();
	});
});

test.describe("Composer", () => {
	test("send button is disabled when input is empty", async ({ page }) => {
		await page.goto("/");
		const sendBtn = page.locator('[aria-label="Send message"]');
		await expect(sendBtn).toBeDisabled();
	});

	test("composer accepts text input", async ({ page }) => {
		await page.goto("/");
		const input = page.getByPlaceholder("Ask about orders, policies...");
		await input.fill("What is my order status?");
		await expect(input).toHaveValue("What is my order status?");
		const sendBtn = page.locator('[aria-label="Send message"]');
		await expect(sendBtn).toBeEnabled();
	});
});
