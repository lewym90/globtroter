"""Silnik wyszukiwania. Trzy kroki, tak zeby jak najmniej pytac Google:
1. ROZPOZNANIE: kilka dat, wszystkie lotniska naraz, ceny kazdej pary.
2. KALENDARZ: najlepsze pary, cena dla kazdej daty wylotu.
3. POTWIERDZENIE: konkretne loty dla najlepszych wariantow."""
import calendar as cal,datetime as dt,itertools,math,threading,time,uuid
import access,climate,flights,geo,hotels,links,ryanair,store
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
        a=max(dt.date.fromisoformat(w['from']),min_day);b=min(dt.date.fromisoformat(w['to']),min_day+dt.timedelta(days=400))
    if b<a: raise ValueError('Ten termin już minął')
    return a,b,nights,a.month
def last_return(w,b):
    """Do kiedy mozna wrocic. Miesiac i wlasne daty sa scisle, przy kwartale czy roku powrot moze wypasc tuz po okresie."""
    if w.get('mode')=='dates' or (w.get('mode')=='range' and w.get('spill')): return None
    return b
def months_of(a,b):
    return ryanair._yms(a,b)
def allowed(x,a,b,lim,wd):
    d=dt.date.fromisoformat(x['dep'])
    return a<=d<=b and (lim is None or x['ret']<=lim.isoformat()) and (not wd or d.weekday() in wd)
def merge(*gs):
    """Laczy kalendarze: dla kazdej daty wylotu zostaje najnizsza cena."""
    m={}
    for g in gs:
        for x in g or []:
            k=(x['dep'],x['ret'])
            if k not in m or x['price']<m[k]['price']: m[k]=x
    return sorted(m.values(),key=lambda x:x['dep'])
def spans(a,b,n=59):
    r=[];c=a
    while c<=b:
        e=min(b,c+dt.timedelta(days=n));r.append((c,e));c=e+dt.timedelta(days=1)
    return r
