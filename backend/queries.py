from datetime import date
from fastapi import HTTPException
from psycopg import sql

from backend.models import Filters, Meta, Metrics
from backend.retention import months, parse_month, shift_month

METRICS_SQL = """count(*) FILTER(WHERE kind='listing') AS new_listings,
    count(*) FILTER(WHERE kind='sold') AS closed_sales,
    percentile_cont(0.5) WITHIN GROUP(ORDER BY close_price) FILTER(WHERE kind='sold') AS median_price,
    avg(days_on_market) FILTER(WHERE kind='sold') AS days_on_market,
    avg(price_sqft) FILTER(WHERE kind='sold') AS price_sqft,
    avg(price_ratio) FILTER(WHERE kind='sold') AS price_ratio,
    count(days_on_market) FILTER(WHERE kind='sold') AS days_sample,
    count(price_sqft) FILTER(WHERE kind='sold') AS sqft_sample,
    count(price_ratio) FILTER(WHERE kind='sold') AS ratio_sample"""


def metadata(conn, version=None):
    row = conn.execute("SELECT * FROM market.datasets WHERE id = COALESCE(%s::uuid,(SELECT active FROM market.state))", (version,)).fetchone()
    if not row:
        raise HTTPException(409 if version else 503, detail={"code":"version_unavailable" if version else "no_dataset", "message":"Refresh to load the current dataset." if version else "The first market update has not been published yet."})
    return Meta(version=str(row["id"]), start_month=row["window_start"].strftime("%Y-%m"), end_month=row["window_end"].strftime("%Y-%m"),
                published_at=row["published_at"].isoformat(), demo=row["demo"],
                months=[m.strftime("%Y-%m") for m in months(row["window_start"],row["window_end"])],
                source="Synthetic demonstration data" if row["demo"] else "CRMLS via Trestle")


def selected_month(filters: Filters, meta: Meta):
    month = filters.month or meta.end_month
    if month < meta.start_month or month > meta.end_month:
        raise HTTPException(416, detail={"code":"period_unavailable", "message":"This month is outside the retained reporting period.",
            "start_month":meta.start_month,"end_month":meta.end_month,"nearest_month":min(max(month,meta.start_month),meta.end_month)})
    return parse_month(month)


def where(filters: Filters, version, *, start=None, end=None, omit=None):
    parts, values = [sql.SQL("dataset=%s")], [version]
    for key in ("county","city","zip","subtype"):
        value = getattr(filters,key)
        if value and key != omit:
            parts.append(sql.SQL("{}=%s").format(sql.Identifier(key)))
            values.append(value)
    if start:
        parts.append(sql.SQL("month >= %s")); values.append(start)
    if end:
        parts.append(sql.SQL("month <= %s")); values.append(end)
    return sql.SQL(" AND ").join(parts), values


def metrics(conn, filters, version, month):
    clause, values = where(filters,version,start=month,end=month)
    row = conn.execute(sql.SQL("SELECT "+METRICS_SQL+" FROM market.facts WHERE {}").format(clause),values).fetchone()
    rate = conn.execute("SELECT rate FROM market.mortgage WHERE dataset=%s AND month=%s",(version,month)).fetchone()
    return Metrics(**row,mortgage_rate=rate["rate"] if rate else None)


def summary(conn, filters):
    meta=metadata(conn,filters.version); month=selected_month(filters,meta)
    previous=shift_month(month,-1)
    return {"meta":meta,"month":month.strftime("%Y-%m"),"current":metrics(conn,filters,meta.version,month),
            "previous":metrics(conn,filters,meta.version,previous) if previous>=parse_month(meta.start_month) else None}


