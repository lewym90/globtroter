"""Silnik wyszukiwania. Trzy kroki, tak zeby jak najmniej pytac Google:
1. ROZPOZNANIE: kilka dat, wszystkie lotniska naraz, ceny kazdej pary.
2. KALENDARZ: najlepsze pary, cena dla kazdej daty wylotu.
3. POTWIERDZENIE: konkretne loty dla najlepszych wariantow."""
import calendar as cal,datetime as dt,itertools,math,threading,time,uuid
import access,climate,flights,geo,hotels,links,store
JOBS={};_jl=threading.Lock()
MAXD=12
LCC={'FR','W6','U2','VY','HV','V7','LS','EW','DY'}
def chunk(x,n): return [x[i:i+n] for i in range(0,len(x),n)]
def window(w):
    """Zwraca (start,koniec,lista noclegow,miesiac)."""
    today=dt.date.today();min_day=today+dt.timedelta(days=1)
    if w.get('mode')=='dates':
        a=dt.date.fromisoformat(w['from']);b=dt.date.fromisoformat(w['to'])
        if b<=a: raise ValueError('Data powrotu musi być po dacie wylotu')
        if a<min_day: raise ValueError('Data wylotu musi być w przyszłości')
        return a,a,[(b-a).days],a.month
    nights=sorted({max(1,int(n)) for n in (w.get('nights') or [7])})[:3]
    if w.get('mode')=='month':
        y,m=int(w['year']),int(w['month'])
        a=max(dt.date(y,m,1),min_day);b=dt.date(y,m,cal.monthrange(y,m)[1])
    else:
        a=max(dt.date.fromisoformat(w['from']),min_day);b=dt.date.fromisoformat(w['to'])
    if b<a: raise ValueError('Ten termin już minął')
    return a,b,nights,a.month
def pick_dests(q,month):
    """Zwraca kierunki do sprawdzenia i uwagi. Klimat decyduje przy wyborze stylu."""
    t=q.get('dest',{});mode=t.get('mode','city');notes=[]
    style=t.get('style') if mode!='city' else None
    if mode=='city':
        ds=[geo.BYID[i] for i in t.get('ids',[]) if i in geo.BYID]
        if not ds: raise ValueError('Nie znam tego miejsca')
    elif mode=='country':
        ds=[d for d in geo.DESTS if d['cc'] in t.get('countries',[])]
        if style: ds=[d for d in ds if style in d['tags']] or ds
        if not ds: raise ValueError('Brak kierunków w tym kraju')
    else:
        ds=[d for d in geo.DESTS if not style or style in d['tags']]
    scored=[]
    for d in ds:
        s,why=climate.fit(d,month,style or 'city')
        scored.append((s,d,why))
    unfit=[(d,why) for s,d,why in scored if style=='beach' and s is not None and s<0.55]
    if style=='beach' and mode!='anywhere' and unfit and len(unfit)==len(scored):
        best=sorted([(climate.fit(d,month,'beach')[0] or 0,d) for d in geo.DESTS if 'beach' in d['tags']],key=lambda x:-x[0])[:4]
        notes.append({'kind':'climate','text':f"W tym miesiącu {unfit[0][0]['name']} nie nadaje się na plażowanie. {unfit[0][1]}.",
            'alternatives':[{'id':d['id'],'name':d['name'],'fit':climate.month(d,month)} for _,d in best]})
    pool=[x for x in scored if not(style in('beach','ski') and mode=='anywhere' and (x[0] or 0)<0.55)] or scored
    pool.sort(key=lambda x:(-(x[0] if x[0] is not None else .5),-x[1].get('links',0)))
    res=[];seen={}
    for s,d,why in pool:
        if mode=='anywhere' and seen.get(d['cc'],0)>=2: continue
        res.append(d);seen[d['cc']]=seen.get(d['cc'],0)+1
        if len(res)>=MAXD: break
    return res,notes
def sample_days(a,b,n=3):
    if a==b: return [a]
    span=(b-a).days
    return sorted({a+dt.timedelta(days=round(span*(i+.5)/n)) for i in range(n)})
