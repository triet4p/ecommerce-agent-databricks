"""Trusted end-user identity handling for conversation server boundaries.

Only the Databricks-injected ``X-Forwarded-User`` header is accepted.  A
browser request body, query parameter, or fallback placeholder is never an
authority for ownership.
"""

from __future__ import annotations

from collections.abc import Mapping


class TrustedIdentityError(ValueError):
    """Raised when a request lacks a usable Databricks forwarded identity."""


def normalize_owner(value: str) -> str:
    """Return the canonical owner value used by every persistence operation."""
    owner = value.strip().casefold()
    if not owner or owner == "unknown@unknown" or len(owner) > 255:
        raise TrustedIdentityError(
            "A valid trusted Databricks user identity is required"
        )
    return owner


def trusted_owner_from_headers(headers: Mapping[str, str]) -> str:
    """Extract identity from trusted server-side headers, case-insensitively."""
    for key, value in headers.items():
        if key.casefold() == "x-forwarded-user":
            return normalize_owner(value)
    raise TrustedIdentityError("Missing X-Forwarded-User trusted header")
