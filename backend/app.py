"""Read-only public API. No ingestion endpoints or source records are exposed."""
import logging
from typing import Annotated

import psycopg
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

from backend import queries
from backend.db import connection
from backend.models import Competitive, Filters, FilterOptions, MapData, MapFilters, Meta, Summary, Trends, TrendFilters

app=FastAPI(title="California Housing Market API",version="1.0.0",docs_url="/api/docs",openapi_url="/api/openapi.json")
Selection=Annotated[Filters,Query()]


@app.middleware("http")
async def headers(request:Request,call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Cache-Control"]="public, max-age=60, s-maxage=300" if response.status_code==200 else "no-store"
    return response


@app.exception_handler(psycopg.Error)
async def database_error(request,exc):
    logging.getLogger(__name__).error("Database request failed (%s)",type(exc).__name__)
    return JSONResponse(status_code=503,content={"detail":{"code":"temporarily_unavailable","message":"Market data is temporarily unavailable. Please try again."}})


@app.get("/api/v1/meta",response_model=Meta)
def meta():
    with connection(readonly=True) as conn: return queries.metadata(conn)


@app.get("/api/v1/filters",response_model=FilterOptions)
def filters(selection:Selection):
    with connection(readonly=True) as conn: return queries.filter_options(conn,selection)


@app.get("/api/v1/summary",response_model=Summary)
def summary(selection:Selection):
    with connection(readonly=True) as conn: return queries.summary(conn,selection)


@app.get("/api/v1/trends",response_model=Trends)
def trends(selection:Annotated[TrendFilters,Query()]):
    with connection(readonly=True) as conn: return queries.trends(conn,selection,selection.period)


@app.get("/api/v1/map",response_model=MapData)
def map_data(selection:Annotated[MapFilters,Query()]):
    with connection(readonly=True) as conn: return queries.map_data(conn,selection,selection.level,selection.metric)


@app.get("/api/v1/competitive",response_model=Competitive)
def competitive(selection:Selection):
    with connection(readonly=True) as conn: return queries.competitive(conn,selection)


handler=Mangum(app,lifespan="off")
