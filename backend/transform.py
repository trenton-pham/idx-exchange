"""Production adapters around the established cleaning and outlier stages."""
import math
from pathlib import Path
import pandas as pd
from clean import clean_frames
from feature_engineer import engineer_features
from outlier import filter_outliers
from backend.retention import window

REQUIRED={"ListingKey","ModificationTimestamp","ListingContractDate","CloseDate","ClosePrice","OriginalListPrice",
          "LivingArea","DaysOnMarket","CountyOrParish","City","PostalCode","PropertySubType","PropertyType",
          "StateOrProvince","ListAgentFullName","ListOfficeName","ListAgentKey","ListOfficeKey","ListingId",
          "Latitude","Longitude","PurchaseContractDate","ContractStatusChangeDate","BedroomsTotal","BathroomsTotalInteger","StandardStatus"}

def deduplicate(frame):
    if frame["ListingKey"].isna().any() or frame["ListingKey"].astype(str).str.strip().eq("").any():
        raise ValueError("Listing identity is missing")
    frame=frame.drop_duplicates().copy()
    duplicated=frame["ListingKey"].duplicated(keep=False)
    if not duplicated.any(): return frame
    winners=[]
    for _,group in frame.loc[duplicated].groupby("ListingKey",sort=False):
        stamps=pd.to_datetime(group["ModificationTimestamp"],errors="coerce",utc=True)
        latest=group.loc[stamps==stamps.max()]
        if stamps.isna().any() or len(latest)!=1:
            raise ValueError("Conflicting listing revisions require source reconciliation")
        winners.append(latest)
    return pd.concat([frame.loc[~duplicated],*winners],ignore_index=True)

def read_month_pairs(raw:Path,start,end):
    from backend.retention import months
    listings=[]; sold=[]
    for month in months(start,end):
        for kind,frames in (("Listing",listings),("Sold",sold)):
            path=raw/f"CRMLS{kind}{month:%Y%m}.csv"
            columns=pd.read_csv(path,nrows=0).columns
            missing=REQUIRED-set(columns)
            if missing: raise ValueError("Required fields missing: "+", ".join(sorted(missing)))
            # Archive the full export, but hold only analytical fields in memory.
            frame=pd.read_csv(path,usecols=sorted(REQUIRED),low_memory=False,dtype={field:"string" for field in ("ListingKey","PostalCode","ListAgentKey","ListOfficeKey","ListingId")})
            frames.append(frame)
    return deduplicate(pd.concat(listings,ignore_index=True)),deduplicate(pd.concat(sold,ignore_index=True))

def apply_coordinate_overrides(frame,path:Path | None):
    if path is None or not path.exists(): return frame
    overrides=pd.read_csv(path,dtype={"ListingKey":"string"})
    if not {"ListingKey","Latitude","Longitude","reason","source"} <= set(overrides.columns):
        raise ValueError("Coordinate overrides require identity, coordinates, reason and source")
    if overrides["ListingKey"].duplicated().any() or overrides[["reason","source"]].isna().any().any():
        raise ValueError("Coordinate overrides must be unique and attributable")
    result=frame.copy().set_index("ListingKey",drop=False)
    for row in overrides.to_dict("records"):
        if row["ListingKey"] in result.index:
            for field in ("Latitude","Longitude"):
                if pd.isna(result.at[row["ListingKey"],field]): result.at[row["ListingKey"],field]=row[field]
    return result.reset_index(drop=True)

def transform(listings,sold,*,zip_path,county_path,overrides=None):
    listings=apply_coordinate_overrides(listings,overrides); sold=apply_coordinate_overrides(sold,overrides)
    listings=listings.loc[listings.PropertyType=="Residential"].copy()
    sold=sold.loc[(sold.PropertyType=="Residential")&(sold.StandardStatus=="Closed")].copy()
    for frame in (listings,sold):
        for col in ("ClosePrice","OriginalListPrice","LivingArea","DaysOnMarket","BedroomsTotal","BathroomsTotalInteger"):
            frame[col]=pd.to_numeric(frame[col],errors="coerce")
    listings,sold=clean_frames(listings,sold,zip_path=zip_path,county_path=county_path,retain_unmapped_zip=True)
    return listings,filter_outliers(engineer_features(sold))

def finite(value):
    if value is None or pd.isna(value): return None
    number=float(value)
    return number if math.isfinite(number) else None

def fact_rows(listings,sold,end):
    start,end=window(end)
    def name(value): return str(value).strip() if pd.notna(value) and str(value).strip() else "Unknown"
    for kind,frame,date_field in (("listing",listings,"ListingContractDate"),("sold",sold,"CloseDate")):
        parsed_dates=pd.to_datetime(frame[date_field],errors="coerce",utc=True)
        modifications=pd.to_datetime(frame.get("ModificationTimestamp",pd.Series(index=frame.index,dtype="object")),errors="coerce",utc=True)
        for values,parsed,modified in zip(frame.itertuples(index=False,name=None),parsed_dates,modifications):
            if pd.isna(parsed): continue
            month=parsed.date().replace(day=1)
            if not start<=month<=end: continue
            row=dict(zip(frame.columns,values))
            agent=name(row.get("ListAgentFullName")); office=name(row.get("ListOfficeName"))
            dom=finite(row.get("DaysOnMarket")); lat=finite(row.get("Latitude")); lng=finite(row.get("Longitude"))
            valid_geo=bool(row.get("coordinates_in_california",False)) and not bool(row.get("coordinates_outside_county_flag",True))
            agent_id=name(row.get("ListAgentKey")); office_id=name(row.get("ListOfficeKey"))
            yield {"kind":kind,"listing_key":str(row["ListingKey"]),"month":month,
                "county":name(row.get("CountyOrParish")),"city":name(row.get("City")),"zip":name(row.get("PostalCode")),"subtype":name(row.get("PropertySubType")),
                "close_price":finite(row.get("ClosePrice")) if kind=="sold" else None,
                "days_on_market":dom if dom is not None and dom>=0 else None,
                "price_sqft":finite(row.get("PricePerSqFt")),"price_ratio":finite(row.get("CloseToOriginalListRatio")),
                "agent_id":agent_id,"agent_name":agent if agent_id!="Unknown" else "Unknown agent",
                "office_id":office_id,"office_name":office if office_id!="Unknown" else "Unknown office",
                "grid_lat":round(math.floor(lat*10)/10+0.05,2) if valid_geo and lat is not None and lng is not None else None,
                "grid_lng":round(math.floor(lng*10)/10+0.05,2) if valid_geo and lat is not None and lng is not None else None,
                "modified_at":modified.to_pydatetime() if pd.notna(modified) else None}