def pick_dests(q,month):
    """Zwraca kierunki do sprawdzenia i uwagi. Klimat decyduje przy wyborze stylu."""
    t=q.get('dest',{});mode=t.get('mode','city');notes=[]
    style=t.get('style') if mode!='city' else None
    ms=[month] if isinstance(month,int) else month
    def fitb(d,st):
        """Przy kilku miesiacach liczy sie najlepszy z nich."""
        rs=[climate.fit(d,m,st) for m in ms]
        return max(rs,key=lambda r:-1 if r[0] is None else r[0])
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
        s,why=fitb(d,style or 'city')
        scored.append((s,d,why))
    unfit=[(d,why) for s,d,why in scored if style=='beach' and s is not None and s<0.55]
    if style=='beach' and mode!='anywhere' and unfit and len(unfit)==len(scored):
        best=sorted([(fitb(d,'beach')[0] or 0,d) for d in geo.DESTS if 'beach' in d['tags']],key=lambda x:-x[0])[:4]
        notes.append({'kind':'climate','text':f"W tym miesiącu {unfit[0][0]['name']} nie nadaje się na plażowanie. {unfit[0][1]}.",
            'alternatives':[{'id':d['id'],'name':d['name'],'fit':climate.month(d,ms[0])} for _,d in best]})
    pool=scored
    if style in('beach','ski') and mode=='anywhere':
        pool=[x for x in scored if (x[0] or 0)>=0.55]
        if not pool:
            pool=sorted(scored,key=lambda x:-(x[0] or 0))[:6]
            notes.append({'kind':'climate','text':'W tym miesiącu nigdzie w Europie nie ma idealnych warunków. Pokazujemy najlepsze, jakie są.'})
    pool.sort(key=lambda x:(-(x[0] if x[0] is not None else .5),-x[1].get('links',0)))
    res=[];seen={}
    for s,d,why in pool:
        if mode=='anywhere' and seen.get(d['cc'],0)>=(4 if style=='beach' else 2): continue
        res.append(d);seen[d['cc']]=seen.get(d['cc'],0)+1
        if len(res)>=(8 if mode=='anywhere' else MAXD): break
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
        w=q.get('when') or {}
        a,b,nights,month=window(w)
        lim=last_return(w,b);wd=set(int(x) for x in w.get('days') or []) if w.get('mode')!='dates' else set()
        yms=months_of(a,b);long_=len(yms)>2;ok=lambda x:allowed(x,a,b,lim,wd)
        mnums=[int(y[5:7]) for y in yms]
        dests,notes=pick_dests(q,mnums if len(mnums)>1 else month)
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
        st=0 if q.get('direct') else None
        best={};stat={'ok':0,'failed':0}
        # Ryanair: pelne ceny dzien po dniu, bez czekania na Google
        ryanair.reset();fr={};calls=0
        step('Sprawdzam ceny Ryanaira',.04)
        for o in sorted(codes,key=lambda c:drive[c]['km']):
            r=ryanair.routes(o)
            for dd in [x for x in air if x in r]:
                if calls>=300: break
                step(f'Ceny Ryanair {o} → {dd}',.04+.14*min(1,calls/max(1,len(codes)*len(yms)*2)))
                try:
                    t,z=ryanair.fares(o,dd,a,b+dt.timedelta(days=max(nights)));calls+=len(yms)*2
                except ryanair.Down: continue
                for n in nights:
                    g=[x for x in ryanair.grid(t,z,a,b,n) if ok(x)]
                    if g:
                        fr[(o,dd,n)]=g;top=min(g,key=lambda x:x['price'])
                        if (o,dd) not in best or top['price']/2<best[(o,dd)]['price']: best[(o,dd)]={'price':top['price']/2,'stops':0,'day':top['dep']}
        # Google: pozostale linie. Gdy zaczyna blokowac, a mamy ceny Ryanaira, nie czekamy minutami na kazde pytanie
        def gq(fn,*x):
            if fr and stat['failed']>=2: raise flights.Unavailable('Google pominiete')
            return fn(*x)
        grids={};parts=spans(a,b)
        # Krotki okres i jedno-dwa miasta: od razu kalendarze. Jedno zapytanie daje caly miesiac zamiast jednego dnia,
        # i pokazuje kazda pare lotnisk, a nie tylko te, ktore Google wybral do rozpoznania.
        direct=not long_ and a!=b and len(dests)<=2
        if direct: days=[]
        elif a==b: days=[a]
        elif long_: days=[d for d in sample_days(a,b,len(yms) if len(yms)<=6 else 6)]
        else: days=sample_days(a,b,2 if len(dests)>3 else 3)
        batches=[(o,d,day) for day in days for o in chunk(codes,7) for d in chunk(air,7)]
        for i,(o,d,day) in enumerate(batches):
            step(f"Sprawdzam rynek: {day.day}.{day.month:02d}, {len(o)} lotnisk",.18+.3*i/len(batches))
            try:
                r,_=gq(flights.oneway,o,d,day.isoformat(),1,0,st)
                stat['ok']+=1
                for f in r:
                    k=(f['legs'][0]['from'],f['legs'][-1]['to'])
                    if k not in best or f['price']<best[k]['price']: best[k]={'price':f['price'],'stops':f['stops'],'day':day.isoformat()}
            except flights.Unavailable: stat['failed']+=1
        if direct:
            pairs=[(c,x) for c in sorted(codes,key=lambda c:drive[c]['km']) for d in dests for x in d['air'][:2]][:12]
            for i,(c,x) in enumerate(pairs):
                step(f'Kalendarz cen {c} → {x}',.18+.42*i/len(pairs))
                for p in parts:
                    try:
                        r,_=gq(flights.calendar,c,x,p[0].isoformat(),p[1].isoformat(),nights[0],1,0,st)
                        g=[y for y in r if ok(y)];stat['ok']+=1
                        grids.setdefault((c,x,nights[0]),[]).extend(g)
                        if g:
                            top=min(g,key=lambda y:y['price'])
                            if (c,x) not in best or top['price']/2<best[(c,x)]['price']: best[(c,x)]={'price':top['price']/2,'stops':None,'day':top['dep']}
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
        chosen=sorted(chosen,key=est)[:(10 if len(dests)>1 else 8) if not long_ else (6 if len(dests)>1 else 4)]
        jobs=[]
        for (o,dd) in chosen:
            for n in nights:
                g=fr.get((o,dd,n))
                if not long_ or len(parts)<=2: use=parts
                elif g:
                    # Ryanair zna juz caly okres, Google sprawdza tylko najtansze fragmenty pod katem innych linii
                    use=sorted(parts,key=lambda p:min([x['price'] for x in g if p[0].isoformat()<=x['dep']<=p[1].isoformat()] or [10**9]))[:1]
                else: use=parts if n==nights[0] else parts[:0]
                if (o,dd,n) in grids: continue
                jobs+=[(o,dd,n,p) for p in use]
        jobs=jobs[:36]
        for i,(o,dd,n,p) in enumerate(jobs):
            step(f"Kalendarz cen {o} → {dd}",.6+.15*i/len(jobs))
            try:
                r,_=gq(flights.calendar,o,dd,p[0].isoformat(),p[0].isoformat() if a==b else p[1].isoformat(),n,1,0,st)
                grids.setdefault((o,dd,n),[]).extend([x for x in r if ok(x)]);stat['ok']+=1
            except flights.Unavailable: stat['failed']+=1
        for k,g in fr.items():
            if (k[0],k[1]) in chosen or k in grids: grids[k]=merge(grids.get(k),g)
        for k in list(grids): grids[k]=merge(grids[k])
        style=(q.get('dest') or {}).get('style') if (q.get('dest') or {}).get('mode')!='city' else None
        def good(c):
            if style not in('beach','ski'): return True
            s,_=climate.fit(adest[c['d']][0],int(c['dep'][5:7]),style)
            return s is None or s>=.55
        # Warianty: najtanszy termin dla pary i dlugosci; przy dlugim okresie osobno dla kazdego miesiaca
        cand=[]
        for (o,dd,n),g in grids.items():
            if not g: continue
            groups={}
            for x in g: groups.setdefault(x['dep'][:7] if long_ else '',[]).append(x)
            for pool in groups.values():
                top=min(pool,key=lambda x:x['price'])
                cand.append({'o':o,'d':dd,'n':n,'dep':top['dep'],'ret':top['ret'],'grid':g,'pool':pool,'one':top['price']})
        if not all(map(good,cand)) and any(map(good,cand)): cand=[c for c in cand if good(c)]
        def full(c):
            cc=dict(cfg)
            return c['one']*P+access.cost(mode,c['o'],drive[c['o']],c['n']+1,P,{**cc,'tollOneWay':0})['total']
        cand.sort(key=full)
        tocheck=[];seen={};seenm=set();cap=(5 if long_ else 3) if len(dests)==1 else 2
        for c in cand:
            ds=adest[c['d']][0]['id'];mk=(ds,c['dep'][:7])
            if seen.get(ds,0)>=cap or len(tocheck)>=(6 if len(dests)==1 else 8) or (long_ and mk in seenm): continue
            tocheck.append(c);seen[ds]=seen.get(ds,0)+1;seenm.add(mk)
        opts=[]
        for i,c in enumerate(tocheck):
            step(f"Sprawdzam noclegi {adest[c['d']][0]['name']}",.75+.1*i/max(1,len(tocheck)))
            best_dates(c,adest[c['d']][0],A,C,P)
            step(f"Potwierdzam loty {c['o']} → {c['d']}",.85+.12*i/max(1,len(tocheck)))
            rt=None;checked=None
            try:
                r,age=gq(confirm,c,A,C,st)
                stat['ok']+=1
                if r: rt=prefer(r,q);checked=time.time()-age
            except flights.Unavailable: stat['failed']+=1
            if not rt and (c['o'],c['d'],c['n']) in fr:
                rt=ryanair.trip(c['o'],c['d'],c['dep'],c['ret'],P) or None
                if rt: checked=time.time()
            o=build(c,rt,checked,q,drive,mode,cfg,A,C,adest,lat,lon,month,best)
            opts.append(o)
        opts.sort(key=lambda o:(not o['verified'],o['hotelEst'] is None,o['totalWithHotel']))
        # Kazde lotnisko dostaje prawdziwa cene z kalendarza zamiast wstepnej z rozpoznania
        checked={**fr,**grids};tried=set();calls=0;seenw=set();wins=[]
        for o in opts:
            mk=(o['dest']['id'],o['dep'][:7] if long_ else '')
            if mk not in seenw: seenw.add(mk);wins.append((o,mk))
        gone=False
        for o,(did,ym) in wins:
            d=geo.BYID[did];n=o['nights']
            have=lambda c:any(x for k,v in checked.items() if k[0]==c and k[1] in d['air'] and k[2]==n for x in v if x['dep'].startswith(ym))
            # Rozpoznanie pokazuje tylko czesc par, wiec lotnisko bez ceny tez sprawdzamy: najpierw te z cena, potem najblizsze
            for c in sorted(codes,key=lambda c:(min([best[(c,x)]['price'] for x in d['air'] if (c,x) in best] or [10**9]),drive[c]['km'])):
                if have(c): tried.add((c,did,ym));continue
                if calls>=12 or gone: continue
                for dd in [x for x in d['air'] if (c,x) in best] or d['air'][:1]:
                    if ym:
                        y,m0=int(ym[:4]),int(ym[5:7]);p0=max(a,dt.date(y,m0,1));p1=min(b,dt.date(y,m0,cal.monthrange(y,m0)[1]));use=[(p0,p1)]
                    else: use=parts
                    step(f'Sprawdzam lotnisko {c}',.97)
                    for p in use:
                        calls+=1
                        try:
                            r,_=gq(flights.calendar,c,dd,p[0].isoformat(),p[0].isoformat() if a==b else p[1].isoformat(),n,1,0,st)
                            checked[(c,dd,n)]=merge(checked.get((c,dd,n)),[x for x in r if ok(x)]);stat['ok']+=1;tried.add((c,did,ym))
                        except flights.Unavailable: stat['failed']+=1;gone=True
        # Gdy inne lotnisko wychodzi taniej, liczymy je w pelni i moze wygrac
        extra=0
        for o,(did,ym) in wins:
            d=geo.BYID[did];n=o['nights'];alts={}
            for (c,dd,k),v in checked.items():
                if k!=n or dd not in d['air'] or c==o['from']: continue
                g=[x for x in v if x['dep'].startswith(ym)]
                if not g: continue
                top=min(g,key=lambda x:x['price']);cost=top['price']*P+access.cost(mode,c,drive[c],n+1,P,{**cfg,'tollOneWay':0})['total']
                if cost<o['total']-50 and (c not in alts or cost<alts[c][0]): alts[c]=(cost,dd,top,g)
            for c,(cost,dd,top,g) in sorted(alts.items(),key=lambda z:z[1][0])[:1]:
                if extra>=2 or any(x['from']==c and x['dep']==top['dep'] for x in opts): continue
                extra+=1;e={'o':c,'d':dd,'n':n,'dep':top['dep'],'ret':top['ret'],'grid':checked[(c,dd,n)],'pool':g,'one':top['price']}
                step(f'Potwierdzam loty {c} → {dd}',.98)
                best_dates(e,d,A,C,P);rt=None;when_=None
                try:
                    r,age=gq(confirm,e,A,C,st)
                    if r: rt=prefer(r,q);when_=time.time()-age
                except flights.Unavailable: stat['failed']+=1
                if not rt and (c,dd,n) in fr:
                    rt=ryanair.trip(c,dd,e['dep'],e['ret'],P) or None
                    if rt: when_=time.time()
                if rt: opts.append(build(e,rt,when_,q,drive,mode,cfg,A,C,adest,lat,lon,month,best))
        opts.sort(key=lambda o:(not o['verified'],o['hotelEst'] is None,o['totalWithHotel']))
        compare_airports(opts,best,drive,mode,cfg,P,codes,lat,lon,checked,long_,tried)
        step('Gotowe',1)
        summary=month_summary(yms,{**fr,**grids},adest,style) if len(yms)>1 else None
        job.update(state='done',result={'options':opts,'notes':notes,'coverage':stat,'empty':not opts,'month':month,'at':time.time(),'months':summary,
            'grids':{f'{k[0]}-{k[1]}-{k[2]}':v for k,v in {**fr,**grids}.items()} if summary else None,'driveBy':{k:drive[k] for k in codes} if summary else None,
            'partial':stat['failed']>0})
    except ValueError as e: job.update(state='error',error=str(e))
    except flights.Unavailable as e:
        job.update(state='error',error='Google Flights chwilowo nie odpowiada. Nie wiemy, jakie są ceny, więc niczego nie pokazujemy. Spróbuj za kilka minut.',retry=True)
    except Exception as e:
        import logging;logging.exception('search');job.update(state='error',error='Wyszukiwanie przerwane przez błąd serwera. Spróbuj ponownie.',retry=True)
