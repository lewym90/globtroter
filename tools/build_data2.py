#!/usr/bin/env python3
"""Krok 2: kierunki. Dane z Wikidata, klucze hoteli sprawdzane w Xotelo."""
import json,os,re,sys,time,unicodedata
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_data import get,sparql,dist,ROOT
def slug(s):
    s=unicodedata.normalize('NFKD',s.replace('ł','l').replace('Ł','L'))
    return re.sub(r'[^a-z0-9]+','-',s.encode('ascii','ignore').decode().lower()).strip('-')
TA_FB={'Barcelona':'187497','Madrid':'187514','Paris':'187147','London':'186338','Milan':'187849','Lisbon':'189158','Amsterdam':'188590','Vienna':'190454','Prague':'274707','Budapest':'274887','Athens':'189400','Berlin':'187323','Dublin':'186605','Porto':'189180','Venice':'187870','Florence':'187895','Naples':'187785','Málaga':'187438','Seville':'187443','Valencia':'187529','Nice':'187234','Split':'295370','Dubrovnik':'295371','Zadar':'303826','Copenhagen':'189541','Stockholm':'189852','Oslo':'190479','Helsinki':'189934','Istanbul':'293974','Antalya':'297962','Bodrum':'298031','Riga':'274967','Tallinn':'274958','Vilnius':'274951','Reykjavík':'189970','Edinburgh':'186525','Valletta':'190328','Marrakesh':'293734','Tbilisi':'294195','Kraków':'274772'}
aps={a['iata']:a for a in json.load(open(ROOT+'/data/airports.json'))}
ds=[]
for ln in open(ROOT+'/tools/destinations.tsv',encoding='utf8'):
    p=ln.rstrip('\n').split('\t')
    if len(p)<5: continue
    air=[x for x in p[3].split(',') if x in aps]
    if not air: print('BRAK LOTNISK',p[0]);continue
    ds.append({'id':slug(p[0]),'name':p[0],'en':p[1],'cc':p[2],'air':air,'tags':p[4].split(',')})
CITIES=json.load(open(os.environ['CITIES']))
ALT={'Thira':'Fíra','Sarandë':'Sarandë','Arrecife':'Arrecife','Puerto del Rosario':'Puerto del Rosario','Chamonix-Mont-Blanc':'Chamonix-Mont-Blanc','Zermatt':'Zermatt','Mykonos':'Mykonos','Hvar':'Hvar'}
for d in ds:
    n=ALT.get(d['en'],d['en'])
    hit=[c for c in CITIES if c['country']==d['cc'] and (c['name']==n or c['name']==d['en'])]
    hit=[c for c in hit if dist(float(c['lat']),float(c['lng']),aps[d['air'][0]]['lat'],aps[d['air'][0]]['lon'])<320]
    if hit: d['lat'],d['lon']=round(float(hit[0]['lat']),4),round(float(hit[0]['lng']),4)
    else: continue
    q='''SELECT ?c ?ta ?links ?descr WHERE { SERVICE wikibase:around { ?c wdt:P625 ?co. bd:serviceParam wikibase:center "Point(%s %s)"^^geo:wktLiteral; wikibase:radius "9". }
    ?c wikibase:sitelinks ?links. FILTER(?links>=15) FILTER EXISTS{?c wdt:P31/wdt:P279* wd:Q486972}
    OPTIONAL{?c wdt:P3134 ?ta} OPTIONAL{?c schema:description ?descr FILTER(LANG(?descr)="pl")} } ORDER BY DESC(?links) LIMIT 6'''%(d['lon'],d['lat'])
    try:
        r=sparql(q)
        if r:
            d['qid']=r[0]['c']['value'].rsplit('/',1)[1];d['links']=int(r[0]['links']['value'])
            if 'descr' in r[0]: d['desc']=r[0]['descr']['value']
            for x in r:
                if 'ta' in x: d['ta']=x['ta']['value'].split('-')[0].lstrip('g');break
    except Exception as e: print('wd',d['name'],str(e)[:80],flush=True)
    if d['en'] in TA_FB: d['ta']=TA_FB[d['en']]
    time.sleep(.4)
print('bez wsp',[d['name'] for d in ds if 'lat' not in d],flush=True)
for d in ds:
    if 'lat' not in d:
        a=aps[d['air'][0]];d['lat'],d['lon'],d['approx']=a['lat'],a['lon'],True;d['links']=0
bad=[]
for d in ds:
    if 'ta' not in d: continue
    try:
        j=json.loads(get(f"https://data.xotelo.com/api/list?location_key=g{d['ta']}&limit=1&sort=best_value",tries=2,timeout=20))
        L=(j.get('result') or {}).get('list') or []
        if not L: d.pop('ta');bad.append(d['name']);continue
        g=L[0].get('geo') or {}
        if g and dist(d['lat'],d['lon'],g['latitude'],g['longitude'])>60: bad.append(d['name']+'(dystans)');d.pop('ta')
        else: d['hotels']=j['result']['total_count']
    except Exception as e: print('xo',d['name'],str(e)[:60])
    time.sleep(.4)
print('zle TA',bad);print('bez TA',[d['name'] for d in ds if 'ta' not in d])
json.dump(ds,open(ROOT+'/data/destinations.json','w'),ensure_ascii=False,separators=(',',':'))
print('ok',len(ds))
