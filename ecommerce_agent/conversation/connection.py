"""Lakebase Postgres connection management with OAuth credential rotation.

The Databricks Apps runtime injects ``PGHOST``, ``PGDATABASE``, ``PGUSER``,
``PGPORT``, and ``PGSSLMODE`` when a postgres resource is bound.  The runtime
does **not** inject a password — the app must call the Databricks SDK's
``postgres.generate_database_credential()`` to obtain a short-lived OAuth token
for each connection.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from databricks.sdk import WorkspaceClient
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pool configuration
# ---------------------------------------------------------------------------

_MIN_CONNECTIONS = 1
_MAX_CONNECTIONS = 5
_CONNECTION_TIMEOUT_S = 120
_CONNECT_TIMEOUT_S = 60
_IDLE_TIMEOUT_S = 300
_MAX_LIFETIME_S = 1800


class LakebaseConnectionError(Exception):
    """Raised when Lakebase connection configuration is incomplete or fails."""


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def _get_connection_params() -> dict[str, str]:
    """Read connection parameters from env vars injected by the runtime."""
    host = os.environ.get("PGHOST") or os.environ.get("LAKEBASE_LOCAL_HOST")
    dbname = os.environ.get("PGDATABASE") or os.environ.get("LAKEBASE_LOCAL_DATABASE")
    user = os.environ.get("PGUSER") or os.environ.get("LAKEBASE_LOCAL_USER")
    port = os.environ.get("PGPORT") or os.environ.get("LAKEBASE_LOCAL_PORT", "5432")

    missing = [
        k
        for k, v in [("PGHOST", host), ("PGDATABASE", dbname), ("PGUSER", user)]
        if not v
    ]
    if missing:
        raise LakebaseConnectionError(
            f"Missing Lakebase connection env vars: {', '.join(missing)}. "
            "Bind a postgres resource. For local dev set "
            "LAKEBASE_LOCAL_HOST, LAKEBASE_LOCAL_DATABASE, LAKEBASE_LOCAL_USER."
        )
    return {"host": host, "dbname": dbname, "user": user, "port": port}


# ---------------------------------------------------------------------------
# Token generation — cached WorkspaceClient + async wrapper
# ---------------------------------------------------------------------------
# WorkspaceClient is created once at module level (synchronous) so it has a
# chance to initialise its auth outside of any background event-loop thread.

_WORKSPACE_CLIENT: WorkspaceClient | None = None


def _get_ws() -> WorkspaceClient:
    global _WORKSPACE_CLIENT
    if _WORKSPACE_CLIENT is None:
        _WORKSPACE_CLIENT = WorkspaceClient()
    return _WORKSPACE_CLIENT


async def _generate_token() -> str:
    """Generate a fresh OAuth database credential.

    Runs the synchronous SDK call in a thread executor so it doesn't block
    the async event loop on the background thread.
    """
    endpoint = os.environ.get("LAKEBASE_ENDPOINT")
    if not endpoint:
        raise LakebaseConnectionError(
            "Missing LAKEBASE_ENDPOINT. Bind a postgres resource or set the "
            "endpoint explicitly for local development."
        )
    logger.info("Generating Lakebase OAuth database credential")
    loop = asyncio.get_running_loop()
    ws = _get_ws()
    try:
        cred = await loop.run_in_executor(
            None,
            lambda: ws.postgres.generate_database_credential(endpoint=endpoint),
        )
        logger.info("Lakebase OAuth database credential generated")
        return cred.token
    except Exception as exc:
        logger.warning(
            "Lakebase OAuth database credential generation failed: %s",
            type(exc).__name__,
        )
        raise


# ---------------------------------------------------------------------------
# Pool factory
# ---------------------------------------------------------------------------


class _LakebasePool(AsyncConnectionPool):
    """Pool that generates a fresh OAuth token per connection.

    Overrides ``_resolve_kwargs`` to inject the token as the password on
    every new connection.  The base ``_connect()`` handles all bookkeeping
    (``_pool``, ``_created_at``, ``_expire_at``, configure hook, stats).
    """

    async def _resolve_conninfo(self) -> str:
        pg = _get_connection_params()
        logger.info("Lakebase connection parameters resolved")
        return f"host={pg['host']} port={pg['port']} dbname={pg['dbname']} user={pg['user']}"

    async def _resolve_kwargs(self) -> dict[str, Any]:
        token = await _generate_token()
        logger.info("Opening Lakebase connection")
        return {
            "password": token,
            "connect_timeout": _CONNECT_TIMEOUT_S,
            "sslmode": "require",
            "options": "-c search_path=conversations,$user,public",
        }


def create_pool() -> AsyncConnectionPool:
    """Create a bounded async Postgres connection pool for Lakebase."""
    _get_connection_params()
    logger.info("Creating Lakebase connection pool")
    return _LakebasePool(
        conninfo="",  # _resolve_conninfo builds the real conninfo per-connect
        min_size=_MIN_CONNECTIONS,
        max_size=_MAX_CONNECTIONS,
        timeout=_CONNECTION_TIMEOUT_S,
        max_idle=_IDLE_TIMEOUT_S,
        max_lifetime=_MAX_LIFETIME_S,
        open=False,
    )


@asynccontextmanager
async def managed_pool() -> AsyncGenerator[AsyncConnectionPool, None]:
    """Context manager that creates, opens, and closes a connection pool."""
    pool = create_pool()
    try:
        await pool.open()
        yield pool
    finally:
        await pool.close()


async def verify_connectivity(pool: AsyncConnectionPool) -> bool:
    """Verify that the pool can establish a database connection."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            row = await cur.fetchone()
            return row is not None and row[0] == 1