def month_summary(yms,grids,adest,style):
    """Najnizsza cena biletu w kazdym miesiacu, z pogoda w tym miesiacu."""
    out=[]
    for ym in yms:
        top=None
        for (o,dd,n),g in grids.items():
            for x in g:
                if x['dep'][:7]==ym and (top is None or x['price']<top[0]['price']): top=(x,o,dd,n)
        if not top: out.append({'ym':ym,'state':'none'});continue
        x,o,dd,n=top;d=adest[dd][0];cl=climate.month(d,int(ym[5:7])) or {};s=climate.fit(d,int(ym[5:7]),style)[0] if style in('beach','ski') else None
        out.append({'ym':ym,'state':'ok','price':x['price'],'dep':x['dep'],'ret':x['ret'],'nights':n,'from':o,'to':dd,'destId':d['id'],'destName':d['name'],'tmax':cl.get('tmax'),'sea':cl.get('sea'),'unfit':s is not None and s<.55})
    return out
def month_grid(b):
    """Kalendarz sasiedniego miesiaca po dotknieciu strzalki. Kazde zrodlo osobno, zeby awaria jednego nie zabrala cen."""
    o,dd,ym,n=b['from'],b['to'],b['ym'],int(b['nights'])
    y,m=int(ym[:4]),int(ym[5:7]);a=max(dt.date(y,m,1),dt.date.today()+dt.timedelta(days=1));e=dt.date(y,m,cal.monthrange(y,m)[1])
    if e<a: return {'ym':ym,'grid':[]}
    g=[];ga=[];down=False
    if dd in ryanair.routes(o):
        try:
            t,z=ryanair.fares(o,dd,a,e+dt.timedelta(days=n));g=ryanair.grid(t,z,a,e,n)
        except ryanair.Down: pass
    try: ga,_=flights.calendar(o,dd,a.isoformat(),e.isoformat(),n,1,0,0 if b.get('direct') else None)
    except flights.Unavailable: down=True
    if down and not g: raise flights.Unavailable('kalendarz')
    return {'ym':ym,'grid':merge(ga,g)}
