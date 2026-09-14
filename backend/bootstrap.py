"""Schema migrations and application-role grants, run in an admin Fargate task."""
import json
import os
import boto3
from psycopg import sql
from backend.db import connection
from backend.migrate import migrate

def main():
    migrate(); secrets=boto3.client("secretsmanager")
    with connection() as conn:
        for env,role in (("API_SECRET_ARN","api_reader"),("INGEST_SECRET_ARN","etl_writer")):
            password=json.loads(secrets.get_secret_value(SecretId=os.environ[env])["SecretString"])["password"]
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(role,)).fetchone():
                conn.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role)))
            conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role),sql.Literal(password)))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA market TO {}").format(sql.Identifier(role)))
        conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA market TO api_reader")
        conn.execute("REVOKE ALL ON market.ingestion_runs, market.schema_migrations FROM api_reader")
        conn.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA market TO etl_writer")
        conn.execute("REVOKE ALL ON market.schema_migrations FROM etl_writer")
        conn.execute("ALTER ROLE api_reader SET statement_timeout='8s'")
        conn.execute("ALTER ROLE api_reader CONNECTION LIMIT 8")
        conn.execute("ALTER ROLE etl_writer CONNECTION LIMIT 5")
    print("Schema and application roles are ready")

if __name__=="__main__": main()
