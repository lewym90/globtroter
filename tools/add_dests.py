#!/usr/bin/env python3
"""Dodaje nowe kierunki z tools/destinations_new.tsv bez przebudowy i bez zmiany istniejacych wpisow.
Robi to samo co build_data*.py, ale tylko dla nowych: lotniska (OurAirports, sprawdzane w bibliotece fli),
rekord kierunku (GeoNames, Wikidata, klucz TripAdvisora sprawdzony w Xotelo), klimat (Meteostat),
morze (Open-Meteo Marine 2025), atrakcje z Wikidata i ksztalt kraju (Natural Earth przez world-atlas).
Czego nie da sie pobrac, zostaje puste i trafia do raportu. Nic nie jest zgadywane.
Uruchomienie: python3 tools/add_dests.py  (CITIES=sciezka do cities.json z GeoNames, opcjonalnie)
Dalej: ONLY=<id,id> python3 tools/build_poi.py, build_voyage.py, build_wiki.py, build_hours.py, build_food.py, build_hotels.py, build_photos.py"""
import csv,gzip,io,json,math,os,re,sys,time,unicodedata,urllib.error,urllib.parse,urllib.request
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_data import EU,dist,ROOT
UA={'User-Agent':'Globtroter/1.0 (non-commercial travel planner; github.com/lewym90/globtroter)'}
NEW=ROOT+'/tools/destinations_new.tsv'
def get(url,tries=6,timeout=60):
    """Pobranie z ponawianiem; przy 429 czeka tyle, ile kaze serwer."""
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=timeout) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code==404 or i==tries-1: raise
            w=int(e.headers.get('retry-after') or 0) if e.code==429 else 0
            time.sleep(min(max(w,5*(i+1)),120))
        except Exception:
            if i==tries-1: raise
            time.sleep(5*(i+1))
def sparql(q): return json.loads(get('https://query.wikidata.org/sparql?format=json&query='+urllib.parse.quote(q),timeout=90))['results']['bindings']
def slug(s):
    s=unicodedata.normalize('NFKD',s.replace('ł','l').replace('Ł','L'))
    return re.sub(r'[^a-z0-9]+','-',s.encode('ascii','ignore').decode().lower()).strip('-')
def dump(o,p): json.dump(o,open(p,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))

# Miejscowosc, ktorej wspolrzedne bierzemy z GeoNames (jak build_data2), gdy nazwa kierunku to wyspa lub region.
GEONAME={'Dżerba':'Midoun','Sousse i Monastir':'Sousse','Szarm el-Szejk':'Sharm el-Sheikh','Sal':'Santa Maria','Boa Vista':'Sal Rei'}
# Wspolrzedne z Wikidata (P625): brak w GeoNames albo punkt GeoNames lezy w glebi ladu.
# Chalkidiki: Nikiti, u nasady Sithonii, miedzy Kassandra a Sithonia. Dubaj: punkt GeoNames lezy ok. 15 km od brzegu.
WDCOORD={'Chalkidiki':'Q1018264','Słoneczny Brzeg':'Q1011039','Dubaj':'Q612'}
# Element Wikidata opisujacy caly kierunek (wyspa, polwysep, miasto). Daje qid, links i opis.
QID={'Hurghada':'Q187284','Makadi Bay':'Q1521754','Marsa Alam':'Q1001901','Szarm el-Szejk':'Q644','Dżerba':'Q188938','Sousse i Monastir':'Q180717',
     'Hammamet':'Q339535','Mahdia':'Q466054','Side':'Q152405','Alanya':'Q171810','Belek':'Q815388','Marmaris':'Q209908','Chalkidiki':'Q204728',
     'Lloret de Mar':'Q12977','Salou':'Q662789','Benidorm':'Q487981','Słoneczny Brzeg':'Q1011039','Dubaj':'Q612','Akaba':'Q180522','Sal':'Q111989','Boa Vista':'Q110440'}
# Klucze miejsc TripAdvisora: z adresow stron tripadvisor.com (Hotels-g<ID>-...), Side z Wikidata P3134. Kazdy sprawdzany w Xotelo.
TA={'Hurghada':297549,'Makadi Bay':297550,'Marsa Alam':311425,'Szarm el-Szejk':297555,'Dżerba':297948,'Sousse i Monastir':295401,'Hammamet':297943,
    'Mahdia':297947,'Side':297968,'Alanya':297961,'Belek':312725,'Marmaris':298033,'Chalkidiki':189466,'Lloret de Mar':494960,'Salou':562814,
    'Benidorm':187525,'Słoneczny Brzeg':499086,'Dubaj':295424,'Akaba':298101,'Sal':482848,'Boa Vista':482843}
