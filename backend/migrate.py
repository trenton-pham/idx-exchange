"""Run using the migration role, never the public API role."""
from pathlib import Path
from backend.db import connection


def migrate():
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(812401)")
        conn.execute("CREATE SCHEMA IF NOT EXISTS market")
        conn.execute("CREATE TABLE IF NOT EXISTS market.schema_migrations (name text PRIMARY KEY, applied_at timestamptz DEFAULT now())")
        for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
            if not conn.execute("SELECT 1 FROM market.schema_migrations WHERE name=%s", (path.name,)).fetchone():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO market.schema_migrations(name) VALUES (%s)", (path.name,))


if __name__ == "__main__":
    migrate()