def confirm(c,A,C,st):
    """Potwierdza konkretne loty: w obie strony, potem osobno, potem nastepna najtansza data."""
    for x in [{'dep':c['dep'],'ret':c['ret'],'price':c['one']}]+sorted([g for g in c.get('pool') or c['grid'] if g['dep']!=c['dep']],key=lambda g:g['price'])[:2]:
        r,age=flights.roundtrip(c['o'],c['d'],x['dep'],x['ret'],A,C,5,st)
        if not r: r=flights.separate(c['o'],c['d'],x['dep'],x['ret'],A,C,st);age=0
        if r:
            if x['dep']!=c['dep']:
                c.update(dep=x['dep'],ret=x['ret'],one=x['price']);c.pop('hotelEst',None)
            return r,age
    return [],0
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
        if f.get('separate'): warn.append('Cena to dwa osobne bilety w jedną stronę. Przy zakupie sprawdź, czy w obie strony nie wyjdzie taniej.')
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
    res['perPersonAll']=round(res['totalWithHotel']/P)
    if res['flight']:
        L=res['flight']['out']['legs'][0];lh,buf=leave_home(L['dep'],drv,mode,d['cc'] not in NONSCH)
        res['leaveHome']=lh;res['airportBuffer']=buf
        h=int(lh[11:13])
        if h<4 or lh[:10]<L['dep'][:10]: warn.append(f"Wylot o {L['dep'][11:]}: z domu trzeba wyjechać o {lh[11:]}"+(' poprzedniego dnia.' if lh[:10]<L['dep'][:10] else '.'))
        if res['flight']['out'].get('selfTransfer') or res['flight']['back'].get('selfTransfer'): warn.append('Przesiadka na osobnych biletach: spóźnienie pierwszego lotu to Twoje ryzyko.')
    dq=q.get('dest') or {}
    month=int(c['dep'][5:7])
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
    g=sorted(c.get('pool') or c['grid'],key=lambda x:x['price']);picks=[]
    for x in g:
        if x['price']>g[0]['price']*1.35: break
        day=dt.date.fromisoformat(x['dep'])
        if all(abs((day-dt.date.fromisoformat(y['dep'])).days)>=6 for y in picks): picks.append(x)
        if len(picks)==3: break
    bestv=None;t0=time.time()
    for x in picks:
        # Limit czasu na porownanie terminow: lepiej mniej terminow niz minuty czekania
        if bestv and time.time()-t0>25: break
        e=hotels.estimate(d,x['dep'],x['ret'],A,C)
        v=x['price']*P+(e['total'] if e else 0)
        if bestv is None or v<bestv[0]: bestv=(v,x,e)
    if bestv:
        c['dep'],c['ret'],c['one']=bestv[1]['dep'],bestv[1]['ret'],bestv[1]['price']
        c['hotelEst']=bestv[2]
