#!/usr/bin/env python3
"""Buduje dane statyczne Globtrotera: lotniska, kierunki, klimat, morze, atrakcje.
Zrodla: OurAirports (public domain), Wikidata (CC0), Meteostat (CC BY-NC), Open-Meteo Marine (CC BY)."""
import csv,gzip,io,json,math,os,re,sys,time,urllib.parse,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA={'User-Agent':'Globtroter/1.0 (non-commercial travel planner)'}
def get(url,tries=4,timeout=60):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=timeout) as r: return r.read()
        except Exception as e:
            if i==tries-1: raise
            time.sleep(3*(i+1))
def sparql(q):
    u='https://query.wikidata.org/sparql?format=json&query='+urllib.parse.quote(q)
    return json.loads(get(u,timeout=70))['results']['bindings']
def dist(a,b,c,d):
    R=6371;p=math.radians;x=math.sin(p(c-a)/2)**2+math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))
EU='AL AD AT BA BE BG BY CH CY CZ DE DK EE ES FI FR GB GE GR HR HU IE IS IT LT LU LV MA MD ME MK MT NL NO PL PT RO RS SE SI SK TR XK EG TN AE JO CV'.split()
PLN={'pl':'Polska'}
def airports():
    rows=list(csv.DictReader(io.StringIO(get('https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv').decode())))
    try:
        from fli.models import Airport
        known=set(Airport.__members__)
    except ImportError: known=None
    out=[]
    for r in rows:
        if r['iso_country'] not in EU or r['type'] not in('large_airport','medium_airport') or not r['iata_code'] or r['scheduled_service']!='yes': continue
        if known is not None and r['iata_code'] not in known: continue
        out.append({'iata':r['iata_code'],'name':r['name'],'city':r['municipality'],'cc':r['iso_country'],'lat':round(float(r['latitude_deg']),4),'lon':round(float(r['longitude_deg']),4),'large':r['type']=='large_airport'})
    return sorted(out,key=lambda a:a['iata'])
def dests(aps):
    idx={a['iata']:a for a in aps}
    out=[]
    for ln in open(os.path.join(ROOT,'tools/destinations.tsv'),encoding='utf8'):
        p=ln.rstrip('\n').split('\t')
        if len(p)<5: continue
        d=[x for x in p[3].split(',') if x in idx]
        if not d: print('BRAK LOTNISK',p[0],file=sys.stderr); continue
        out.append({'name':p[0],'en':p[1],'cc':p[2],'air':d,'tags':p[4].split(',')})
    # Wikidata: po etykiecie i kraju
    for i in range(0,len(out),25):
        part=out[i:i+25]
        vals=' '.join('("%s"@en "%s")'%(d['en'].replace('"',''),d['cc']) for d in part)
        q='''SELECT ?l ?iso ?c ?coord ?ta ?links ?descr WHERE { VALUES (?l ?iso) {%s}
        ?c rdfs:label ?l; wdt:P625 ?coord; wikibase:sitelinks ?links; wdt:P17 ?k. ?k wdt:P297 ?iso.
        OPTIONAL{?c wdt:P3134 ?ta} OPTIONAL{?c schema:description ?descr FILTER(LANG(?descr)="pl")} }'''%vals
        best={}
        try:
            for r in sparql(q):
                k=r['l']['value'];n=int(r['links']['value'])
                if k not in best or n>best[k][0]: best[k]=(n,r)
        except Exception as e: print('wd',e,file=sys.stderr)
        for d in part:
            b=best.get(d['en'])
            if b:
                r=b[1];m=re.findall(r'-?\d+\.?\d*',r['coord']['value']);d['lon'],d['lat']=round(float(m[0]),4),round(float(m[1]),4)
                d['qid']=r['c']['value'].rsplit('/',1)[1];d['links']=b[0]
                if 'ta' in r: d['ta']=r['ta']['value']
                if 'descr' in r: d['desc']=r['descr']['value']
        time.sleep(1.5)
    return out
if __name__=='__main__':
    aps=airports();print(len(aps),'lotnisk')
    json.dump(aps,open(ROOT+'/data/airports.json','w'),ensure_ascii=False,separators=(',',':'))
    ds=dests(aps);print(len(ds),'kierunkow; bez wsp:',[d['name'] for d in ds if 'lat' not in d],'\nbez TA:',[d['name'] for d in ds if 'ta' not in d])
    json.dump(ds,open(ROOT+'/tools/dests.step1.json','w'),ensure_ascii=False,indent=0)