def leave_home(dep_iso,drive,mode,schengen=True):
    d=dt.datetime.fromisoformat(dep_iso)
    buf=120 if schengen else 150
    extra=25 if mode=='car' else 10
    # Czas w aucie: bufor 15% i minimum 20 minut na korki
    road=round(drive['min']*1.15)+20
    return (d-dt.timedelta(minutes=buf+extra+road)).isoformat(timespec='minutes'),buf
NONSCH={'GB','IE','CY','TR','RS','BA','ME','AL','MK','MD','GE','MA','RO','BG'}
NONSCH-={'RO','BG'}
def run(job,q):
    def step(t,p):
        job['label']=t;job['progress']=round(p,3)
    try:
        lat=float(q['origin']['lat']);lon=float(q['origin']['lon'])
        pax=q.get('pax') or {};A=max(1,int(pax.get('adults',1)));C=max(0,int(pax.get('children',0)));P=A+C
        a,b,nights,month=window(q.get('when') or {})
        dests,notes=pick_dests(q,month)
        ors=access.nearby(lat,lon,int(q.get('radius',450)),q.get('originsManual'))
        if not ors: raise ValueError('Brak lotnisk w zasięgu')
        ors=ors[:16]
        codes=[x[1]['iata'] for x in ors]
        step('Liczę drogę na lotniska',.03)
        drive=access.drive_table(lat,lon,codes)
        mode=q.get('transport',{}).get('mode','car');cfg=dict(q.get('transport',{}))
        adest={}
        for d in dests:
            for x in d['air']: adest.setdefault(x,[]).append(d)
        air=list(adest)
        days=sample_days(a,b,1 if a==b else (2 if len(dests)>3 else 3))
        st=0 if q.get('direct') else None
        batches=[(o,d,day) for day in days for o in chunk(codes,7) for d in chunk(air,7)]
        best={};stat={'ok':0,'failed':0}
        for i,(o,d,day) in enumerate(batches):
            step(f"Sprawdzam rynek: {day.day}.{day.month:02d}, {len(o)} lotnisk",.05+.4*i/len(batches))
            try:
                r,_=flights.oneway(o,d,day.isoformat(),1,0,st)
                stat['ok']+=1
                for f in r:
                    k=(f['legs'][0]['from'],f['legs'][-1]['to'])
                    if k not in best or f['price']<best[k]['price']: best[k]={'price':f['price'],'stops':f['stops'],'day':day.isoformat()}
            except flights.Unavailable: stat['failed']+=1
        if not best:
            if stat['failed']: raise flights.Unavailable('Google Flights nie odpowiada')
            job.update(state='done',result={'options':[],'notes':notes,'coverage':stat,'empty':True});return
        # Wstepny koszt od drzwi do drzwi
        n0=nights[0]
        def est(k):
            o,dd=k;drv=drive[o];c=dict(cfg)
            if mode=='car' or mode=='dropoff':c['tollOneWay']=0
            return best[k]['price']*2*P+access.cost(mode,o,drv,n0+1,P,c)['total']
        chosen=[]
        for d in dests:
            ks=sorted([k for k in best if k[1] in d['air']],key=est)[:3]
            near=[k for k in sorted(best,key=lambda k:drive[k[0]]['km']) if k[1] in d['air']][:1]
            for k in ks+near:
                if k not in chosen: chosen.append(k)
        chosen=sorted(chosen,key=est)[:10 if len(dests)>1 else 8]
        grids={}
        for i,((o,dd),n) in enumerate(itertools.product(chosen,nights)):
            step(f"Kalendarz cen {o} → {dd}",.45+.3*i/(len(chosen)*len(nights)))
            try:
                end=min(b,a+dt.timedelta(days=59))
                if a==b:
                    r,_=flights.calendar(o,dd,a.isoformat(),a.isoformat(),n,1,0,st)
                else:r,_=flights.calendar(o,dd,a.isoformat(),end.isoformat(),n,1,0,st)
                r=[x for x in r if dt.date.fromisoformat(x['dep'])>=a and dt.date.fromisoformat(x['dep'])<=b]
                grids[(o,dd,n)]=r;stat['ok']+=1
            except flights.Unavailable: stat['failed']+=1
        # Warianty: najtanszy termin dla pary i dlugosci
        cand=[]
        for (o,dd,n),g in grids.items():
            if not g: continue
            top=min(g,key=lambda x:x['price'])
            cand.append({'o':o,'d':dd,'n':n,'dep':top['dep'],'ret':top['ret'],'grid':g,'one':top['price']})
        def full(c):
            cc=dict(cfg)
            return c['one']*P+access.cost(mode,c['o'],drive[c['o']],c['n']+1,P,{**cc,'tollOneWay':0})['total']
        cand.sort(key=full)
        tocheck=[];seen={}
        for c in cand:
            ds=adest[c['d']][0]['id']
            if seen.get(ds,0)>=(3 if len(dests)==1 else 2) or len(tocheck)>=(6 if len(dests)==1 else 8): continue
            tocheck.append(c);seen[ds]=seen.get(ds,0)+1
        opts=[]
        for i,c in enumerate(tocheck):
            step(f"Sprawdzam noclegi {adest[c['d']][0]['name']}",.75+.1*i/max(1,len(tocheck)))
            best_dates(c,adest[c['d']][0],A,C,P)
            step(f"Potwierdzam loty {c['o']} → {c['d']}",.85+.12*i/max(1,len(tocheck)))
            rt=None;checked=None
            try:
                r,age=flights.roundtrip(c['o'],c['d'],c['dep'],c['ret'],A,C,5,st)
                stat['ok']+=1
                if r: rt=prefer(r,q);checked=time.time()-age
            except flights.Unavailable: stat['failed']+=1
            o=build(c,rt,checked,q,drive,mode,cfg,A,C,adest,lat,lon,month,best)
            opts.append(o)
        opts.sort(key=lambda o:(o['hotelEst'] is None,o['totalWithHotel']))
        compare_airports(opts,best,drive,mode,cfg,P,codes,lat,lon)
        step('Gotowe',1)
        job.update(state='done',result={'options':opts,'notes':notes,'coverage':stat,'empty':not opts,'month':month,'at':time.time(),
            'partial':stat['failed']>0})
    except ValueError as e: job.update(state='error',error=str(e))
    except flights.Unavailable as e:
        job.update(state='error',error='Google Flights chwilowo nie odpowiada. Nie wiemy, jakie są ceny, więc niczego nie pokazujemy. Spróbuj za kilka minut.',retry=True)
    except Exception as e:
        import logging;logging.exception('search');job.update(state='error',error='Wyszukiwanie przerwane przez błąd serwera. Spróbuj ponownie.',retry=True)
