#!/usr/bin/env python3
"""Godziny otwarcia atrakcji z OpenStreetMap. Laczymy tylko po identyfikatorze Wikidata, nigdy po nazwie,
wiec godziny nie trafia do zlego miejsca. Brak danych to brak godzin, a nie zgadywanie."""
import json,os,sys,time,urllib.parse,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=ROOT+'/data/attractions.json';D=ROOT+'/data/hours.json'
URLS=['https://overpass-api.de/api/interpreter','https://overpass.private.coffee/api/interpreter','https://maps.mail.ru/osm/tools/overpass/api/interpreter']
BUDGET=float(os.environ.get('BUDGET_S','5000'))
ONLY=set(filter(None,os.environ.get('ONLY','').split(',')))  # np. ONLY=hurghada,side: tylko te kierunki
def ask(q):
    for u in URLS:
        try:
            r=urllib.request.Request(u,data=urllib.parse.urlencode({'data':q}).encode(),headers={'User-Agent':'Globtroter/1.0 (non-commercial)'})
            return json.load(urllib.request.urlopen(r,timeout=120))['elements']
        except Exception as e: print(' ',u[8:24],str(e)[:60],flush=True);time.sleep(4)
    return None
def main():
    ds=json.load(open(ROOT+'/data/destinations.json',encoding='utf8'));A=json.load(open(P,encoding='utf8'))
    done=json.load(open(D,encoding='utf8')) if os.path.exists(D) else {};t0=time.time()
    ds=[d for d in ds if not ONLY or d['id'] in ONLY]
    for d in ds:
        if d['id'] in done or time.time()-t0>BUDGET: continue
        la,lo=d['lat'],d['lon'];w=.15
        r=ask(f'[out:json][timeout:90];nwr["wikidata"]["opening_hours"]({la-w},{lo-w},{la+w},{lo+w});out tags;')
        if r is None: continue
        m={e['tags']['wikidata']:e['tags']['opening_hours'][:120] for e in r}
        n=0
        for x in A.get(d['id'],[]):
            if x['q'] in m: x['h']=m[x['q']];n+=1
        done[d['id']]=n;print(d['name'],n,flush=True);time.sleep(3)
        json.dump(done,open(D,'w'));json.dump(A,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
    print('miasta',len(done),'z',len(ds))
if __name__=='__main__': main()
