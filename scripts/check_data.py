"""Check stored conversation data to see what was persisted."""

import json
import subprocess

import psycopg

EP = "projects/ecommerce-agent-conversations/branches/production/endpoints/primary"

h = json.loads(
    subprocess.run(
        [
            "databricks",
            "postgres",
            "get-endpoint",
            EP,
            "--profile",
            "Ecommerce-Agent",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
)["status"]["hosts"]["host"]

t = json.loads(
    subprocess.run(
        [
            "databricks",
            "postgres",
            "generate-database-credential",
            EP,
            "--profile",
            "Ecommerce-Agent",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
)["token"]

conn = psycopg.connect(
    host=h,
    user="trietlm0306@gmail.com",
    password=t,
    dbname="databricks_postgres",
    sslmode="require",
    options="-c search_path=conversations",
)
cur = conn.cursor()

print("=== CONVERSATIONS ===")
cur.execute(
    "SELECT id, owner, title, created_at FROM conversations ORDER BY created_at DESC"
)
for r in cur.fetchall():
    print(f"  {r[0]}: owner={r[1]} title='{r[2]}' created={r[3]}")

print("\n=== TURNS ===")
cur.execute(
    "SELECT id, conversation_id, sequence, status, mlflow_trace_id FROM turns ORDER BY sequence ASC"
)
for r in cur.fetchall():
    print(f"  turn={r[2]} conv={str(r[1])[:8]} status={r[3]} trace={r[4] or '-'}")

print("\n=== ITEMS (ordered) ===")
cur.execute("""
    SELECT ci.sequence, ci.item_type, ci.role,
           substring(ci.payload::text, 1, 120) as payload_preview
    FROM conversation_items ci
    JOIN turns t ON t.id = ci.turn_id
    ORDER BY ci.sequence ASC
""")
for r in cur.fetchall():
    print(f"  seq={r[0]} type={r[1]} role={r[2]} payload={r[3]}")

print(f"\nTotal items: {cur.rowcount}")

cur.close()
conn.close()
