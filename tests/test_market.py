"""Domain tests require no confidential data or cloud access."""
from datetime import date,datetime,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import pandas as pd
import yaml
from backend.retention import window,months,latest_complete_month,shift_month,SCHEDULE,TIMEZONE
from backend.transform import deduplicate,fact_rows,apply_coordinate_overrides
from feature_engineer import engineer_features
from mortgage_fetch import monthly_rates

class RetentionTests(unittest.TestCase):
    def test_partial_and_full_window(self):
        self.assertEqual(window(date(2026,8,1)),(date(2024,1,1),date(2026,8,1)))
        self.assertEqual(len(months(*window(date(2026,12,1)))),36)
    def test_rolling_january_2027_drops_january_2024(self):
        self.assertEqual(window(date(2027,1,1)),(date(2024,2,1),date(2027,1,1)))
    def test_leap_year(self):
        self.assertEqual(shift_month(date(2024,2,29),1),date(2024,3,1))
        self.assertEqual(len(months(*window(date(2028,2,1)))),36)
    def test_uses_pacific_calendar_at_utc_boundary(self):
        self.assertEqual(latest_complete_month(datetime(2027,2,1,3,tzinfo=timezone.utc)),date(2026,12,1))
        self.assertEqual(latest_complete_month(datetime(2027,2,7,14,tzinfo=timezone.utc)),date(2027,1,1))
    def test_schedule_and_dst(self):
        class Loader(yaml.SafeLoader): pass
        Loader.add_multi_constructor('!',lambda loader,suffix,node: loader.construct_scalar(node) if isinstance(node,yaml.ScalarNode) else loader.construct_sequence(node) if isinstance(node,yaml.SequenceNode) else loader.construct_mapping(node))
        template=yaml.load(Path('infra/application.yaml').read_text(),Loader=Loader)
        props=template['Resources']['MonthlySchedule']['Properties']
        self.assertEqual(props['ScheduleExpression'],SCHEDULE)
        self.assertEqual(props['ScheduleExpressionTimezone'],TIMEZONE)
        for month,hour in [(1,14),(7,13)]:
            self.assertEqual(datetime(2027,month,7,6,tzinfo=ZoneInfo(TIMEZONE)).astimezone(timezone.utc).hour,hour)