def prefer(r,q):
    """Uwzglednia godziny: najpierw loty nie wczesniej niz wskazana godzina."""
    h=q.get('earliest')
    if not h: return r
    ok=[x for x in r if int(x['out']['legs'][0]['dep'][11:13])>=int(h)]
    return ok+[x for x in r if x not in ok] if ok else r
def build(c,rt,checked,q,drive,mode,cfg,A,C,adest,lat,lon,month,best):
    P=A+C;o,dd=c['o'],c['d'];d=adest[dd][0];drv=drive[o]
    days=c['n']+1
    tc=dict(cfg)
    if mode in('car','dropoff'): tc['tollOneWay']=access.tolls(lat,lon,o)
    acc=access.cost(mode,o,drv,days,P,tc)
    warn=[]
    if tc.get('tollOneWay') is None and mode!='public': warn.append('Nie udało się policzyć opłat za autostrady.')
    res={'id':uuid.uuid4().hex[:10],'dest':{k:d.get(k) for k in('id','name','cc','lat','lon','tags','desc','ta')},'from':o,'to':dd,'fromName':aname(o),'fromGen':agen(o),'toName':geo.AIRPORTS[dd]['city'],
        'dep':c['dep'],'ret':c['ret'],'nights':c['n'],'pax':{'adults':A,'children':C},'calendar':c['grid'],'access':acc,'drive':drv}
    bag=q.get('bags') or {}
    if rt:
        f=rt[0];res.update(tickets=f['total'],flight=f,alternatives=rt[1:],verified=True,checkedAt=checked)
    else:
        res.update(tickets=c['one']*P,flight=None,alternatives=[],verified=False,checkedAt=None)
        warn.append('Nie udało się potwierdzić konkretnych lotów. To cena z kalendarza dla jednej osoby razy liczba osób.')
    bags=0;carr=res['flight']['out']['legs'][0]['airline'] if res['flight'] else None
    if carr in LCC:
        bags=(int(bag.get('cabin',0))*130+int(bag.get('checked',0))*220)*2
        res['bagNote']='Tania linia: bilet zwykle obejmuje tylko mały plecak. Dopłata za bagaż to szacunek, sprawdź przy zakupie.'
    res['bags']=bags
    res['hotelEst']=c['hotelEst'] if 'hotelEst' in c else hotels.estimate(d,c['dep'],c['ret'],A,C)
    res['tickets']=round(res['tickets']);res['total']=res['tickets']+acc['total']+bags
    res['totalWithHotel']=res['total']+(res['hotelEst']['total'] if res['hotelEst'] else 0)
    res['perPerson']=round(res['total']/P)
    if res['flight']:
        L=res['flight']['out']['legs'][0];lh,buf=leave_home(L['dep'],drv,mode,d['cc'] not in NONSCH)
        res['leaveHome']=lh;res['airportBuffer']=buf
        h=int(lh[11:13])
        if h<4 or lh[:10]<L['dep'][:10]: warn.append(f"Wylot o {L['dep'][11:]}: z domu trzeba wyjechać o {lh[11:]}"+(' poprzedniego dnia.' if lh[:10]<L['dep'][:10] else '.'))
        if res['flight']['out'].get('selfTransfer') or res['flight']['back'].get('selfTransfer'): warn.append('Przesiadka na osobnych biletach: spóźnienie pierwszego lotu to Twoje ryzyko.')
    dq=q.get('dest') or {}
    s,why=climate.fit(d,month,(dq.get('style') if dq.get('mode')!='city' else None) or 'city')
    res['climate']={'month':climate.month(d,month),'score':s,'why':why}
    res['warnings']=warn
    res['links']=links.flight_links(o,dd,c['dep'],c['ret'],A,C,carr)
    return res
