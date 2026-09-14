"""Full-history extraction, archival and atomic 36-month publication."""
import argparse
import json
import logging
import os
from pathlib import Path
from uuid import UUID,uuid4
import boto3
from botocore.exceptions import ClientError
from psycopg.types.json import Jsonb
from backend.db import connection
from backend.publish import publish
from backend.retention import HISTORY_START,latest_complete_month,months,parse_month
from backend.transform import read_month_pairs,transform,fact_rows,finite
from extract_crmls import TrestleClient,Month,DATASET_SPECS,export_month
from mortgage_fetch import fetch_rates

def optional_download(s3,bucket,key,path):
    try: s3.download_file(bucket,key,str(path)); return True
    except ClientError as exc:
        if str(exc.response["Error"]["Code"]) not in ("404","NoSuchKey"): raise
        return False

def run(args):
    end=parse_month(args.end_month) if args.end_month else latest_complete_month()
    if end>latest_complete_month(): raise ValueError("Only completed months can be published")
    run_id=str(UUID(args.run_id)) if args.run_id else str(uuid4())
    logging.info("Ingestion run %s for %s",run_id,end.strftime("%Y-%m"))
    root=Path(args.work_dir)/run_id; raw=root/"raw"; raw.mkdir(parents=True,exist_ok=True)
    bucket=os.environ["ARCHIVE_BUCKET"]; s3=boto3.client("s3")
    with connection() as lock:
        if not lock.execute("SELECT pg_try_advisory_lock(812403) AS acquired").fetchone()["acquired"]:
            raise RuntimeError("Another ingestion is already running")
        try:
            with connection() as conn:
                existing=conn.execute("SELECT reporting_month,status FROM market.ingestion_runs WHERE id=%s",(run_id,)).fetchone()
                if existing and existing["reporting_month"]!=end: raise ValueError("Resume must retain the original reporting month")
                if existing and existing["status"]=="succeeded": return run_id
                conn.execute("INSERT INTO market.ingestion_runs(id,status,reporting_month) VALUES (%s,'running',%s) ON CONFLICT(id) DO UPDATE SET status='running',finished_at=NULL",(run_id,end))
            client=TrestleClient(); client.validate_property_fields()
            for month in months(HISTORY_START,end):
                for spec in DATASET_SPECS:
                    filename=f"{spec.filename_prefix}{month:%Y%m}.csv"; key=f"runs/{run_id}/raw/{filename}"
                    if not optional_download(s3,bucket,key,raw/filename):
                        export_month(client,spec,Month(month.year,month.month),raw,force=True)
                        s3.upload_file(str(raw/filename),bucket,key)
            refs=root/"references"; refs.mkdir(exist_ok=True)
            for filename in ("california_valid_zip_codes.csv","City_and_County_Boundaries.geojson"):
                s3.download_file(bucket,f"references/{filename}",str(refs/filename))
            overrides=refs/"coordinate_overrides.csv"
            optional_download(s3,bucket,"references/coordinate_overrides.csv",overrides)
            rates=fetch_rates(); rates.to_csv(root/"mortgage.csv",index=False)
            s3.upload_file(str(root/"mortgage.csv"),bucket,f"runs/{run_id}/mortgage.csv")
            listings,sold=read_month_pairs(raw,HISTORY_START,end)
            before={"listing":len(listings),"sold":len(sold)}
            listings,sold=transform(listings,sold,zip_path=refs/"california_valid_zip_codes.csv",county_path=refs/"City_and_County_Boundaries.geojson",overrides=overrides)
            report={"before_cleaning":before,"after_cleaning":{"listing":len(listings),"sold":len(sold)},"policy":"full-history three-IQR; ratio 0.75–1.50; 36-month database window"}
            s3.put_object(Bucket=bucket,Key=f"runs/{run_id}/quality.json",Body=json.dumps(report),ContentType="application/json")
            version=publish(fact_rows(listings,sold,end),[(parse_month(r.year_month),finite(r.rate_30yr_fixed)) for r in rates.itertuples()],end,dataset_id=run_id)
            with connection() as conn:
                conn.execute("UPDATE market.ingestion_runs SET status='succeeded',finished_at=now(),details=%s WHERE id=%s",(Jsonb(report),run_id))
            logging.info("Published dataset %s",version)
            return version
        except Exception as exc:
            with connection() as conn:
                conn.execute("UPDATE market.ingestion_runs SET status='failed',finished_at=now(),details=%s WHERE id=%s",(Jsonb({"error_type":type(exc).__name__}),run_id))
            raise
        finally: lock.execute("SELECT pg_advisory_unlock(812403)")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end-month"); parser.add_argument("--run-id",help="Resume an immutable raw snapshot")
    parser.add_argument("--work-dir",default=os.getenv("WORK_DIR","/tmp/idx"))
    args=parser.parse_args(); logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    try: run(args)
    except Exception as exc:
        logging.error("Ingestion failed (%s); previous publication is preserved",type(exc).__name__)
        raise SystemExit(1) from None

if __name__=="__main__": main()