class QualityTests(unittest.TestCase):
    def test_month_pair_transform_preserves_corrections_and_measure_specific_exclusions(self):
        import geopandas as gpd
        from shapely.geometry import box
        from backend.transform import REQUIRED,read_month_pairs,transform
        end=date(2026,8,1)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            rows=[]
            for index in range(40):
                row=dict.fromkeys(REQUIRED)
                row.update(ListingKey=f'key-{index}',ListingId='219113154PS' if index==0 else str(index),ModificationTimestamp='2026-09-01',ListingContractDate='2026-08-01',CloseDate='2026-08-20',PurchaseContractDate='2026-08-10',ContractStatusChangeDate='2026-08-20',ClosePrice=380000+index*10000,OriginalListPrice=400000+index*10000,LivingArea=0 if index==1 else 1200,DaysOnMarket=-1 if index==2 else 20,CountyOrParish='Example',City='Example City',PostalCode=None if index==3 else '90001',PropertySubType='House',PropertyType='Residential',StateOrProvince='CA',ListAgentFullName='Example Agent',ListOfficeName='Example Office',ListAgentKey='a',ListOfficeKey='o',Latitude=34,Longitude=-118,BedroomsTotal=3,BathroomsTotalInteger=2,StandardStatus='Closed')
                rows.append(row)
            rows[0]['ClosePrice']=999999
            for kind in ('Listing','Sold'): pd.DataFrame(rows).to_csv(root/f'CRMLS{kind}202608.csv',index=False)
            pd.DataFrame({'ZIP_CODE':['90001']}).to_csv(root/'zips.csv',index=False)
            gpd.GeoDataFrame({'COUNTY_NAME':['Example'],'geometry':[box(-120,32,-116,36)]},crs=4326).to_file(root/'counties.geojson',driver='GeoJSON')
            listing,sold=read_month_pairs(root,end,end)
            listing,sold=transform(listing,sold,zip_path=root/'zips.csv',county_path=root/'counties.geojson')
            records=list(fact_rows(listing,sold,end)); sales={r['listing_key']:r for r in records if r['kind']=='sold'}
            self.assertEqual(len(sales),40)
            self.assertEqual(sales['key-0']['close_price'],380000)
            self.assertIsNone(sales['key-1']['price_sqft'])
            self.assertIsNone(sales['key-2']['days_on_market'])
            self.assertEqual(sales['key-3']['zip'],'Unknown')
            (root/'CRMLSSold202608.csv').unlink()
            with self.assertRaises(FileNotFoundError): read_month_pairs(root,end,end)
    def test_missing_zip_remains_in_production_totals(self):
        from clean import filter_zip_codes
        frame=pd.DataFrame({'PostalCode':['90001',None,'oops','90001-1234']})
        self.assertEqual(len(filter_zip_codes(frame,{'90001'},retain_unmapped=True)),4)
        self.assertEqual(len(filter_zip_codes(frame,{'90001'})),2)
    def test_latest_revision_wins_and_identical_rows_collapse(self):
        frame=pd.DataFrame([{'ListingKey':'x','ModificationTimestamp':'2026-01-01','ClosePrice':1},{'ListingKey':'x','ModificationTimestamp':'2026-02-01','ClosePrice':2}])
        self.assertEqual(deduplicate(pd.concat([frame,frame])).ClosePrice.tolist(),[2])
    def test_conflicts_without_unique_newest_timestamp_fail(self):
        for stamp in [None,'2026-01-01']:
            with self.assertRaisesRegex(ValueError,'Conflicting'):
                deduplicate(pd.DataFrame([{'ListingKey':'x','ModificationTimestamp':stamp,'ClosePrice':1},{'ListingKey':'x','ModificationTimestamp':stamp,'ClosePrice':2}]))
    def test_invalid_denominators(self):
        frame=pd.DataFrame({'CloseDate':['2026-01-01']*3,'ListingContractDate':['2025-12-01']*3,'PurchaseContractDate':['2025-12-10']*3,'ClosePrice':[100,100,100],'OriginalListPrice':[0,100,100],'LivingArea':[0,79,100]})
        result=engineer_features(frame)
        self.assertTrue(pd.isna(result.PriceRatio.iloc[0]));self.assertTrue(result.PricePerSqFt.iloc[:2].isna().all());self.assertEqual(result.PricePerSqFt.iloc[2],1)
    def test_retention_uses_event_date_and_invalid_dom_is_null(self):
        row={'ListingKey':'x','ListingContractDate':'2020-01-01','CloseDate':'2027-01-01','DaysOnMarket':-2,'ClosePrice':100,'PropertySubType':'House'}
        result=list(fact_rows(pd.DataFrame([row]),pd.DataFrame([row]),date(2027,1,1)))
        self.assertEqual(len(result),1);self.assertEqual(result[0]['kind'],'sold');self.assertIsNone(result[0]['days_on_market'])
    def test_overrides_only_fill_missing_coordinates(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'overrides.csv'
            pd.DataFrame([{'ListingKey':'x','Latitude':33,'Longitude':-118,'reason':'verified','source':'review'}]).to_csv(path,index=False)
            result=apply_coordinate_overrides(pd.DataFrame([{'ListingKey':'x','Latitude':34,'Longitude':None,'ClosePrice':123}]),path)
            self.assertEqual(result.Latitude.iloc[0],34);self.assertEqual(result.Longitude.iloc[0],-118);self.assertEqual(result.ClosePrice.iloc[0],123)
    def test_mortgage_is_average_of_observations(self):
        result=monthly_rates(pd.DataFrame({'date':['2026-01-01','2026-01-08','2026-02-01'],'rate':[6,8,5]}))
        self.assertEqual(result.rate_30yr_fixed.tolist(),[7,5])