NAMES={'WAW':('Warszawa Chopin','Warszawy (Chopin)'),'WMI':('Warszawa Modlin','Modlina'),'RDO':('Warszawa Radom','Radomia'),'KRK':('Kraków','Krakowa'),'KTW':('Katowice','Katowic'),'GDN':('Gdańsk','Gdańska'),'WRO':('Wrocław','Wrocławia'),'POZ':('Poznań','Poznania'),'LUZ':('Lublin','Lublina'),'RZE':('Rzeszów','Rzeszowa'),'SZZ':('Szczecin','Szczecina'),'BZG':('Bydgoszcz','Bydgoszczy'),'LCJ':('Łódź','Łodzi'),'SZY':('Olsztyn-Mazury','Olsztyna'),'IEG':('Zielona Góra','Zielonej Góry')}
def aname(c): return NAMES.get(c,(geo.AIRPORTS[c]['city'],))[0]
def agen(c):
    n=NAMES.get(c);return n[1] if n else geo.AIRPORTS[c]['city']
def best_dates(c,d,A,C,P):
    """Wybiera termin po sumie lot + nocleg. Najtanszy lot czasem wypada w tygodniu drogich hoteli."""
    g=sorted(c['grid'],key=lambda x:x['price']);picks=[]
    for x in g:
        if x['price']>g[0]['price']*1.35: break
        day=dt.date.fromisoformat(x['dep'])
        if all(abs((day-dt.date.fromisoformat(y['dep'])).days)>=6 for y in picks): picks.append(x)
        if len(picks)==3: break
    bestv=None
    for x in picks:
        e=hotels.estimate(d,x['dep'],x['ret'],A,C)
        v=x['price']*P+(e['total'] if e else 0)
        if bestv is None or v<bestv[0]: bestv=(v,x,e)
    if bestv:
        c['dep'],c['ret'],c['one']=bestv[1]['dep'],bestv[1]['ret'],bestv[1]['price']
        c['hotelEst']=bestv[2]
