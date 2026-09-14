import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connection(*, readonly=False):
    """One bounded connection per request; Lambda concurrency bounds total load."""
    url = os.getenv("DATABASE_URL")
    kwargs = {} if url else {
        "host": os.environ["DB_HOST"], "dbname": os.getenv("DB_NAME", "housing"),
        "user": os.environ["DB_USER"], "password": os.environ["DB_PASSWORD"],
        "sslmode": "verify-full", "sslrootcert": os.getenv("DB_SSLROOTCERT", "/var/task/backend/rds-ca.pem"),
    }
    with psycopg.connect(url or "", **kwargs, connect_timeout=5, row_factory=dict_row) as conn:
        if readonly:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            conn.execute("SET LOCAL statement_timeout = '8s'")
        else:
            conn.execute("SET LOCAL lock_timeout = '10s'")
        yield conn