ISON={'EG':818,'TN':788,'AE':784,'JO':400,'CV':132}
# Miejsca z gotowym elementem Wikidata i wspolrzednymi (P625), np. polskie miejscowosci: EXTRA=plik.json {nazwa: {q, lat, lon}}
EXTRA=json.load(open(os.environ['EXTRA'],encoding='utf8')) if os.environ.get('EXTRA') else {}
for _n,_v in EXTRA.items():
    if _v: QID[_n]=_v['q']
REPORT={}
def note(i,k,v): REPORT.setdefault(i,{})[k]=v

def read_new(have):
    out=[];ids={d['id'] for d in have};ens={(d['en'],d['cc']) for d in have};names={d['name'] for d in have}
    for ln in open(NEW,encoding='utf8'):
        p=ln.rstrip('\n').split('\t')
        if len(p)<5: continue
        i=slug(p[0])
        if i in ids or (p[1],p[2]) in ens or p[0] in names: print('JUZ JEST, pomijam',p[0]);continue
        out.append({'id':i,'name':p[0],'en':p[1],'cc':p[2],'want':p[3].split(','),'tags':p[4].split(','),'line':ln.rstrip('\n')})
    return out
def airports(new,aps):
    """Dopisuje brakujace lotniska: nowe kraje tym samym filtrem co build_data.airports() i lotniska wskazane w TSV."""
    have={a['iata'] for a in aps};need={x for d in new for x in d['want']}
    ccs={d['cc'] for d in new if d['cc'] not in {a['cc'] for a in aps}}
    try:
        from fli.models import Airport
        known=set(Airport.__members__)
    except ImportError: known=None;print('UWAGA: brak biblioteki fli, nie sprawdzam lotnisk')
    rows=csv.DictReader(io.StringIO(get('https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv',timeout=120).decode()))
    add=[];nofli=[]
    for r in rows:
        c=r['iata_code']
        if not c or c in have: continue
        ok=(r['iso_country'] in ccs and r['type'] in('large_airport','medium_airport') and r['scheduled_service']=='yes') or c in need
        if not ok: continue
        if known is not None and c not in known: nofli.append(c);continue
        add.append({'iata':c,'name':r['name'],'city':r['municipality'],'cc':r['iso_country'],'lat':round(float(r['latitude_deg']),4),'lon':round(float(r['longitude_deg']),4),'large':r['type']=='large_airport'})
    print('nowe lotniska',len(add),'| nieznane fli:',nofli)
    return sorted(aps+add,key=lambda a:a['iata']),add,nofli,known
def wd_items(qs):
    v=' '.join('wd:'+q for q in qs)
    r=sparql('''SELECT ?c ?coord ?links ?ta ?dpl ?iso WHERE { VALUES ?c {%s} ?c wikibase:sitelinks ?links. OPTIONAL{?c wdt:P625 ?coord}
      OPTIONAL{?c wdt:P3134 ?ta} OPTIONAL{?c schema:description ?dpl FILTER(LANG(?dpl)="pl")} OPTIONAL{?c wdt:P17 ?k. ?k wdt:P297 ?iso} }'''%v)
    out={}
    for x in r:
        q=x['c']['value'].rsplit('/',1)[1];o=out.setdefault(q,{'links':int(x['links']['value']),'coords':set(),'iso':set()})
        if 'coord' in x: m=re.findall(r'-?\d+\.?\d*',x['coord']['value']);o['coords'].add((round(float(m[1]),4),round(float(m[0]),4)))
        if 'dpl' in x: o['desc']=x['dpl']['value']
        if 'iso' in x: o['iso'].add(x['iso']['value'])
        if 'ta' in x: o['ta']=x['ta']['value']
    return out