def trends(conn,filters,period):
    meta=metadata(conn,filters.version); end=selected_month(filters,meta)
    start=max(parse_month(meta.start_month),shift_month(end,-(35 if period=="all" else 23)))
    clause,values=where(filters,meta.version,start=start,end=end)
    result=conn.execute(sql.SQL("SELECT month,"+METRICS_SQL+" FROM market.facts WHERE {} GROUP BY month ORDER BY month").format(clause),values).fetchall()
    by_month={r.pop("month"):r for r in result}
    rates={r["month"]:r["rate"] for r in conn.execute("SELECT month,rate FROM market.mortgage WHERE dataset=%s",(meta.version,))}
    return {"meta":meta,"points":[{"month":m.strftime("%Y-%m"),**Metrics(**by_month.get(m,{}),mortgage_rate=rates.get(m)).model_dump()} for m in months(start,end)]}


def filter_options(conn,filters):
    meta=metadata(conn,filters.version); selected_month(filters,meta)
    result={"meta":meta}
    for key,label in (("county","counties"),("city","cities"),("zip","zips"),("subtype","subtypes")):
        clause,values=where(filters,meta.version,omit=key)
        result[label]=[r["value"] for r in conn.execute(sql.SQL("SELECT DISTINCT {} AS value FROM market.geographies WHERE {} ORDER BY value").format(sql.Identifier(key),clause),values) if key!='zip' or (len(r['value'])==5 and r['value'].isdigit())]
    return result


def map_data(conn,filters,level,metric):
    meta=metadata(conn,filters.version); month=selected_month(filters,meta)
    # Keep peer regions visible so a county can be changed directly on the map.
    clause,values=where(filters,meta.version,start=month,end=month,omit=level)
    area=sql.Identifier(level)
    rows=conn.execute(sql.SQL("""SELECT {area} AS id,count(*) AS closed_sales,
        percentile_cont(0.5) WITHIN GROUP(ORDER BY close_price) AS median_price
        FROM market.facts WHERE {where} AND kind='sold' GROUP BY {area} ORDER BY {area}""").format(area=area,where=clause),values).fetchall()
    for row in rows:
        row["name"]=row["id"]
        row["value"]=row["median_price"] if metric=="median_price" else row["closed_sales"]
    cells=[]
    if metric=="concentration":
        cells=[{"latitude":r["grid_lat"],"longitude":r["grid_lng"],"count":r["count"]} for r in conn.execute(sql.SQL("SELECT grid_lat,grid_lng,count(*) FROM market.facts WHERE {} AND kind='sold' AND grid_lat IS NOT NULL AND grid_lng IS NOT NULL GROUP BY grid_lat,grid_lng").format(clause),values)]
    unmapped=conn.execute(sql.SQL("SELECT count(*) AS n FROM market.facts WHERE {} AND kind='sold' AND (grid_lat IS NULL OR grid_lng IS NULL)").format(clause),values).fetchone()["n"]
    return {"meta":meta,"metric":metric,"level":level,"areas":rows,"cells":cells,"unmapped_sales":unmapped}


def competitive(conn,filters):
    meta=metadata(conn,filters.version); month=selected_month(filters,meta)
    clause,values=where(filters,meta.version,start=month,end=month)
    total=conn.execute(sql.SQL("SELECT count(*) AS n,COALESCE(sum(close_price),0) AS volume FROM market.facts WHERE {} AND kind='sold'").format(clause),values).fetchone()
    result={"meta":meta,"closed_sales":total["n"],"sales_volume":float(total["volume"])}
    for entity in ("agent","office"):
        rows=conn.execute(sql.SQL("""SELECT {id} AS id,min({name}) AS name,count(*) AS closed_sales,
            sum(close_price) AS sales_volume,percentile_cont(0.5) WITHIN GROUP(ORDER BY close_price) AS median_price
            FROM market.facts WHERE {where} AND kind='sold' GROUP BY {id} ORDER BY sales_volume DESC,{id}""").format(id=sql.Identifier(entity+"_id"),name=sql.Identifier(entity+"_name"),where=clause),values).fetchall()
        for row in rows:
            row["market_share"]=float(row["sales_volume"]/total["volume"]) if total["volume"] else 0
        result[entity+"s" if entity=="agent" else "offices"]=rows
    return result
