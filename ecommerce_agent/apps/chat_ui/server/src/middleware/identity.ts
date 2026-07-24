// =============================================================================
// Authenticated end-user extraction from trusted Databricks headers (S4-C1)
// =============================================================================
// Only the X-Forwarded-User header injected by Databricks Apps is accepted.
// A browser request body, query parameter, or fallback placeholder is never
// an authority for ownership. This mirrors the Sprint 3 identity.py.

import type { NextFunction, Request, Response } from "express";

export class TrustedIdentityError extends Error {
	constructor(message = "Missing X-Forwarded-User trusted header") {
		super(message);
		this.name = "TrustedIdentityError";
	}
}

/**
 * Extract the authenticated end-user identity from trusted server-side
 * headers. The X-Forwarded-User header is injected by Databricks Apps and
 * is the ONLY trusted source.
 */
export function extractUserFromHeaders(
	headers: Record<string, string | string[] | undefined>,
): string {
	for (const [key, value] of Object.entries(headers)) {
		if (key.toLowerCase() === "x-forwarded-user") {
			const val = Array.isArray(value) ? value[0] : value;
			if (val) return normalizeOwner(val);
		}
	}
	throw new TrustedIdentityError();
}

/**
 * Normalize an owner value to its canonical form.
 */
export function normalizeOwner(value: string): string {
	const owner = value.trim().toLowerCase();
	if (!owner || owner === "unknown@unknown" || owner.length > 255) {
		throw new TrustedIdentityError(
			"A valid trusted Databricks user identity is required",
		);
	}
	return owner;
}

/**
 * Express middleware that extracts the user identity from the
 * X-Forwarded-User header and attaches it to the request.
 */
export function identityMiddleware(
	req: Request,
	_res: Response,
	next: NextFunction,
): void {
	try {
		const user = extractUserFromHeaders(
			req.headers as Record<string, string | string[] | undefined>,
		);
		req.user = user;
		next();
	} catch (err) {
		if (err instanceof TrustedIdentityError) {
			_res.status(401).json({
				error: {
					code: "UNAUTHORIZED",
					message: err.message,
				},
			});
			return;
		}
		throw err;
	}
}
