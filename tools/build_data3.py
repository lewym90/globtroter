#!/usr/bin/env python3
"""Krok 3: klimat (Meteostat, normy wieloletnie), morze (Open-Meteo Marine), atrakcje (Wikidata)."""
import csv,gzip,io,json,os,re,sys,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_data import get,sparql,dist,ROOT
P=ROOT+'/data/destinations.json'
ds=json.load(open(P,encoding='utf8'))
st=json.loads(gzip.decompress(get('https://bulk.meteostat.net/v2/stations/lite.json.gz')))
st=[s for s in st if (s.get('inventory') or {}).get('normals',{}).get('start') and s['location']['latitude'] is not None]
def normals(s):
    try: raw=gzip.decompress(get(f"https://bulk.meteostat.net/v2/normals/{s['id']}.csv.gz",tries=2,timeout=20)).decode()
    except Exception: return None
    rows=list(csv.reader(io.StringIO(raw)));last=max(int(r[1]) for r in rows)
    out={}
    for r in rows:
        if int(r[1])!=last: continue
        out[int(r[2])]=r
    if len(out)<12 or any(not out[m][4] for m in out): return None
    f=lambda r,i:float(r[i]) if r[i] else None
    return {'tmin':[f(out[m],3) for m in range(1,13)],'tmax':[f(out[m],4) for m in range(1,13)],'rain':[f(out[m],5) for m in range(1,13)],'station':s['name'].get('en'),'period':last}
nocl=[]
for d in ds:
    if d.get('climate'): continue
    near=sorted(st,key=lambda s:dist(d['lat'],d['lon'],s['location']['latitude'],s['location']['longitude']))[:6]
    for s in near:
        k=dist(d['lat'],d['lon'],s['location']['latitude'],s['location']['longitude'])
        if k>150: break
        n=normals(s)
        if n: n['km']=round(k);d['climate']=n;break
    if not d.get('climate'): nocl.append(d['name'])
print('bez klimatu',nocl,flush=True)
nosea=[]
for d in ds:
    if 'beach' not in d['tags'] or (d.get('climate') or {}).get('sea'): continue
    if not d.get('climate'): continue
    try:
        r=json.loads(get(f"https://marine-api.open-meteo.com/v1/marine?latitude={d['lat']}&longitude={d['lon']}&hourly=sea_surface_temperature&start_date=2025-01-01&end_date=2025-12-31&timezone=UTC",tries=3,timeout=30))
        h=r['hourly'];m=[[] for _ in range(12)]
        for t,v in zip(h['time'],h['sea_surface_temperature']):
            if v is not None: m[int(t[5:7])-1].append(v)
        if all(m): d['climate']['sea']=[round(sum(x)/len(x),1) for x in m]
        else: nosea.append(d['name'])
    except Exception as e: nosea.append(d['name']+'!')
    time.sleep(.5)
print('bez morza',nosea,flush=True)
json.dump(ds,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
T={'Q33506':'museum','Q207694':'museum','Q16970':'church','Q2977':'church','Q56242215':'church','Q16560':'palace','Q23413':'castle','Q4989906':'monument','Q174782':'square','Q22698':'park','Q570116':'sight','Q839954':'ruins','Q44613':'church','Q57821':'castle','Q1081138':'sight','Q12280':'bridge','Q2319498':'sight','Q40080':'beach','Q1107656':'park','Q43501':'zoo','Q162875':'monument','Q170980':'monument','Q39715':'sight','Q1497364':'sight','Q2065736':'museum','Q17431399':'museum','Q11707':'food','Q34442':'street','Q79007':'street','Q8502':'nature','Q34038':'nature','Q4421':'nature','Q179700':'monument','Q1244442':'sight','Q24354':'theatre','Q153562':'theatre','Q148319':'sight','Q45776':'sight','Q860861':'monument'}
vals=' '.join('wd:'+k for k in T)
A={}
miss=[]
for i,d in enumerate(ds):
    rad=25 if set(d['tags'])&{'nature','ski'} and 'city' not in d['tags'] else 12
    q='''SELECT ?i ?pl ?en ?coord ?links ?t ?img ?site WHERE { SERVICE wikibase:around { ?i wdt:P625 ?coord. bd:serviceParam wikibase:center "Point(%s %s)"^^geo:wktLiteral; wikibase:radius "%d". }
    ?i wdt:P31 ?t. VALUES ?t {%s} ?i wikibase:sitelinks ?links. FILTER(?links>=4)
    OPTIONAL{?i rdfs:label ?pl FILTER(LANG(?pl)="pl")} OPTIONAL{?i rdfs:label ?en FILTER(LANG(?en)="en")} OPTIONAL{?i wdt:P18 ?img} OPTIONAL{?i wdt:P856 ?site} } ORDER BY DESC(?links) LIMIT 70'''%(d['lon'],d['lat'],rad,vals)
    try:
        seen={}
        for r in sparql(q):
            k=r['i']['value'].rsplit('/',1)[1]
            if k in seen: continue
            m=re.findall(r'-?\d+\.?\d*',r['coord']['value']);name=(r.get('pl') or r.get('en') or {}).get('value')
            if not name or re.fullmatch(r'Q\d+',name): continue
            seen[k]={'n':name,'lat':round(float(m[1]),4),'lon':round(float(m[0]),4),'l':int(r['links']['value']),'t':T[r['t']['value'].rsplit('/',1)[1]],'q':k}
            if 'img' in r: seen[k]['img']=r['img']['value'].rsplit('/',1)[1]
            if 'site' in r: seen[k]['web']=r['site']['value']
        L=sorted(seen.values(),key=lambda x:-x['l'])[:36]
        A[d['id']]=L
        if len(L)<4: miss.append(d['name'])
    except Exception as e: miss.append(d['name']+'!');print(str(e)[:80])
    if i%20==0: print(i,flush=True);json.dump(A,open(ROOT+'/data/attractions.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
    time.sleep(1)
json.dump(A,open(ROOT+'/data/attractions.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
print('malo atrakcji',miss,flush=True)
