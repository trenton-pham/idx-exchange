"""Monthly expected-publication check, invoked on day 8 by EventBridge."""
from datetime import datetime
from zoneinfo import ZoneInfo
from backend.db import connection
from backend.retention import TIMEZONE,latest_complete_month

def handler(event,context):
    with connection(readonly=True) as conn:
        row=conn.execute("SELECT window_end FROM market.datasets WHERE id=(SELECT active FROM market.state)").fetchone()
    if not row or row["window_end"]<latest_complete_month():
        raise RuntimeError("Expected monthly publication is missing")
    return {"status":"current"}