def compare_airports(opts,best,drive,mode,cfg,P,codes,lat,lon,fr=None,bymonth=False,tried=None):
    """Porownanie lotnisk na jednej zasadzie: bilety, bagaz i dojazd, ta sama dlugosc pobytu, najtanszy termin
    z kazdego lotniska. Noclegu tu nie liczymy: nie zalezy od lotniska, a roznice terminow by wszystko zamazaly."""
    by={}
    for o in opts: by.setdefault((o['dest']['id'],o['dep'][:7] if bymonth else ''),[]).append(o)
    for (did,ym),lst in by.items():
        lst.sort(key=lambda o:(not o['verified'],o.get('hotelEst') is None,o['totalWithHotel']))
        d=geo.BYID[did];win=lst[0];rows={};days=win['nights']+1
        def row(o): return {'from':o['from'],'city':aname(o['from']),'km':o['drive']['km'],'min':o['drive']['min'],'tickets':round(o['tickets']),'access':o['access']['total']+o.get('bags',0),'total':round(o['total']),'dep':o['dep'],'ret':o['ret'],'verified':o['verified'],'optionId':o['id'],'state':'verified' if o['verified'] else 'estimate','stops':o['flight']['out']['stops'] if o.get('flight') else None}
        for o in sorted([o for o in lst if o['nights']==win['nights']],key=lambda o:o['total']):
            rows.setdefault(o['from'],row(o))
        rows[win['from']]=row(win)
        for c in codes:
            if c in rows: continue
            ps=[best[k]['price'] for k in best if k[0]==c and k[1] in d['air']]
            g=[(x,k[1]) for k,v in (fr or {}).items() if k[0]==c and k[1] in d['air'] and k[2]==win['nights'] for x in v if x['dep'].startswith(ym)]
            if g:
                # Dokladna cena z danego dnia, nie z rozpoznania
                x,to=min(g,key=lambda v:v[0]['price']);c2=dict(cfg)
                if mode in('car','dropoff'): c2['tollOneWay']=access.tolls(lat,lon,c) or 0
                ac=access.cost(mode,c,drive[c],days,P,c2)['total']+win.get('bags',0);t=round(x['price']*P)
                rows[c]={'from':c,'to':to,'city':aname(c),'km':drive[c]['km'],'min':drive[c]['min'],'tickets':t,'access':ac,'total':t+ac,'dep':x['dep'],'ret':x['ret'],'verified':False,'state':'fare','stops':0 if x.get('src')=='FR' else None,'nights':win['nights'],'drive':drive[c]}
            elif tried is not None and (c,did,ym) not in tried: continue
            else:
                # Sprawdzone i brak lotow w tym okresie. Nie zgadujemy ceny.
                rows[c]={'from':c,'city':aname(c),'km':drive[c]['km'],'min':drive[c]['min'],'state':'none'}
        R=sorted(rows.values(),key=lambda r:(r['state']=='none',r.get('total',0),r['km']))
        win['compare']=R;win['compareNights']=win['nights']
        priced=[r for r in R if r['state']!='none'];sure=[r for r in priced if r['state']=='verified']
        w=rows[win['from']];near=min(priced,key=lambda r:r['km']);out=[]
        cheap=min(sure,key=lambda r:r['total']) if sure else w
        if cheap is not w and w['total']-cheap['total']>=20:
            out.append(f"Same bilety i dojazd wychodzą taniej z {agen(cheap['from'])} o {w['total']-cheap['total']} zł, ale tam termin ma droższe noclegi, więc cały wyjazd jest tańszy z {agen(w['from'])}.")
        elif near is not w and w['total']<near['total']:
            out.append(f"Opłaca się jechać dalej. Z {agen(w['from'])} ({w['km']} km) bilety i dojazd wychodzą {near['total']-w['total']} zł taniej niż z {agen(near['from'])} ({near['km']} km).")
        elif near is w and len(priced)>1:
            n2=next(r for r in priced if r is not w)
            if n2['total']>w['total']: out.append(f"Najbliższe lotnisko z lotami jest też najtańsze. Kolejne, {aname(n2['from'])}, wychodzi {n2['total']-w['total']} zł drożej.")
        fare=[r for r in priced if r['state']=='fare' and w['total']-r['total']>=50]
        if fare:
            c=min(fare,key=lambda r:r['total'])
            out.append(f"Z {agen(c['from'])} bilety i dojazd wychodzą {w['total']-c['total']} zł taniej w terminie {int(c['dep'][8:])}.{c['dep'][5:7]}. Dotknij tego lotniska, sprawdzę loty i nocleg.")
        if out: win['insight']=' '.join(out)
def recheck(body):
    """Uzytkownik dotknal dnia w kalendarzu: potwierdzamy loty na ten termin."""
    o,dep,ret,q=body['option'],body['dep'],body['ret'],body.get('q') or {}
    if not o.get('drive'): raise ValueError('Brak danych dojazdu')
    d0=dt.date.fromisoformat(dep);d1=dt.date.fromisoformat(ret)
    if d1<=d0: raise ValueError('Powrót musi być po wylocie')
    A,C=o['pax']['adults'],o['pax']['children']
    lat,lon=float(q['origin']['lat']),float(q['origin']['lon'])
    d=geo.BYID[o['dest']['id']]
    drive={o['from']:o['drive']}
    mode=(q.get('transport') or {}).get('mode','car')
    r,age=flights.roundtrip(o['from'],o['to'],dep,ret,A,C,5,0 if q.get('direct') else None)
    if not r: r=flights.separate(o['from'],o['to'],dep,ret,A,C,0 if q.get('direct') else None);age=0
    if not r: r=ryanair.trip(o['from'],o['to'],dep,ret,A+C)
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
