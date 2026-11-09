"""Wyjazdy w Polsce: autem od drzwi do drzwi, pociagiem albo samolotem, do tego nocleg.
Auto: trasa z OSRM, paliwo ze spalania i ceny podanej przez uzytkownika, oplaty tylko na platnych odcinkach autostrad.
Samolot: tylko prawdziwe loty z Google na te daty. Pociag: rozklad z Transitous, cena biletu to szacunek.
Niczego nie wymyslamy: czego nie da sie sprawdzic, tego nie liczymy i mowimy o tym wprost."""
import datetime as dt,logging,math,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
import access,climate,flights,geo,hotels,net,store
log=logging.getLogger('domestic')
JOBS={};_jl=threading.Lock()
PL_AIR=[a for a in geo.AIRPORTS.values() if a.get('cc')=='PL']

# Platne odcinki autostrad dla aut osobowych (kategoria 1). Zrodla sprawdzone 9.11.2026:
# A1 AmberOne Rusocin-Nowa Wies, ok. 152 km: 29,90 zl za cala trase (otomoto.pl, 4.07.2026).
# A2 Autostrada Wielkopolska od 11.09.2026: Swiecko-Nowy Tomysl 18 zl, Nowy Tomysl-Poznan, Poznan-Wrzesnia, Wrzesnia-Konin po 41 zl (tvn24.pl).
# A4 Katowice-Krakow: 18 zl na kazdej z dwoch bramek, Myslowice i Balice, od 1.04.2026 (autostrada-a4.com.pl);
#    od 15.03.2027 bezplatna dla osobowych (koniec koncesji, odpowiedz ministerstwa cytowana przez elektromobilni.pl).
A1_RATE=29.90/152
A2_SECTIONS=[(14.55,16.10,18,'A2 Świecko–Nowy Tomyśl'),(16.10,16.85,41,'A2 Nowy Tomyśl–Poznań'),(16.85,17.55,41,'A2 Poznań–Września'),(17.55,18.15,41,'A2 Września–Konin')]
A4_GATES=[(19.05,19.45,18,'A4 bramka Mysłowice'),(19.45,19.85,18,'A4 bramka Balice')]
A4_FREE=dt.date(2027,3,15)
TOLL_SRC='Stawki: A1 AmberOne, A2 Autostrada Wielkopolska i A4 Katowice–Kraków według cenników z 2026 roku. Pozostałe autostrady i drogi ekspresowe są dla osobówek bezpłatne.'
def _seg(geom):
    c=geom['coordinates']
    for (x1,y1),(x2,y2) in zip(c,c[1:]): yield (x1+x2)/2,(y1+y2)/2,geo.km(y1,x1,y2,x2)
