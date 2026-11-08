"""Porownanie oferty biura z tym samym wyjazdem na wlasna reke: prawdziwy lot z Google i cena tego hotelu z Google.
Niczego nie szacujemy na oko. Czego nie znajdziemy, tego nie liczymy i mowimy o tym wprost."""
import datetime as dt,logging,re,threading,time,unicodedata,uuid
import flights,geo,ghotels,net,store
log=logging.getLogger('compare')
JOBS={};_l=threading.Lock()
def _norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return [w for w in re.findall(r'[a-z0-9]+',s) if w not in('hotel','resort','spa','the','and','by','apartments','apartamenty','aparthotel','suites','beach','club')]
def same_hotel(a,b):
    """Czy dwie nazwy to ten sam hotel: wiekszosc znaczacych slow musi sie zgadzac."""
    A,B=set(_norm(a)),set(_norm(b))
    if not A or not B: return False
    return len(A&B)/min(len(A),len(B))>=0.67
def find_hotel(name,place,ci,co):
    """Hotel z oferty w Google Hotels: (hotel, zgodny?) albo (None, None)."""
    town=(place or '').split(',')[-1].strip()
    for q in (f'{name} {town} from',f'hotels in {town} from'):
        a,b=dt.date.fromisoformat(ci),dt.date.fromisoformat(co)
        f=lambda d:f'{ghotels.MONTHS[d.month-1]} {d.day} {d.year}'
        r=ghotels.fetch(f'{q} {f(a)} to {f(b)}')
        if not r: continue
        H=[h for h in (ghotels.parse(x,ci,co) for x in r[0]) if h]
        for h in H:
            if same_hotel(name,h['name']):
                k=net.fx(h['currency']);h['totalPln']=round(h['total']*k);return h,True
    return None,None
def airports_near(lat,lon,n=2,maxkm=220):
    L=sorted(((geo.km(lat,lon,a['lat'],a['lon']),a) for a in geo.AIRPORTS.values() if a.get('cc')!='PL'),key=lambda x:x[0])
    return [a['iata'] for k,a in L if k<=maxkm][:n]
FROM={'WAW':['WAW','WMI'],'WMI':['WMI','WAW'],'RDO':['RDO','WAW']}
def best_flight(orig,dests,dep,ret,A):
    best=None
    for o in FROM.get(orig,[orig]):
        for d in dests:
            try: r,_=flights.roundtrip(o,d,dep,ret,A,0,3)
            except Exception as e: log.warning('cmp rt %s',e);r=[]
            for x in r or []:
                if not best or x['total']<best['total']: best=dict(x,o=o,d=d)
    return best
def run(job,x):
    try:
        A=int(x.get('adults') or 2);ci=x['dep'];co=x.get('ret')
        if not co: raise ValueError('Ta oferta nie ma daty powrotu')
        job['step']='Szukam tego hotelu w Google'
        h,ok=find_hotel(x['name'],x.get('place',''),ci,co)
        pos=(h['lat'],h['lon']) if h else None
        if not pos:
            import plan
            g=plan.geocode(f"{x['name']}, {x.get('place','')}") or plan.geocode(x.get('place','').split(',')[-1])
            pos=(g['lat'],g['lon']) if g else None
        if not pos: raise ValueError('Nie udało się ustalić, gdzie jest ten hotel')
        dests=airports_near(*pos)
        job['step']='Szukam lotów'
        orig=x.get('from') if re.fullmatch(r'[A-Z]{3}',x.get('from') or '') else 'WAW'
        f=best_flight(orig,dests,ci,co,A)
        res={'hotel':None,'flight':None,'notes':[]}
        if f:
            L=f['out']['legs'];B=f['back']['legs']
            res['flight']={'total':round(f['total']),'from':f['o'],'to':f['d'],'stops':len(L)-1,'backStops':len(B)-1,'airlines':sorted({l['airlineName'] for l in L+B}),'dep':L[0]['dep'],'arr':L[-1]['arr'],'bdep':B[0]['dep'],'barr':B[-1]['arr'],
                           'url':f"https://www.google.com/travel/flights?q=Flights%20from%20{f['o']}%20to%20{f['d']}%20on%20{ci}%20through%20{co}&curr=PLN&hl=pl"}
        else: res['notes'].append('Nie znalazłem regularnego lotu w te dni. Biura latają czarterami, których miejsc zwykle nie da się kupić osobno.')
        if h and ok:
            res['hotel']={'name':h['name'],'total':h['totalPln'],'stars':h.get('stars'),'url':'https://www.google.com/travel/search?q='+net.urllib.parse.quote(h['name'])+'&hl=pl&curr=PLN'}
        else: res['notes'].append('Nie znalazłem tego hotelu z ceną na te daty w Google.')
        if res['hotel'] and res['flight']:
            res['own']=res['hotel']['total']+res['flight']['total'];res['agency']=int(x.get('total') or 0) or None
            if res['agency']: res['diff']=res['agency']-res['own']
        b=(x.get('board') or '').lower()
        if res['hotel'] and ('all' in b or 'pełne' in b or 'obiad' in b or 'kolac' in b):
            res['notes'].append(f"W biurze masz {x.get('board')}. Cena hotelu z Google to zwykle sam pokój albo ze śniadaniem, więc jedzenie trzeba doliczyć.")
        res['notes'].append('Na własną rękę nie ma transferu z lotniska, rezydenta ani gwarancji z funduszu turystycznego. Taksówkę z lotniska doliczasz sam.')
        job['res']=res;job['state']='done'
    except ValueError as e: job['state']='err';job['error']=str(e)
    except Exception: log.exception('compare');job['state']='err';job['error']='Nie udało się porównać. Spróbuj za chwilę.'
def start(x):
    for k in('name','dep'):
        if not x.get(k): raise ValueError('Niepełna oferta')
    sig=f"{x.get('op')}|{x['name']}|{x['dep']}|{x.get('ret')}|{x.get('from')}"
    with _l:
        for k in [k for k,v in JOBS.items() if time.time()-v['t']>6*3600]: del JOBS[k]
        for v in JOBS.values():
            if v['sig']==sig and v['state']!='err': return v['id']
        if sum(1 for v in JOBS.values() if v['state']=='run')>=3: raise ValueError('Serwer porównuje już kilka ofert. Spróbuj za minutę.')
        j={'id':uuid.uuid4().hex[:12],'sig':sig,'state':'run','step':'Start','t':time.time()};JOBS[j['id']]=j
    threading.Thread(target=run,args=(j,x),daemon=True).start()
    return j['id']
def status(i):
    j=JOBS.get(i)
    if not j: raise KeyError('id')
    return {k:j.get(k) for k in('state','step','res','error')}
