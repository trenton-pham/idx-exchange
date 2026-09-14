"""Transactional, versioned publication. Staging exists only within the transaction."""
import math
from datetime import date
from uuid import uuid4

from psycopg import sql
from backend.db import connection
from backend.retention import window

FACT_COLUMNS = ["kind", "listing_key", "month", "county", "city", "zip", "subtype",
                "close_price", "days_on_market", "price_sqft", "price_ratio",
                "agent_id", "agent_name", "office_id", "office_name", "grid_lat", "grid_lng", "modified_at"]


def publish(rows, mortgage, end: date, *, dataset_id=None, demo=False, before_activate=None):
    start, end = window(end)
    version = str(dataset_id or uuid4())
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(812402)")
        state = conn.execute("SELECT * FROM market.state FOR UPDATE").fetchone()
        if conn.execute("SELECT 1 FROM market.datasets WHERE id=%s", (version,)).fetchone():
            if str(state["active"]) != version:
                raise ValueError("Dataset ID already belongs to a different publication")
            return version
        if state["active"]:
            active = conn.execute("SELECT window_end FROM market.datasets WHERE id=%s", (state["active"],)).fetchone()
            if end < active["window_end"]:
                raise ValueError("Use rollback rather than publishing an older reporting window")
        conn.execute("INSERT INTO market.datasets(id,window_start,window_end,demo) VALUES (%s,%s,%s,%s)", (version,start,end,demo))
        count = 0
        with conn.cursor().copy(sql.SQL("COPY market.facts (dataset,{}) FROM STDIN").format(sql.SQL(',').join(map(sql.Identifier,FACT_COLUMNS)))) as copy:
            for row in rows:
                if not start <= row["month"] <= end:
                    continue
                values = [row.get(key) for key in FACT_COLUMNS]
                if any(isinstance(v, float) and not math.isfinite(v) for v in values):
                    raise ValueError("Non-finite metric in candidate publication")
                copy.write_row([version, *values])
                count += 1
        if not count:
            raise ValueError("Refusing an empty publication")
        with conn.cursor().copy("COPY market.mortgage(dataset,month,rate) FROM STDIN") as copy:
            for month, rate in mortgage:
                if start <= month <= end:
                    copy.write_row((version,month,rate))
        conn.execute("INSERT INTO market.geographies SELECT DISTINCT dataset,county,city,zip,subtype FROM market.facts WHERE dataset=%s", (version,))
        conn.execute("""INSERT INTO market.monthly_aggregates
            SELECT dataset,month,COALESCE(county,'__state__'), jsonb_build_object(
                'new_listings',count(*) FILTER(WHERE kind='listing'),
                'closed_sales',count(*) FILTER(WHERE kind='sold'),
                'median_price',percentile_cont(0.5) WITHIN GROUP(ORDER BY close_price) FILTER(WHERE kind='sold'),
                'days_on_market',avg(days_on_market) FILTER(WHERE kind='sold'),
                'price_sqft',avg(price_sqft) FILTER(WHERE kind='sold'),
                'price_ratio',avg(price_ratio) FILTER(WHERE kind='sold'))
            FROM market.facts WHERE dataset=%s GROUP BY GROUPING SETS ((dataset,month,county),(dataset,month))""", (version,))
        for entity in ("agent", "office"):
            conn.execute(sql.SQL("""INSERT INTO market.competitive_aggregates
                SELECT dataset,month,%s,{id},count(*),sum(close_price) FROM market.facts
                WHERE dataset=%s AND kind='sold' GROUP BY dataset,month,{id}""").format(id=sql.Identifier(entity+"_id")), (entity,version))
        if before_activate:
            before_activate(conn)
        previous = state["active"]
        conn.execute("UPDATE market.state SET active=%s,previous=%s", (version,previous))
        conn.execute("DELETE FROM market.datasets WHERE id<>%s AND id IS DISTINCT FROM %s", (version,previous))
        for table in ("facts", "mortgage", "monthly_aggregates", "competitive_aggregates"):
            conn.execute(sql.SQL("DELETE FROM market.{} WHERE month < %s OR month > %s").format(sql.Identifier(table)), (start,end))
        if previous:
            old = conn.execute("SELECT window_end FROM market.datasets WHERE id=%s", (previous,)).fetchone()
            if old["window_end"] < start:
                conn.execute("UPDATE market.state SET previous=NULL")
                conn.execute("DELETE FROM market.datasets WHERE id=%s", (previous,))
            else:
                conn.execute("UPDATE market.datasets SET window_start=GREATEST(window_start,%s) WHERE id=%s", (start,previous))
                conn.execute("DELETE FROM market.geographies WHERE dataset=%s", (previous,))
                conn.execute("INSERT INTO market.geographies SELECT DISTINCT dataset,county,city,zip,subtype FROM market.facts WHERE dataset=%s", (previous,))
    return version


def rollback():
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(812402)")
        state = conn.execute("SELECT * FROM market.state FOR UPDATE").fetchone()
        if not state["previous"]:
            raise ValueError("No previous dataset is available")
        conn.execute("UPDATE market.state SET active=previous,previous=active")
        return str(state["previous"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["rollback"])
    parser.parse_args()
    print(rollback())