def route(lat,lon,la,lo,day=None):
    """Trasa autem z oplatami za autostrady w jedna strone."""
    k=f'plr:{round(lat,3)},{round(lon,3)}:{round(la,3)},{round(lo,3)}'
    r,_=store.get(k)
    if r is None:
        j=net.fetch_json(f'https://router.project-osrm.org/route/v1/driving/{lon},{lat};{lo},{la}?overview=false&steps=true&geometries=geojson',cache=False,tries=2,timeout=25)
        R=j['routes'][0];a1=0.0;a2={};a4={}
        for s in R['legs'][0]['steps']:
            refs={x.strip() for x in (s.get('ref') or '').split(';')}
            if not refs&{'A1','A2','A4'}: continue
            for x,y,L in _seg(s['geometry']):
                if 'A1' in refs and 53.03<=y<=54.30 and 18.4<=x<=18.95: a1+=L
                if 'A2' in refs and 51.9<=y<=52.6:
                    for i,(w,e,_,_) in enumerate(A2_SECTIONS):
                        if w<=x<e: a2[i]=a2.get(i,0)+L
                if 'A4' in refs and 49.95<=y<=50.35:
                    for i,(w,e,_,_) in enumerate(A4_GATES):
                        if w<=x<e: a4[i]=a4.get(i,0)+L
        r={'km':round(R['distance']/1000),'drive':round(R['duration']/60*1.1),'a1':round(a1,1),'a2':{str(i):round(v,1) for i,v in a2.items()},'a4':{str(i):round(v,1) for i,v in a4.items()}}
        store.put(k,r,30*86400)
    items=[]
    if r['a1']>=5: items.append({'label':'A1 AmberOne','pln':round(r['a1']*A1_RATE,2)})
    for i,v in r['a2'].items():
        if v>=8: w,e,p,n=A2_SECTIONS[int(i)];items.append({'label':n,'pln':p})
    if not day or day<A4_FREE:
        for i,v in r['a4'].items():
            if v>=5: w,e,p,n=A4_GATES[int(i)];items.append({'label':n,'pln':p})
    m=r['drive'];stops=max(0,(m-1)//150)*20
    return {'km':r['km'],'min':m+stops,'drive':m,'tolls':round(sum(x['pln'] for x in items)),'tollItems':items,
            'map':f'https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={la},{lo}&travelmode=driving'}
def table(lat,lon,ds):
    """Czas i dystans do wielu miejsc naraz."""
    out={}
    for i in range(0,len(ds),60):
        part=ds[i:i+60];coords=';'.join([f'{lon},{lat}']+[f"{d['lon']},{d['lat']}" for d in part])
        try:
            t=net.fetch_json(f'https://router.project-osrm.org/table/v1/driving/{coords}?sources=0&annotations=duration,distance',ttl=30*86400,tries=2,timeout=30)
            for j,d in enumerate(part):
                s=t['durations'][0][j+1];m=t['distances'][0][j+1]
                if s is not None and m is not None: out[d['id']]={'km':round(m/1000),'min':round(s/60*1.1)}
        except Exception as e: log.warning('table %s',e)
    return out
def pick(q,lat,lon):
    t=q.get('dest') or {};mode=t.get('mode','anywhere');style=t.get('style')
    PL=[d for d in geo.DESTS if d['cc']=='PL']
    if mode=='city':
        ds=[geo.BYID[i] for i in t.get('ids',[]) if i in geo.BYID and geo.BYID[i]['cc']=='PL']
        if not ds: raise ValueError('Wybierz miejsce w Polsce')
        return ds,table(lat,lon,ds),[]
    ds=[d for d in PL if not style or style in d['tags']]
    if not ds: raise ValueError('Brak miejsc w tym stylu')
    T=table(lat,lon,ds);notes=[]
    maxh=float(q.get('maxHours') or 0)
    near=[d for d in ds if d['id'] in T and T[d['id']]['km']>=25]
    if maxh:
        fit=[d for d in near if T[d['id']]['min']<=maxh*60]
        if not fit:
            fit=sorted(near,key=lambda d:T[d['id']]['min'])[:4]
            if fit: notes.append({'text':f'W zasięgu {maxh:g} h jazdy nie ma takich miejsc. Pokazuję najbliższe.'})
        near=fit
    near.sort(key=lambda d:-d.get('links',0))
    return near[:8],T,notes
def dates(q):
    """Lista mozliwych terminow (zameldowanie, wymeldowanie)."""
    import search
    w=q.get('when') or {}
    a,b,nights,_=search.window(w)
    if w.get('mode')=='dates': return [(a,a+dt.timedelta(days=nights[0]))]
    n=nights[0];last=b-dt.timedelta(days=n) if (b-a).days>n else a
    return [(s,s+dt.timedelta(days=n)) for s in search.sample_days(a,max(a,last),3)]
def car_cost(r,cfg):
    L=float(cfg.get('consumption') or 7.5);F=float(cfg.get('fuelPrice') or 5.99)
    fuel=round(r['km']*2*L/100*F)
    return {'fuel':fuel,'tolls':r['tolls']*2,'total':fuel+r['tolls']*2}
def plane(home,d,ci,co,A,C,cfg,car_min):
    """Lot krajowy z dojazdem na lotnisko i z lotniska. Tylko gdy autem jest daleko i taki lot istnieje na te daty."""
    if car_min<240: return None
    oa=sorted((geo.km(home[0],home[1],a['lat'],a['lon']),a) for a in PL_AIR);oa=[a for k,a in oa if k<=120][:2]
    da=sorted((geo.km(d['lat'],d['lon'],a['lat'],a['lon']),a) for a in PL_AIR);da=[a for k,a in da if k<=90][:2]
    best=None;P=A+C
    for o in oa:
        for z in da:
            if o['iata']==z['iata'] or geo.km(o['lat'],o['lon'],z['lat'],z['lon'])<200: continue
            try: r,_=flights.roundtrip(o['iata'],z['iata'],ci,co,A,C,3)
            except Exception as e: log.warning('pl rt %s',e);r=[]
            for x in r or []:
                if not best or x['total']<best[0]['total']: best=(x,o,z)
    if not best: return None
    f,o,z=best;days=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days+1
    drv=access.drive_table(home[0],home[1],[o['iata']])[o['iata']]
    acc=access.cost('car',o['iata'],drv,days,P,{**cfg,'tollOneWay':0})
    tk=round(geo.km(z['lat'],z['lon'],d['lat'],d['lon'])*1.25)
    tr=access.cost('public',z['iata'],{'km':tk},days,P,{})
    L=f['out']['legs'];B=f['back']['legs']
    tmin=drv['min']+90+f['out']['min']+30+round(tk/40*60)
    return {'from':o['iata'],'to':z['iata'],'fromCity':o.get('city'),'toCity':z.get('city'),'tickets':round(f['total']),'flight':f,
            'access':acc,'transfer':{'km':tk,'pln':tr['total']},'total':round(f['total'])+acc['total']+tr['total'],'min':tmin,
            'dep':L[0]['dep'],'arr':L[-1]['arr'],'bdep':B[0]['dep'],'barr':B[-1]['arr'],'stops':len(L)-1,
            'url':f"https://www.google.com/travel/flights?q=Flights%20from%20{o['iata']}%20to%20{z['iata']}%20on%20{ci}%20through%20{co}&curr=PLN&hl=pl"}
def train(home,d,ci,P,km):
    import plan
    try: tr=plan.transit(home,(d['lat'],d['lon']),dt.datetime.combine(dt.date.fromisoformat(ci),dt.time(8,0)))
    except Exception: tr=None
    if not tr: return None
    est=round(max(25,km*access.PUBLIC_ZL_KM)*2*P)
    return {'min':tr['min'],'transfers':tr['transfers'],'legs':tr['legs'],'sample':tr['sample'],'tickets':est,'total':est,
            'links':[{'site':'PKP Intercity','url':'https://www.intercity.pl/'},{'site':'Koleo','url':'https://koleo.pl/'},
                     {'site':'Google Maps','url':f"https://www.google.com/maps/dir/?api=1&origin={home[0]},{home[1]}&destination={d['lat']},{d['lon']}&travelmode=transit"}]}
def one(job,q,d,T,ds_,home,A,C,cfg):
    P=A+C;r=None
    try: r=route(home[0],home[1],d['lat'],d['lon'],ds_[0][0])
    except Exception as e: log.warning('route %s %s',d['id'],e)
    if r is None and d['id'] in T: r={'km':T[d['id']]['km'],'min':T[d['id']]['min'],'drive':T[d['id']]['min'],'tolls':0,'tollItems':[],'est':True,'map':f"https://www.google.com/maps/dir/?api=1&origin={home[0]},{home[1]}&destination={d['lat']},{d['lon']}&travelmode=driving"}
    if r is None: return None
    best=None
    for ci,co in ds_:
        try: h=hotels.estimate(d,ci.isoformat(),co.isoformat(),A,C)
        except Exception: h=None
        if h and (not best or h['total']<best[1]['total']): best=((ci,co),h)
        if len(ds_)==1: break
    (ci,co),h=best if best else (ds_[0],None)
    ci,co=ci.isoformat(),co.isoformat()
    car={**r,**car_cost(r,cfg)}
    if r.get('est'): car['note']='Trasa policzona w przybliżeniu, bez opłat za autostrady.'
    if r['min']>540: car['note']=f"Około {r['min']//60} h jazdy. Rozważ nocleg po drodze."
    tr=train(home,d,ci,P,r['km'])
    pl=None
    try: pl=plane(home,d,ci,co,A,C,cfg,r['min'])
    except Exception as e: log.warning('plane %s',e)
    m=int(ci[5:7])
    o={'id':uuid.uuid4().hex[:10],'dest':{k:d.get(k) for k in('id','name','cc','lat','lon','tags','desc','ta')},'dep':ci,'ret':co,
       'nights':(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days,'pax':{'adults':A,'children':C},'hotelEst':h,
       'car':car,'train':tr,'plane':pl,'climate':{'month':climate.month(d,m)}}
    modes={'car':car['total']}
    if tr: modes['train']=tr['total']
    if pl: modes['plane']=pl['total']
    o['best']=min(modes,key=modes.get);o['transport']=modes[o['best']]
    o['total']=o['transport']+(h['total'] if h else 0)
    return o
def run(job,q):
    def step(t,p): job['label']=t;job['progress']=round(p,3)
    try:
        lat=float(q['origin']['lat']);lon=float(q['origin']['lon']);home=(lat,lon)
        pax=q.get('pax') or {};A=max(1,int(pax.get('adults',1)));C=max(0,int(pax.get('children',0)))
        cfg=dict(q.get('transport') or {})
        step('Wybieram miejsca',.05)
        ds_=dates(q)
        step('Liczę trasy autem',.1)
        dests,T,notes=pick(q,lat,lon)
        if not dests: raise ValueError('Nie znalazłem miejsc w zasięgu')
        out=[];done=[0]
        def go(d):
            try: o=one(job,q,d,T,ds_,home,A,C,cfg)
            except Exception: log.exception('pl %s',d['id']);o=None
            done[0]+=1;step(f"Sprawdzam {d['name']}: trasa, noclegi, pociąg i loty",.12+.85*done[0]/len(dests))
            return o
        with ThreadPoolExecutor(3) as ex: out=[o for o in ex.map(go,dests) if o]
        if not out: raise ValueError('Nie udało się sprawdzić żadnego miejsca. Spróbuj za chwilę.')
        out.sort(key=lambda o:(o['hotelEst'] is None,o['total']))
        import plan
        hol=plan.holidays('PL',min(o['dep'] for o in out),max(o['ret'] for o in out))
        if hol: notes.append({'text':'W tym terminie są dni wolne: '+', '.join(f"{h['name']} ({h['date'][8:]}.{h['date'][5:7]})" for h in hol)+'. Część restauracji, muzeów i sklepów może być wtedy zamknięta albo czynna krócej. Sprawdź godziny przed wyjazdem.'})
        job['result']={'kind':'pl','options':out,'notes':notes,'tollSrc':TOLL_SRC,'at':time.time()};job['state']='done';job['progress']=1
    except ValueError as e: job['state']='error';job['error']=str(e)
    except Exception: log.exception('domestic');job['state']='error';job['error']='Nie udało się wyszukać. Spróbuj za chwilę.'
def start(q):
    if not (q.get('origin') or {}).get('lat'): raise ValueError('Ustaw miejsce wyjazdu')
    with _jl:
        for k in [k for k,v in JOBS.items() if time.time()-v['t']>3*3600]: del JOBS[k]
        if sum(1 for v in JOBS.values() if v['state']=='running')>=4: raise ValueError('Serwer szuka już kilku wyjazdów. Spróbuj za minutę.')
        j={'id':uuid.uuid4().hex[:12],'state':'running','label':'Start','progress':0,'t':time.time()};JOBS[j['id']]=j
    threading.Thread(target=run,args=(j,q),daemon=True).start()
    return j['id']
def status(i):
    j=JOBS.get(i)
    if not j: raise ValueError('Wyszukiwanie wygasło. Uruchom je jeszcze raz.')
    return {k:j.get(k) for k in('state','label','progress','result','error')}
def plan_trip(b):
    """Plan wyjazdu po wybraniu sposobu dojazdu i noclegu."""
    import plan
    o=b['option'];mode=b.get('mode') if b.get('mode') in('car','train','plane') else 'car'
    d=geo.BYID.get(o['dest']['id'])
    if not d: raise ValueError('Nie znam tego miejsca')
    home=b.get('home') or {};H=b.get('hotel') or {}
    body={'dest':{'id':d['id']},'from':o['dep'],'to':o['ret'],'mode':mode,'home':home,'pax':o['pax'],'transport':b.get('transport'),'prefs':b.get('prefs') or {},
          'hotelObj':{'name':str(H.get('name') or 'Nocleg do wyboru')[:80],'lat':float(H.get('lat') or d['lat']),'lon':float(H.get('lon') or d['lon']),'bestTotal':H.get('bestTotal'),'breakfast':bool(H.get('breakfast')),'url':H.get('url'),'prices':H.get('prices')}}
    if mode=='car':
        c=o['car'];body['arrive']=b.get('arrive') or '15:00';body['leave']=b.get('leave') or '11:00'
        body['extra']=[{'label':x['label']+' ×2','pln':round(x['pln']*2),'est':True} for x in c.get('tollItems',[])]
    elif mode=='plane':
        p=o['plane'];arr=dt.datetime.fromisoformat(p['arr']);bd=dt.datetime.fromisoformat(p['bdep'])
        tmin=round(p['transfer']['km']/40*60)+30
        body['arrive']=(arr+dt.timedelta(minutes=tmin)).strftime('%H:%M');body['leave']=(bd-dt.timedelta(minutes=tmin+90)).strftime('%H:%M')
        body['flightInfo']=p
        body['extra']=[{'label':f"Bilety {p['from']}–{p['to']} w obie strony",'pln':p['tickets'],'est':False}]+[{**x} for x in p['access']['items']]+[{'label':f"Dojazd z lotniska {p['transfer']['km']} km, w obie strony",'pln':p['transfer']['pln'],'est':True}]
    else:
        body['arrive']=b.get('arrive') or '15:00';body['leave']=b.get('leave') or '11:00'
        body['extra']=[{'label':'Bilety kolejowe w obie strony','pln':o['train']['tickets'],'est':True}]
    body['pl']=True
    return plan.manual(body)
