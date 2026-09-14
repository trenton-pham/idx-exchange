"""Download Census public cartographic boundaries and ship compact California geometry."""
from pathlib import Path
import json
import geopandas as gpd
import requests
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
SOURCES={"counties":"https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip",
         "zctas":"https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip"}

def main():
    cache=ROOT/"tmp/boundaries"; cache.mkdir(parents=True,exist_ok=True)
    target=ROOT/"web/public/geo"; target.mkdir(parents=True,exist_ok=True)
    for name,url in SOURCES.items():
        archive=cache/f"{name}.zip"
        if not archive.exists():
            with requests.get(url,stream=True,timeout=120) as response:
                response.raise_for_status()
                temporary=archive.with_suffix('.partial')
                with temporary.open('wb') as stream:
                    for chunk in response.iter_content(1024*1024): stream.write(chunk)
                temporary.replace(archive)
    counties=gpd.read_file(cache/"counties.zip")
    counties=counties.loc[counties.STATEFP=="06"].to_crs(4326)
    state=unary_union(counties.geometry)
    counties["id"]=counties.NAME; counties["name"]=counties.NAME
    counties.geometry=counties.geometry.simplify(0.004,preserve_topology=True)
    (target/"counties.geojson").write_text(counties[["id","name","geometry"]].to_json(drop_id=True))
    zips=gpd.read_file(cache/"zctas.zip",bbox=(-125,32,-114,42.1)).to_crs(4326)
    zips=zips[zips.intersects(state)].copy()
    zips.geometry=zips.geometry.intersection(state).simplify(0.002,preserve_topology=True)
    zips=zips[~zips.geometry.is_empty & zips.geometry.geom_type.isin(["Polygon","MultiPolygon"])]
    zips["id"]=zips.ZCTA5CE20; zips["name"]=zips.ZCTA5CE20
    (target/"zips.geojson").write_text(zips[["id","name","geometry"]].to_json(drop_id=True))
    (target/"sources.json").write_text(json.dumps({"sources":SOURCES,"license":"US Census Bureau public data","processing":"California only; EPSG:4326; topology-preserving simplification; ZCTAs clipped to state. ZCTAs approximate postal ZIP areas."},indent=2))
    print(f"Prepared {len(counties)} counties and {len(zips)} ZCTAs")

if __name__=="__main__": main()