def record(d,idx,cities,wd):
    air=[x for x in d['want'] if x in idx]
    miss=[x for x in d['want'] if x not in idx]
    if miss: note(d['id'],'lotniska bez rekordu',miss)
    if not air: print('BRAK LOTNISK, pomijam',d['name']);note(d['id'],'pominiety','brak uzywalnego lotniska');return None
    r={'id':d['id'],'name':d['name'],'en':d['en'],'cc':d['cc'],'air':air,'tags':d['tags']}
    a0=idx[air[0]]
    if EXTRA.get(d['name']):
        r['lat'],r['lon']=EXTRA[d['name']]['lat'],EXTRA[d['name']]['lon'];note(d['id'],'wspolrzedne','Wikidata '+EXTRA[d['name']]['q'])
    elif d['name'] in WDCOORD:
        cs=sorted(wd.get(WDCOORD[d['name']],{}).get('coords') or [])
        if cs: r['lat'],r['lon']=cs[0];note(d['id'],'wspolrzedne','Wikidata '+WDCOORD[d['name']]+(' (kilka wartosci, wzieta pierwsza)' if len(cs)>1 else ''))
    else:
        n=GEONAME.get(d['name'],d['en'])
        hit=[c for c in cities if c['country']==d['cc'] and c['name']==n and dist(float(c['lat']),float(c['lng']),a0['lat'],a0['lon'])<320]
        if hit: r['lat'],r['lon']=round(float(hit[0]['lat']),4),round(float(hit[0]['lng']),4);note(d['id'],'wspolrzedne','GeoNames '+n)
    if 'lat' not in r: print('BRAK WSPOLRZEDNYCH, pomijam',d['name']);note(d['id'],'pominiety','brak wspolrzednych');return None
    q=QID.get(d['name']);w=wd.get(q)
    if w and d['cc'] in w['iso']:
        r['qid']=q;r['links']=w['links']
        if w.get('desc'): r['desc']=w['desc']
    else: r['links']=0;note(d['id'],'qid','brak lub inny kraj w Wikidata')
    if d['name'] in TA:
        try:
            j=json.loads(get(f"https://data.xotelo.com/api/list?location_key=g{TA[d['name']]}&limit=1&sort=best_value",tries=3,timeout=25))
            L=(j.get('result') or {}).get('list') or [];g=(L[0].get('geo') if L else None) or {}
            if L and g and dist(r['lat'],r['lon'],g['latitude'],g['longitude'])<=60: r['ta']=str(TA[d['name']]);r['hotels']=j['result']['total_count']
            else: note(d['id'],'ta','odrzucony: brak hoteli albo hotel dalej niz 60 km')
        except Exception as e: note(d['id'],'ta','Xotelo nie odpowiada: '+str(e)[:60])
        time.sleep(1)
    return r
def climate(ds):
    st=json.loads(gzip.decompress(get('https://bulk.meteostat.net/v2/stations/lite.json.gz',timeout=120)))
    st=[s for s in st if s['location']['latitude'] is not None]
    def normals(s,shift):
        try: raw=gzip.decompress(get(f"https://bulk.meteostat.net/v2/normals/{s['id']}.csv.gz",tries=2,timeout=20)).decode()
        except Exception: return None
        rows=[r for r in csv.reader(io.StringIO(raw)) if r[4] and r[3]]
        if not rows: return None
        last=max(int(r[1]) for r in rows);out={int(r[2]):r for r in rows if int(r[1])==last}
        if len(out)<12: return None
        f=lambda v:round(float(v)+shift,1) if shift else float(v)
        return {'tmin':[f(out[m][3]) for m in range(1,13)],'tmax':[f(out[m][4]) for m in range(1,13)],'rain':[float(out[m][5]) if out[m][5] else None for m in range(1,13)],'station':s['name'].get('en'),'period':last}
    for d in ds:
        near=sorted(st,key=lambda s:dist(d['lat'],d['lon'],s['location']['latitude'],s['location']['longitude']))[:40]
        # build_data3: stacje z normami do 150 km; build_data4: do 320 km z poprawka na wysokosc
        tried=set()
        for s in [s for s in near if (s.get('inventory') or {}).get('normals',{}).get('start')][:6]+near:
            if s['id'] in tried: continue
            tried.add(s['id']);k=dist(d['lat'],d['lon'],s['location']['latitude'],s['location']['longitude'])
            if k>320: break
            n=normals(s,0)
            if n:
                if all(v is None for v in n['rain']): n['rain']=[0]*12;note(d['id'],'opady','stacja bez opadow, wpisane 0 jak w build_data4')
                n['km']=round(k);d['climate']=n;break
            time.sleep(.3)
        if not d.get('climate'): note(d['id'],'klimat','brak stacji z normami do 320 km')