def compare_airports(opts,best,drive,mode,cfg,P,codes,lat,lon):
    """Dla kazdego celu pelne porownanie lotnisk: te z potwierdzona cena, te z cena rozpoznawcza i te bez lotow."""
    by={}
    for o in opts: by.setdefault(o['dest']['id'],[]).append(o)
    for did,lst in by.items():
        full=lambda o:o['total']+(o['hotelEst']['total'] if o.get('hotelEst') else 0)
        lst.sort(key=lambda o:(o.get('hotelEst') is None,full(o)))
        d=geo.BYID[did];rows={}
        days=lst[0]['nights']+1
        stay=lst[0]['hotelEst']['total'] if lst[0].get('hotelEst') else 0
        for o in lst:
            rows[o['from']]={'from':o['from'],'city':aname(o['from']),'km':o['drive']['km'],'min':o['drive']['min'],'tickets':round(o['tickets']),'access':o['access']['total'],'hotel':o['hotelEst']['total'] if o.get('hotelEst') else 0,'total':round(full(o)),'dep':o['dep'],'ret':o['ret'],'verified':o['verified'],'optionId':o['id'],'state':'verified'}
        for c in codes:
            if c in rows: continue
            ps=[best[k]['price'] for k in best if k[0]==c and k[1] in d['air']]
            if ps:
                c2=dict(cfg)
                if mode in('car','dropoff'): c2['tollOneWay']=access.tolls(lat,lon,c) or 0
                ac=access.cost(mode,c,drive[c],days,P,c2)['total'];t=round(min(ps)*2*P)
                rows[c]={'from':c,'city':aname(c),'km':drive[c]['km'],'min':drive[c]['min'],'tickets':t,'access':ac,'hotel':stay,'total':t+ac+stay,'verified':False,'state':'estimate'}
            else:
                rows[c]={'from':c,'city':aname(c),'km':drive[c]['km'],'min':drive[c]['min'],'state':'none'}
        R=sorted(rows.values(),key=lambda r:(r['state']=='none',r.get('total',0),r['km']))
        win=lst[0];win['compare']=R
        priced=[r for r in R if r['state']!='none']
        near=min(priced,key=lambda r:r['km'])
        w=next(r for r in R if r['from']==win['from'])
        if near is not w and w['total']<near['total']:
            win['insight']=f"Opłaca się jechać dalej. Z {agen(w['from'])} ({w['km']} km) wychodzi {near['total']-w['total']} zł taniej niż z {agen(near['from'])} ({near['km']} km), licząc bilety, dojazd, parking i nocleg."
        elif near is w and len(priced)>1:
            n2=next(r for r in priced if r is not w)
            win['insight']=f"Najbliższe lotnisko z lotami jest też najtańsze w sumie. Kolejne, {aname(n2['from'])}, wychodzi {n2['total']-w['total']} zł drożej."
def recheck(body):
    """Uzytkownik dotknal dnia w kalendarzu: potwierdzamy loty na ten termin."""
    o,dep,ret,q=body['option'],body['dep'],body['ret'],body.get('q') or {}
    d0=dt.date.fromisoformat(dep);d1=dt.date.fromisoformat(ret)
    if d1<=d0: raise ValueError('Powrót musi być po wylocie')
    A,C=o['pax']['adults'],o['pax']['children']
    lat,lon=float(q['origin']['lat']),float(q['origin']['lon'])
    d=geo.BYID[o['dest']['id']]
    drive={o['from']:o['drive']}
    mode=(q.get('transport') or {}).get('mode','car')
    r,age=flights.roundtrip(o['from'],o['to'],dep,ret,A,C,5,0 if q.get('direct') else None)
    r=prefer(r,q)
    if not r: raise ValueError('Na ten termin nie ma już tego połączenia. Wybierz inny dzień.')
    grid=o.get('calendar') or []
    one=next((x['price'] for x in grid if x['dep']==dep),r[0]['total']/(A+C))
    c={'o':o['from'],'d':o['to'],'n':(d1-d0).days,'dep':dep,'ret':ret,'grid':grid,'one':one}
    return build(c,r,time.time()-age,q,drive,mode,dict(q.get('transport') or {}),A,C,{o['to']:[d]},lat,lon,d0.month,{})
def start(q):
    jid=uuid.uuid4().hex[:12]
    job={'id':jid,'state':'running','progress':0,'label':'Start','t':time.time()}
    with _jl:
        for k in [k for k,v in JOBS.items() if time.time()-v['t']>3600]: del JOBS[k]
        if sum(1 for v in JOBS.values() if v['state']=='running')>=3: raise ValueError('Serwer szuka już trzech wyjazdów. Spróbuj za chwilę.')
        JOBS[jid]=job
    threading.Thread(target=run,args=(job,q),daemon=True).start()
    return jid
