"""Explicitly approved cleanup for legacy unowned conversation records.

This intentionally cannot delete arbitrary conversation data.  See
``docs/sprint-3b-data-cleanup.md`` for the required retention approval.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess

import psycopg


parser = argparse.ArgumentParser()
parser.add_argument("--confirm-legacy-unknown-cleanup", action="store_true")
parser.add_argument("--endpoint", default=os.environ.get("LAKEBASE_ENDPOINT"))
parser.add_argument("--profile", default=os.environ.get("DATABRICKS_CONFIG_PROFILE"))
parser.add_argument(
    "--database", default=os.environ.get("PGDATABASE", "databricks_postgres")
)
args = parser.parse_args()
if not args.confirm_legacy_unknown_cleanup:
    raise SystemExit(
        "Refusing cleanup: pass --confirm-legacy-unknown-cleanup after retention approval"
    )
if not args.endpoint:
    raise SystemExit("Set LAKEBASE_ENDPOINT or pass --endpoint")

profile_args = ["--profile", args.profile] if args.profile else []
endpoint = json.loads(
    subprocess.run(
        [
            "databricks",
            "postgres",
            "get-endpoint",
            args.endpoint,
            *profile_args,
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
)
credential = json.loads(
    subprocess.run(
        [
            "databricks",
            "postgres",
            "generate-database-credential",
            args.endpoint,
            *profile_args,
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
)
user = os.environ.get("PGUSER")
if not user:
    raise SystemExit("Set PGUSER; do not hard-code a personal workspace identity")

with psycopg.connect(
    host=endpoint["status"]["hosts"]["host"],
    user=user,
    password=credential["token"],
    dbname=args.database,
    sslmode="require",
    options="-c search_path=conversations",
) as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM conversations WHERE owner = %s", ("unknown@unknown",))
        print(f"Deleted {cur.rowcount} legacy unknown-owner conversations")
