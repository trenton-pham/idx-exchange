"""Run only against a disposable database via TEST_DATABASE_URL."""
import os
import unittest
from datetime import date
from unittest.mock import patch
from uuid import uuid4
import statistics
from itertools import product
from fastapi.testclient import TestClient
from backend.app import app
from backend.db import connection
from backend.migrate import migrate
from backend.publish import publish,rollback
from backend.retention import months,window

def fact(key,month,price,county='Alpha',kind='sold'):
    return {'kind':kind,'listing_key':key,'month':month,'county':county,'city':'City '+county,'zip':'90001' if county=='Alpha' else '90002','subtype':'House',
        'close_price':price if kind=='sold' else None,'days_on_market':20,'price_sqft':100,'price_ratio':1,
        'agent_id':'a','agent_name':'Example Agent','office_id':'o','office_name':'Example Office','grid_lat':34.05,'grid_lng':-118.25,'modified_at':None}

@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'),'Set TEST_DATABASE_URL to a disposable PostgreSQL database')
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'DATABASE_URL':os.environ['TEST_DATABASE_URL']});self.env.start()
        self.addCleanup(self.env.stop)
        with connection() as conn: conn.execute('DROP SCHEMA IF EXISTS market CASCADE')
        migrate();self.client=TestClient(app)
    def seed(self,end=date(2026,12,1)):
        rows=[fact(str(m),m,100) for m in months(*window(end))]
        return publish(rows,[(m,6.5) for m in months(*window(end))],end)
    def test_atomic_rollover_and_previous_version_pruned(self):
        old=self.seed();new=self.seed(date(2027,1,1))
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT min(month) AS m FROM market.facts').fetchone()['m'],date(2024,2,1))
            for table in ['facts','mortgage','monthly_aggregates','competitive_aggregates']:
                self.assertEqual(conn.execute(f'SELECT count(*) AS n FROM market.{table} WHERE month < %s',(date(2024,2,1),)).fetchone()['n'],0)
        self.assertEqual(rollback(),old)
        self.assertEqual(self.client.get('/api/v1/meta').json()['start_month'],'2024-02')
    def test_failure_does_not_activate_or_prune(self):
        old=self.seed()
        def fail(conn):raise ValueError('injected failure')
        with self.assertRaises(ValueError):publish([fact('new',date(2027,1,1),200)],[],date(2027,1,1),before_activate=fail)
        self.assertEqual(self.client.get('/api/v1/meta').json()['version'],old)
        with connection() as conn:
            self.assertEqual(conn.execute('SELECT min(month) AS m FROM market.facts').fetchone()['m'],date(2024,1,1))
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM market.datasets').fetchone()['n'],1)
    def test_exact_median_and_filter_alignment(self):
        end=date(2026,8,1);prices=[100,100,100,1000,2000]
        rows=[fact(str(i),end,p,'Alpha' if i<3 else 'Beta') for i,p in enumerate(prices)]+[fact('l',end,0,kind='listing')]
        version=publish(rows,[(end,6.5)],end)
        result=self.client.get('/api/v1/summary',params={'version':version}).json()['current']
        self.assertEqual(result['median_price'],statistics.median(prices));self.assertEqual(result['closed_sales'],5);self.assertEqual(result['new_listings'],1)
        selected=self.client.get('/api/v1/summary',params={'county':'Beta'}).json()['current']
        self.assertEqual(selected['median_price'],1500);self.assertEqual(selected['mortgage_rate'],6.5)
        trend=self.client.get('/api/v1/trends',params={'county':'Beta','period':'all'})
        self.assertEqual(trend.status_code,200);self.assertEqual(trend.json()['points'][-1]['median_price'],1500)
        mapped=self.client.get('/api/v1/map',params={'level':'zip','metric':'concentration'})
        self.assertEqual(mapped.status_code,200);self.assertTrue(mapped.json()['cells'])
    def test_expired_version_invalid_filter_and_no_previous_comparison(self):
        self.seed(date(2027,1,1))
        self.assertEqual(self.client.get('/api/v1/summary?month=2024-01').status_code,416)
        self.assertEqual(self.client.get('/api/v1/summary?version='+str(uuid4())).status_code,409)
        self.assertEqual(self.client.get('/api/v1/summary?zip=oops').status_code,422)
        self.assertIsNone(self.client.get('/api/v1/summary?month=2024-02').json()['previous'])
    def test_idempotent_replay_and_deleted_records(self):
        end=date(2026,8,1);version=str(uuid4())
        publish([fact('a',end,1),fact('b',end,2)],[],end,dataset_id=version)
        self.assertEqual(publish([],[],end,dataset_id=version),version)
        publish([fact('b',end,2)],[],end)
        self.assertEqual(self.client.get('/api/v1/summary').json()['current']['closed_sales'],1)
    def test_public_responses_have_no_listing_fields(self):
        self.seed()
        for endpoint in ['meta','filters','summary','trends','map','competitive']:
            response=self.client.get('/api/v1/'+endpoint)
            self.assertEqual(response.status_code,200,response.text)
            for forbidden in ['listing_key','UnparsedAddress','modified_at','DB_PASSWORD','ListAgentEmail']:
                self.assertNotIn(forbidden,response.text)
        self.assertEqual(self.client.post('/api/v1/summary').status_code,405)
    def test_invalid_values_abort_before_publication(self):
        old=self.seed(); row=fact('x',date(2026,12,1),200);row['price_sqft']=float('inf')
        with self.assertRaises(ValueError):publish([row],[],date(2026,12,1))
        self.assertEqual(self.client.get('/api/v1/meta').json()['version'],old)

    def test_python_reconciliation_across_filter_intersections(self):
        end=date(2026,8,1); rows=[]
        for index,(county,city,zipcode,subtype) in enumerate(product(['Alpha','Beta'],['East','West'],['90001','90002'],['House','Condominium'])):
            for n in range(index%3+1):
                row=fact(f'{index}-{n}',end,100000+index*15000+n*7000,county)
                row.update(city=city,zip=zipcode,subtype=subtype,days_on_market=None if n==0 else 20+n)
                rows.append(row)
        version=publish(rows,[(end,6.7)],end)
        for county,city,zipcode,subtype in product(['','Alpha'],['','East'],['','90001'],['','Condominium']):
            selected=dict(county=county,city=city,zip=zipcode,subtype=subtype)
            expected=[r for r in rows if all(not value or r[key]==value for key,value in selected.items())]
            response=self.client.get('/api/v1/summary',params={**{k:v for k,v in selected.items() if v},'version':version})
            self.assertEqual(response.status_code,200)
            actual=response.json()['current']
            self.assertEqual(actual['closed_sales'],len(expected))
            self.assertEqual(actual['median_price'],statistics.median(r['close_price'] for r in expected))
            valid_days=[r['days_on_market'] for r in expected if r['days_on_market'] is not None]
            self.assertEqual(actual['days_sample'],len(valid_days))
            self.assertEqual(actual['days_on_market'],statistics.mean(valid_days) if valid_days else None)
            self.assertEqual(actual['mortgage_rate'],6.7)
