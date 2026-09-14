"""Synthetic records only. Never load this into a production dataset."""
import json
import math
import random
from pathlib import Path
from backend.retention import latest_complete_month,window,months
from backend.publish import publish
from backend.migrate import migrate

def records(end):
    from shapely.geometry import shape
    rng=random.Random(4107)
    geometry=json.loads((Path(__file__).resolve().parents[1]/"web/public/geo/counties.geojson").read_text())
    urban={"Los Angeles":("Los Angeles","90012",820000,200),"Santa Clara":("San Jose","95112",1450000,80),
           "San Diego":("San Diego","92101",960000,100),"Orange":("Irvine","92602",1250000,85),
           "San Francisco":("San Francisco","94102",1380000,50),"Sacramento":("Sacramento","95814",540000,80),
           "Alameda":("Oakland","94612",1030000,70),"Riverside":("Riverside","92501",610000,90)}
    offices=["Pacific Coast Realty","Golden State Homes","Westward Properties","Sierra & Coast","California Collective","Harbor House Realty","Valley Residential","Redwood Real Estate"]
    agents=["Alex Morgan","Jordan Chen","Taylor Rivera","Casey Williams","Sam Patel","Morgan Lee","Riley Davis","Avery Kim","Drew Martinez","Quinn Thompson","Jamie Brooks","Cameron Park"]
    for index,month in enumerate(months(*window(end))):
        season=1+0.15*math.sin((month.month-3)/12*2*math.pi)
        for county_index,feature in enumerate(geometry["features"]):
            county=feature["properties"]["name"]; point=shape(feature["geometry"]).representative_point()
            city,zipcode,base,volume=urban.get(county,(county,"9"+str(1000+county_index),400000+county_index*4200,20))
            count=max(5,int(volume*season+rng.uniform(-4,4)))
            for kind,multiplier in (("sold",1),("listing",1.45)):
                for n in range(int(count*multiplier)):
                    price=round(base*(1+index*0.002+0.035*math.sin(month.month/12*2*math.pi))*rng.uniform(0.65,1.4)/1000)*1000
                    office=rng.choices(range(8),weights=[30,22,15,10,8,6,5,4])[0]; agent=rng.randrange(12)
                    yield {"kind":kind,"listing_key":f"demo-{month}-{county_index}-{kind}-{n}","month":month,
                        "county":county,"city":city,"zip":zipcode,"subtype":["Single Family Residence","Condominium","Townhouse"][n%3],
                        "close_price":price if kind=="sold" else None,"days_on_market":round(25+10*math.cos(month.month/12*2*math.pi)+rng.uniform(0,10),1),
                        "price_sqft":round(price/rng.uniform(1200,2400),2) if kind=="sold" else None,"price_ratio":round(rng.uniform(0.94,1.045),4) if kind=="sold" else None,
                        "agent_id":f"demo-agent-{agent}","agent_name":agents[agent],"office_id":f"demo-office-{office}","office_name":offices[office],
                        "grid_lat":round(point.y,1),"grid_lng":round(point.x,1),"modified_at":None}

def main():
    migrate(); end=latest_complete_month()
    rates=[(m,round(6.4+0.35*math.sin(i/4),3)) for i,m in enumerate(months(*window(end)))]
    print("Published SYNTHETIC demonstration dataset",publish(records(end),rates,end,demo=True))

if __name__=="__main__": main()