def sea(ds):
    for d in ds:
        if 'beach' not in d['tags'] or not d.get('climate'): continue
        err=None
        for extra in ('','&cell_selection=sea'):
            try:
                r=json.loads(get(f"https://marine-api.open-meteo.com/v1/marine?latitude={d['lat']}&longitude={d['lon']}&hourly=sea_surface_temperature&start_date=2025-01-01&end_date=2025-12-31&timezone=UTC{extra}",tries=6,timeout=40))
                h=r['hourly'];m=[[] for _ in range(12)]
                for t,v in zip(h['time'],h['sea_surface_temperature']):
                    if v is not None: m[int(t[5:7])-1].append(v)
                if all(m):
                    d['climate']['sea']=[round(sum(x)/len(x),1) for x in m]
                    if extra: note(d['id'],'morze','najblizsza komorka morska Open-Meteo (cell_selection=sea)')
                    break
            except Exception as e: err=str(e)[:60]
            time.sleep(4)
        if not d['climate'].get('sea'): note(d['id'],'morze','brak danych'+(' ('+err+')' if err else ''))
        time.sleep(4)
# Typy atrakcji jak w build_data3.py
T={'Q33506':'museum','Q207694':'museum','Q16970':'church','Q2977':'church','Q56242215':'church','Q16560':'palace','Q23413':'castle','Q4989906':'monument','Q174782':'square','Q22698':'park','Q570116':'sight','Q839954':'ruins','Q44613':'church','Q57821':'castle','Q1081138':'sight','Q12280':'bridge','Q2319498':'sight','Q40080':'beach','Q1107656':'park','Q43501':'zoo','Q162875':'monument','Q170980':'monument','Q39715':'sight','Q1497364':'sight','Q2065736':'museum','Q17431399':'museum','Q11707':'food','Q34442':'street','Q79007':'street','Q8502':'nature','Q34038':'nature','Q4421':'nature','Q179700':'monument','Q1244442':'sight','Q24354':'theatre','Q153562':'theatre','Q148319':'sight','Q45776':'sight','Q860861':'monument'}
def attractions(ds,A):
    """Atrakcje z Wikidata dla nowych kierunkow (zapytanie z build_data3) i filtr dziel sztuki z build_data5."""
    vals=' '.join('wd:'+k for k in T)
    for d in ds:
        if A.get(d['id']): continue
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
            A[d['id']]=sorted(seen.values(),key=lambda x:-x['l'])[:36]
        except Exception as e: note(d['id'],'atrakcje wikidata blad',str(e)[:80])
        print(' wikidata',d['name'],len(A.get(d['id'],[])),flush=True);time.sleep(1.5)
    ids=sorted({x['q'] for d in ds for x in A.get(d['id'],[])});bad=set()
    for i in range(0,len(ids),150):
        v=' '.join('wd:'+q for q in ids[i:i+150])
        bad|={r['i']['value'].rsplit('/',1)[1] for r in sparql('SELECT DISTINCT ?i WHERE { VALUES ?i {%s} ?i wdt:P31 ?t. VALUES ?t {wd:Q860861 wd:Q179700 wd:Q3305213 wd:Q838948} {?i wdt:P276 ?x} UNION {?i wdt:P195 ?x} }'%v)};time.sleep(1)
    for d in ds:
        if d['id'] in A: A[d['id']]=[x for x in A[d['id']] if x['q'] not in bad]
def shapes(ds,S):
    """Zarys kraju w formacie data/shapes.json (Natural Earth 1:50m, ten sam zbior co istniejace ksztalty)."""
    ccs=sorted({d['cc'] for d in ds if d['cc'] not in S and d['cc'] in ISON})
    if not ccs: return
    W=json.loads(get('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json',timeout=120));tr=W['transform']
    def arc(i):
        x=y=0;pts=[]
        for dx,dy in W['arcs'][i if i>=0 else ~i]: x+=dx;y+=dy;pts.append((x*tr['scale'][0]+tr['translate'][0],y*tr['scale'][1]+tr['translate'][1]))
        return pts if i>=0 else pts[::-1]
    def area(p): return abs(sum(p[i][0]*p[i-1][1]-p[i-1][0]*p[i][1] for i in range(len(p))))/2
    for cc in ccs:
        g=next(x for x in W['objects']['countries']['geometries'] if x.get('id') and int(x['id'])==ISON[cc])
        polys=[[sum((arc(i) for i in ring),[]) for ring in poly] for poly in (g['arcs'] if g['type']=='MultiPolygon' else [g['arcs']])]
        big=max(area(p[0]) for p in polys);pts=[(d['lon'],d['lat']) for d in ds if d['cc']==cc]
        near=lambda p:any(min(x for x,_ in p)-.2<=lo<=max(x for x,_ in p)+.2 and min(y for _,y in p)-.2<=la<=max(y for _,y in p)+.2 for lo,la in pts)
        keep=[p for p in polys if area(p[0])>=big*.01 or near(p[0])]
        P=[q for p in keep for q in p[0]];x0=min(x for x,_ in P);y1=max(y for _,y in P);y0=min(y for _,y in P);x1=max(x for x,_ in P)
        c=math.cos(math.radians((y0+y1)/2));k=100/max((x1-x0)*c,y1-y0)
        path=''
        for p in keep:
            ring=[];last=None
            for x,y in p[0]:
                t=(round((x-x0)*c*k,1),round((y1-y)*k,1))
                if t!=last: ring.append(t);last=t
            path+='M'+'L'.join(f'{a:.1f} {b:.1f}' for a,b in ring)+'Z'
        S[cc]={'b':[x0,y1,c,k],'d':path,'w':round((x1-x0)*c*k),'h':round((y1-y0)*k)}
        print(' ksztalt',cc,len(keep),'wielokatow',flush=True)
