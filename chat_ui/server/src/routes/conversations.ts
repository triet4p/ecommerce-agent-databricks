// =============================================================================
// Conversation routes (S4-C2, S4-C5)
// =============================================================================

import { type Request, type Response, Router } from "express";
import { z } from "zod";
import type { ConversationRepository } from "../lib/conversation.js";

export function createConversationRoutes(repo: ConversationRepository): Router {
	const router = Router();

	// GET /api/conversations — list
	router.get("/", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const conversations = await repo.listConversations(user);
			res.json(conversations);
		} catch (err) {
			console.error("Failed to list conversations:", err);
			res.status(500).json({
				error: {
					code: "INTERNAL_ERROR",
					message: "Failed to list conversations",
				},
			});
		}
	});

	// POST /api/conversations — create
	router.post("/", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const schema = z.object({ title: z.string().optional() });
			const { title } = schema.parse(req.body);
			const conversation = await repo.createConversation(user, title);
			res.status(201).json(conversation);
		} catch (err) {
			if (err instanceof z.ZodError) {
				res.status(400).json({
					error: { code: "BAD_REQUEST", message: "Invalid request body" },
				});
				return;
			}
			console.error("Failed to create conversation:", err);
			res.status(500).json({
				error: {
					code: "INTERNAL_ERROR",
					message: "Failed to create conversation",
				},
			});
		}
	});

	// GET /api/conversations/:id — get with items
	router.get("/:id", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const id = req.params.id as string;
			const data = await repo.getConversationWithItems(id, user);
			res.json(data);
		} catch (err: unknown) {
			if (err instanceof Error && err.name === "ConversationNotFoundError") {
				res.status(404).json({
					error: { code: "NOT_FOUND", message: err.message },
				});
				return;
			}
			console.error("Failed to get conversation:", err);
			res.status(500).json({
				error: {
					code: "INTERNAL_ERROR",
					message: "Failed to get conversation",
				},
			});
		}
	});

	// PATCH /api/conversations/:id — update title
	router.patch("/:id", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const id = req.params.id as string;
			const schema = z.object({ title: z.string().min(1).max(500) });
			const { title } = schema.parse(req.body);
			const conversation = await repo.updateTitle(id, user, title);
			res.json(conversation);
		} catch (err) {
			if (err instanceof z.ZodError) {
				res.status(400).json({
					error: { code: "BAD_REQUEST", message: "Invalid title" },
				});
				return;
			}
			if (err instanceof Error && err.name === "ConversationNotFoundError") {
				res.status(404).json({
					error: { code: "NOT_FOUND", message: (err as Error).message },
				});
				return;
			}
			console.error("Failed to update conversation:", err);
			res.status(500).json({
				error: {
					code: "INTERNAL_ERROR",
					message: "Failed to update conversation",
				},
			});
		}
	});

	// DELETE /api/conversations/:id — soft delete
	router.delete("/:id", async (req: Request, res: Response) => {
		try {
			const user = req.user;
			const id = req.params.id as string;
			await repo.softDeleteConversation(id, user);
			res.status(204).end();
		} catch (err: unknown) {
			if (err instanceof Error && err.name === "ConversationNotFoundError") {
				res.status(404).json({
					error: { code: "NOT_FOUND", message: err.message },
				});
				return;
			}
			console.error("Failed to delete conversation:", err);
			res.status(500).json({
				error: {
					code: "INTERNAL_ERROR",
					message: "Failed to delete conversation",
				},
			});
		}
	});

	return router;
}
