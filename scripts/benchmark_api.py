"""Measure warm public API latency without printing market data or credentials."""
import argparse
import json
import statistics
import time
from urllib.parse import urlencode
from urllib.request import urlopen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--runs',type=int,default=20)
    args=parser.parse_args()
    if args.runs<2: parser.error('At least two runs are required')
    def read(endpoint,params=None):
        with urlopen(args.url+'/api/v1/'+endpoint+'?'+urlencode(params or {}),timeout=15) as response:
            raw=response.read(); return json.loads(raw),len(raw)
    meta,_=read('meta'); rows=[]
    for county in ('','Santa Clara'):
        for endpoint in ('summary','trends','map','competitive'):
            params={'version':meta['version'],'county':county} if county else {'version':meta['version']}
            read(endpoint,params)
            times=[]
            for _ in range(args.runs):
                started=time.perf_counter();_,size=read(endpoint,params);times.append((time.perf_counter()-started)*1000)
            rows.append({'endpoint':endpoint,'selection':county or 'California','median_ms':round(statistics.median(times),2),'p95_ms':round(sorted(times)[int(.95*(len(times)-1))],2),'bytes':size})
    print(json.dumps({'demo':meta['demo'],'runs_per_case':args.runs,'results':rows},indent=2))


if __name__=='__main__': main()