def main():
    P=ROOT+'/data/destinations.json';D=json.load(open(P,encoding='utf8'))
    new=read_new(D)
    if not new:
        print('nic nowego, uzupelniam tylko ksztalty krajow')
        SP=ROOT+'/data/shapes.json';S=json.load(open(SP,encoding='utf8'));shapes(D,S);dump(S,SP);return
    aps0=json.load(open(ROOT+'/data/airports.json',encoding='utf8'))
    aps,added,nofli,known=airports(new,aps0)
    for d in new:
        nf=[x for x in d['want'] if known is not None and x not in known]
        if nf: note(d['id'],'nieznane fli',nf)
    idx={a['iata']:a for a in aps}
    cp=os.environ.get('CITIES')
    cities=[] if EXTRA and all(EXTRA.get(d['name']) for d in new) else json.load(open(cp,encoding='utf8')) if cp else json.loads(get('https://raw.githubusercontent.com/lutangar/cities.json/master/cities.json',timeout=180))
    wd=wd_items(sorted(set(QID.values())|set(WDCOORD.values())))
    ds=[r for r in (record(d,idx,cities,wd) for d in new) if r]
    print('rekordy',len(ds),flush=True)
    climate(ds);print('klimat',sum(bool(d.get('climate')) for d in ds),flush=True)
    sea(ds);print('morze',sum(bool((d.get('climate') or {}).get('sea')) for d in ds),flush=True)
    # zapis: tylko dopisujemy
    dump(aps,ROOT+'/data/airports.json')
    dump(D+ds,P)
    tsv=open(ROOT+'/tools/destinations.tsv',encoding='utf8').read()
    lines={d['id']:d['line'] for d in new}
    with open(ROOT+'/tools/destinations.tsv','a',encoding='utf8') as f:
        if tsv and not tsv.endswith('\n'): f.write('\n')
        for d in ds: f.write(lines[d['id']]+'\n')
    A=json.load(open(ROOT+'/data/attractions.json',encoding='utf8'));n0=sum(len(v) for v in A.values())
    attractions(ds,A);dump(A,ROOT+'/data/attractions.json')
    print('atrakcje razem',n0,'->',sum(len(v) for v in A.values()),flush=True)
    SP=ROOT+'/data/shapes.json';S=json.load(open(SP,encoding='utf8'));shapes(D+ds,S);dump(S,SP)
    rep={d['id']:{'air':d['air'],'klimat':(d.get('climate') or {}).get('station'),'km':(d.get('climate') or {}).get('km'),'morze':bool((d.get('climate') or {}).get('sea')),'ta':d.get('ta'),'hotele':d.get('hotels'),'atrakcje_wd':len(A.get(d['id'],[])),**REPORT.get(d['id'],{})} for d in ds}
    rep['_lotniska_dodane']=[a['iata'] for a in added];rep['_nieznane_fli']=nofli;rep['_pominiete']={k:v for k,v in REPORT.items() if 'pominiety' in v}
    if os.environ.get('REPORT'): json.dump(rep,open(os.environ['REPORT'],'w',encoding='utf8'),ensure_ascii=False,indent=1)
    print(json.dumps(rep,ensure_ascii=False,indent=1))
    print('ONLY='+','.join(d['id'] for d in ds))
if __name__=='__main__': main()
