#!/usr/bin/env python3
"""Krok 4: uzupelnia klimat tam, gdzie brak stacji w poblizu, dodaje morze i zweryfikowane klucze hoteli."""
import csv,gzip,io,json,os,sys,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_data import get,dist,ROOT
P=ROOT+'/data/destinations.json'
ds=json.load(open(P,encoding='utf8'))
st=json.loads(gzip.decompress(get('https://bulk.meteostat.net/v2/stations/lite.json.gz')))
st=[s for s in st if s['location']['latitude'] is not None]
def normals(s,elev):
    try: raw=gzip.decompress(get(f"https://bulk.meteostat.net/v2/normals/{s['id']}.csv.gz",tries=1,timeout=15)).decode()
    except Exception: return None
    rows=[r for r in csv.reader(io.StringIO(raw)) if r[4] and r[3]]
    if not rows: return None
    last=max(int(r[1]) for r in rows);out={int(r[2]):r for r in rows if int(r[1])==last}
    if len(out)<12: return None
    c=(s['location'].get('elevation') or 0)-(elev or 0);k=c*0.0065
    return {'tmin':[round(float(out[m][3])+k,1) for m in range(1,13)],'tmax':[round(float(out[m][4])+k,1) for m in range(1,13)],'rain':[float(out[m][5]) if out[m][5] else None for m in range(1,13)],'station':s['name'].get('en'),'period':last}
ELEV={'Livigno':1816,'Interlaken':570}
left=[]
for d in ds:
    if d.get('climate'): continue
    near=sorted(st,key=lambda s:dist(d['lat'],d['lon'],s['location']['latitude'],s['location']['longitude']))[:40]
    for s in near:
        k=dist(d['lat'],d['lon'],s['location']['latitude'],s['location']['longitude'])
        if k>320: break
        if abs((s['location'].get('elevation') or 0)-ELEV.get(d['name'],(s['location'].get('elevation') or 0)))>1500: continue
        n=normals(s,ELEV.get(d['name'],s['location'].get('elevation')))
        if n:
            if all(v is None for v in n['rain']): n['rain']=[0]*12
            n['km']=round(k);d['climate']=n;print(d['name'],s['name'].get('en'),round(k),flush=True);break
    if not d.get('climate'): left.append(d['name'])
print('nadal bez klimatu',left,flush=True)
for d in ds:
    c=d.get('climate')
    if c and 'beach' in d['tags'] and not c.get('sea'):
        try:
            r=json.loads(get(f"https://marine-api.open-meteo.com/v1/marine?latitude={d['lat']}&longitude={d['lon']}&hourly=sea_surface_temperature&start_date=2025-01-01&end_date=2025-12-31&timezone=UTC",tries=3,timeout=30))
            h=r['hourly'];m=[[] for _ in range(12)]
            for t,v in zip(h['time'],h['sea_surface_temperature']):
                if v is not None: m[int(t[5:7])-1].append(v)
            if all(m): c['sea']=[round(sum(x)/len(x),1) for x in m]
            else: print('morze puste',d['name'],flush=True)
        except Exception as e: print('morze blad',d['name'],str(e)[:60],flush=True)
        time.sleep(.4)
fix=json.load(open(ROOT+'/tools/ta_fix.json',encoding='utf8'))
for d in ds:
    if d['name'] in fix:
        g=fix[d['name']]
        j=json.loads(get(f'https://data.xotelo.com/api/list?location_key=g{g}&limit=3&sort=best_value',tries=2,timeout=20))
        L=(j.get('result') or {}).get('list') or []
        q=(L[0].get('geo') if L else None)
        D=dist(d['lat'],d['lon'],q['latitude'],q['longitude']) if q else None
        if D is not None and D<70: d['ta']=str(g);d['hotels']=j['result']['total_count']
        else: print('ODRZUCONY',d['name'],D,L[0]['url'][40:100] if L else None,flush=True);d.pop('ta',None)
        time.sleep(.3)
print('z hotelami',sum('ta' in d for d in ds),'z klimatem',sum(bool(d.get('climate')) for d in ds),'morze',sum(bool((d.get('climate') or {}).get('sea')) for d in ds),'/',len(ds))
print('plaza bez morza',[d['name'] for d in ds if 'beach' in d['tags'] and not (d.get('climate') or {}).get('sea')])
json.dump(ds,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
