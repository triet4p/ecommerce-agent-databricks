"""Clean up all test data from Lakebase conversations schema."""
import subprocess, json, psycopg

EP = "projects/ecommerce-agent-conversations/branches/production/endpoints/primary"

h = json.loads(subprocess.run(
    ["databricks", "postgres", "get-endpoint", EP, "--profile", "Ecommerce-Agent", "-o", "json"],
    capture_output=True, text=True, check=True
).stdout)["status"]["hosts"]["host"]

t = json.loads(subprocess.run(
    ["databricks", "postgres", "generate-database-credential", EP, "--profile", "Ecommerce-Agent", "-o", "json"],
    capture_output=True, text=True, check=True
).stdout)["token"]

conn = psycopg.connect(host=h, user="trietlm0306@gmail.com", password=t,
                       dbname="databricks_postgres", sslmode="require",
                       options="-c search_path=conversations")
conn.autocommit = True
cur = conn.cursor()

cur.execute("DELETE FROM conversation_items")
print(f"Deleted {cur.rowcount} items")
cur.execute("DELETE FROM turns")
print(f"Deleted {cur.rowcount} turns")
cur.execute("DELETE FROM conversations")
print(f"Deleted {cur.rowcount} conversations")

cur.close()
conn.close()
print("Cleanup complete")
