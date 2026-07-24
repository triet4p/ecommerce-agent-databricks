import { type Request, type Response, Router } from "express";

export function createIdentityRoutes(): Router {
	const router = Router();

	router.get("/", (req: Request, res: Response) => {
		res.json({
			user: req.user,
			execution_identity: "app_service_principal",
		});
	});

	return router;
}
