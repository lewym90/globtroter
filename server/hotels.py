"""Hotele: lista i ceny z wielu stron (Xotelo, dane TripAdvisora). Ceny zawsze z czasem sprawdzenia.
Xotelo podaje srednia cene za noc pokoju; pobieramy w EUR i przeliczamy po kursie NBP."""
import datetime as dt,logging,math,re,threading,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
import geo,ghotels,links,net,store
API='https://data.xotelo.com/api'
def rooms_for(A,C): return max(1,math.ceil((A+C)/3) if C else math.ceil(A/2))
def _page(ta,sort,off,n):
    try:
        j=net.fetch_json(f'{API}/list?location_key=g{ta}&limit={n}&offset={off}&sort={sort}',ttl=7*86400,tries=1,timeout=15)
        return (j.get('result') or {}).get('list') or []
    except net.SourceDown: return None
SNAP='https://lewym90.github.io/globtroter/data/hotels/%s.json'
def _list(d):
    """Lista hoteli: najpierw zapisana w repozytorium, na zywo tylko jako zapas."""
    k='hl2:'+d['id']
    v,_=store.get(k)
    if v: return v
    try:
        r=net.fetch_json(SNAP%d['id'],ttl=6*3600,tries=1,timeout=10,cache=False)['r']
        if r: store.put(k,r,6*3600);return r
    except Exception: pass
    seen={}
    for s_ in('best_value','popularity'):
        for h in _page(d['ta'],s_,0,50) or []: seen.setdefault(h['key'],h)
    if not seen: raise net.SourceDown('lista hoteli')
    r=list(seen.values());store.put(k,r,6*3600)
    return r
_rl=threading.Lock();_last=[0.0]
def _rates(key,ci,co,quick=False):
    with _rl:
        w=_last[0]+.12-time.time()
        if w>0:time.sleep(w)
        _last[0]=time.time()
    j=net.fetch_json(f'{API}/rates?hotel_key={key}&chk_in={ci}&chk_out={co}&currency=EUR',ttl=4*3600,tries=1 if quick else 2,timeout=8 if quick else 20)
    if j.get('error'): return None
    return (j.get('result') or {}).get('rates') or []
def _quick(key,ci,co):
    # Przy szacunku jeden wolny hotel nie moze trzymac calego wyszukiwania
    try: return _rates(key,ci,co,True) or []
    except Exception: return []
def estimate(d,ci,co,A,C):
    """Nocleg na konkretny termin: najtanszy z dobrze ocenianych hoteli, z nazwa. Ta sama cena (z tej samej pamieci)
    pojawi sie potem na liscie noclegow, wiec kwota w wynikach i na liscie sie zgadza."""
    R=rooms_for(A,C);N=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
    k=f'esth:{d["id"]}:{ci}:{co}:{A}:{C}'
    v,_=store.get(k)
    if v: return {a:b for a,b in v.items() if a!='rec'}
    if d.get('ta'):
        try:
            L=[]
            for off in (0,100):
                p=_page(d['ta'],'best_value',off,100) or []
                L+=p
                if len(p)<100: break
            L=[h for h in L if (h.get('review_summary') or {}).get('rating',0)>=4 and (h.get('review_summary') or {}).get('count',0)>=20 and _guess(h)
               and h.get('geo') and geo.km(d['lat'],d['lon'],h['geo']['latitude'],h['geo']['longitude'])<=90]
            L=sorted(L,key=_guess)[:8]
            with ThreadPoolExecutor(4) as ex: res=list(ex.map(lambda h:_quick(h['key'],ci,co),L))
            eur=net.fx('EUR');best=None
            for h,r in zip(L,res):
                p=[x['rate'] for x in r if x.get('rate') and x['rate']>0]
                if p and (not best or min(p)<best[1]): best=(h,min(p))
            if best:
                night=round(best[1]*eur)
                v={'night':night,'rooms':R,'total':night*N*R,'name':best[0]['name'],'key':best[0]['key'],'est':False,'rec':{k_:best[0].get(k_) for k_ in('key','name','accommodation_type','review_summary','image','url','geo','price_ranges','merchandising_labels')}}
                store.put(k,v,4*3600);return {a:b for a,b in v.items() if a!='rec'}
        except Exception: pass
    try: return _est_google(d,ci,co,A,C)
    except Exception: return None
def _est_google(d,ci,co,A,C):
    L=ghotels.search(d,ci,co)
    if not L: return None
    ok=[h for h in L if (h['rating'] or 0)>=4 and (h['reviews'] or 0)>=20] or L
    h=min(ok,key=lambda h:h['nightPln']);n=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days;R=rooms_for(A,C)
    return {'night':h['nightPln'],'rooms':R,'total':h['nightPln']*n*R,'name':h['name'],'est':False}
def search_google(d,ci,co,A,C,budget,pref,minrating,kind):
    """Ranking z Google Hotels: gdy Xotelo nie ma listy albo cen dla tego miasta."""
    L=ghotels.deep(d,ci,co)
    if not L: return None
    R=rooms_for(A,C);N=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
    L=[h for h in L if (h['reviews'] or 0)>=20] or L
    if pref!='cheap': L=[h for h in L if not re.search(r'hostel|dorm|backpack',h['name'],re.I) and (h.get('stars') or 2)>=2] or L
    if minrating: L=[h for h in L if (h['rating'] or 0)>=float(minrating)] or L
    lo=min(h['nightPln'] for h in L);hi=max(h['nightPln'] for h in L)
    res=[]
    for h in L:
        x={'review_summary':{'rating':h['rating'],'count':h['reviews']},'geo':{'latitude':h['lat'],'longitude':h['lon']},'_value':1-(h['nightPln']-lo)/max(1,hi-lo),'_breakfast':h.get('breakfast')=='free','_city':'city' in d['tags']}
        s,dist=score(x,pref,(d['lat'],d['lon']))
        total=h['nightPln']*N*R;lk=links.hotel_links(h['name'],d['en'],ci,co,A,C,R)
        why=[]
        if h.get('breakfast')=='free': why.append('śniadanie w cenie')
        if (h['rating'] or 0)>=4.7: why.append('wyjątkowo wysoka ocena gości')
        if 'city' in d['tags'] and dist<1.5: why.append('w samym centrum')
        res.append({'key':h.get('id') or h['name'],'name':h['name'],'type':h.get('kind'),'rating':h['rating'],'reviews':h['reviews'],'image':h['image'],'url':lk['Google'],'lat':h['lat'],'lon':h['lon'],'distKm':round(dist,1) if 'city' in d['tags'] else None,'breakfast':h.get('breakfast')=='free','breakfastPaid':h.get('breakfast')=='paid','stars':h.get('stars'),'amen':h.get('amen') or [],'score':s,
          'prices':[{'site':'Najniższa oferta w Google','night':h['nightPln'],'total':total,'url':lk['Google']}],'compare':[{'site':k,'url':lk[k]} for k in('Booking.com','Agoda.com','Trip.com')],'bestNight':h['nightPln'],'bestTotal':total,'overBudget':bool(budget and total>budget),'why':why,'google':lk['Google']})
    res.sort(key=lambda x:(x['overBudget'],-x['score']))
    return {'hotels':res,'nights':N,'rooms':R,'checkedAt':time.time(),'source':'google'}
def score(h,pref,center):
    """Punkty 0-100. Wagi zaleza od priorytetu."""
    rs=h.get('review_summary') or {};rt=rs.get('rating') or 0;n=rs.get('count') or 0
    w={'balanced':(.38,.32,.2,.1),'luxury':(.65,.05,.2,.1),'cheap':(.2,.6,.15,.05),'center':(.25,.2,.5,.05)}.get(pref,(.38,.32,.2,.1))
    q=max(0,(rt-3)/2);trust=min(1,math.log10(max(n,1))/3.3)
    g=h.get('geo') or {}
    dist=geo.km(center[0],center[1],g.get('latitude',center[0]),g.get('longitude',center[1]))
    near=max(0,1-dist/8) if h.get('_city',True) else .5
    v=h.get('_value',.5)
    return round(100*(w[0]*(q*.8+trust*.2)+w[1]*v+w[2]*near+w[3]*(1 if h.get('_breakfast') else 0))),dist
def search_xotelo(d,ci,co,A,C,budget=None,pref='balanced',minrating=0,kind='all',breakfast=False):
    R=rooms_for(A,C)
    a,b=dt.date.fromisoformat(ci),dt.date.fromisoformat(co);N=(b-a).days
    if N<1: raise ValueError('Wymeldowanie musi być po zameldowaniu')
    try: L=list(_list(d))
    except net.SourceDown: return None
    if kind!='all': L=[h for h in L if (h.get('accommodation_type') or '').lower()==kind]
    if minrating: L=[h for h in L if ((h.get('review_summary') or {}).get('rating') or 0)>=float(minrating)]
    if breakfast: L=[h for h in L if 'Breakfast included' in (h.get('merchandising_labels') or [])]
    usd=net.fx('USD');eur=net.fx('EUR')
    for h in L:
        p=(h.get('price_ranges') or {}).get('minimum') or 0
        h['_city']='city' in d['tags'];h['_guess']=p*usd;h['_breakfast']='Breakfast included' in (h.get('merchandising_labels') or []);h['_value']=.5
    if budget: L=[h for h in L if not h['_guess'] or h['_guess']*N*R<=budget*1.6]
    L.sort(key=lambda h:-score(h,pref,(d['lat'],d['lon']))[0])
    top=L[:18]
    with ThreadPoolExecutor(3) as ex: rates=list(ex.map(lambda h:_safe(h['key'],ci,co),top))
    ok=[]
    for h,r in zip(top,rates):
        if not r: continue
        sr={x['name']:round(x['rate']*eur) for x in r if x.get('rate') and x['rate']>0}
        if not sr: continue
        h['_min']=min(sr.values());h['_rates']=sr;ok.append(h)
    if not ok: return None
    lo=min(h['_min'] for h in ok);hi=max(h['_min'] for h in ok)
    for h in ok: h['_value']=1-(h['_min']-lo)/max(1,hi-lo)
    res=[]
    for h in ok:
        s,dist=score(h,pref,(d['lat'],d['lon']))
        rs=h.get('review_summary') or {}
        lk=links.hotel_links(h['name'],d['en'],ci,co,A,C,R)
        prices=sorted([{'site':'Strona hotelu' if k=='Official Site' else k,'night':v,'total':v*N*R,'url':lk.get(k) or lk['Google'],'via':k not in lk} for k,v in h['_rates'].items()],key=lambda x:x['night'])
        total=prices[0]['total'];why=[]
        if (rs.get('rating') or 0)>=4.7: why.append('wyjątkowo wysoka ocena gości')
        if 'city' not in d['tags']: pass
        elif dist<1.5: why.append('w samym centrum')
        elif dist<3.5: why.append(f'{dist:.1f} km od centrum'.replace('.',','))
        if h['_breakfast']: why.append('śniadanie w cenie')
        if len(prices)>1 and prices[-1]['total']-prices[0]['total']>=50: why.append(f"na {prices[0]['site']} {prices[-1]['total']-prices[0]['total']} zł taniej niż na {prices[-1]['site']}")
        res.append({'key':h['key'],'name':h['name'],'type':h.get('accommodation_type'),'rating':rs.get('rating'),'reviews':rs.get('count'),'image':h.get('image'),'url':h.get('url'),
          'lat':(h.get('geo') or {}).get('latitude'),'lon':(h.get('geo') or {}).get('longitude'),'distKm':round(dist,1) if 'city' in d['tags'] else None,'breakfast':h['_breakfast'],'score':s,'prices':prices,'bestNight':prices[0]['night'],'bestTotal':total,'overBudget':bool(budget and total>budget),'why':why,'google':lk['Google']})
    res.sort(key=lambda x:(x['overBudget'],-x['score']))
    return {'hotels':res,'nights':N,'rooms':R,'checkedAt':time.time(),'note':'Cena za pokój. Lokalny podatek turystyczny może dojść na miejscu.'}
def _safe(k,ci,co):
    try: return _rates(k,ci,co)
    except Exception: return None
def _norm(n):
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',n.lower()).encode('ascii','ignore').decode())[:18]
def offers(key,ci,co,rooms=1):
    if not re.fullmatch(r'Ch[A-Za-z0-9_-]{10,80}',key or ''): raise ValueError('Zły identyfikator hotelu')
    dt.date.fromisoformat(ci);dt.date.fromisoformat(co);r=ghotels.offers(key,ci,co)
    if r is None: raise net.SourceDown('oferty')
    R=max(1,min(5,int(rooms)))
    return {'offers':[{**x,'url':x['url'].replace('searchresults.en.html','searchresults.pl.html').replace('lang=en','lang=pl'),'total':x['total']*R} for x in r],'at':time.time()}
def search(did,ci,co,A,C,budget=None,pref='balanced',minrating=0,kind='all',breakfast=False):
    """Dwa niezalezne zrodla naraz, wynik laczony bez duplikatow."""
    d=geo.BYID.get(did)
    if not d: raise ValueError('Nie znam tego miejsca')
    if (dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days<1: raise ValueError('Wymeldowanie musi być po zameldowaniu')
    with ThreadPoolExecutor(2) as ex:
        fx_=ex.submit(lambda:search_xotelo(d,ci,co,A,C,budget,pref,minrating,kind,False) if d.get('ta') else None)
        fg=ex.submit(search_google,d,ci,co,A,C,budget,pref,minrating,kind)
        def res(f):
            try: return f.result()
            except Exception as e: logging.warning('hotele %s',str(e)[:120]);return None
        x,g=res(fx_),res(fg)
    R=rooms_for(A,C)
    if not x and not g: return {'hotels':[],'sourceDown':True,'fallback':links.hotel_links('hotele',d['en'],ci,co,A,C,R)}
    gs={_norm(h['name']):h for h in (g or {}).get('hotels',[])}
    out=[]
    for h in (x or {}).get('hotels',[]):
        m=gs.pop(_norm(h['name']),None)
        if m:
            h['gkey']=m['key']
            h['amen']=m['amen'];h['stars']=m.get('stars');h['breakfast']=h['breakfast'] or m['breakfast'];h['breakfastPaid']=m['breakfastPaid'] and not h['breakfast']
            if m['bestTotal']<h['bestTotal']:
                h['prices'].insert(0,m['prices'][0]);h['bestTotal']=m['bestTotal'];h['bestNight']=m['bestNight']
        else: h.setdefault('amen',[]);h.setdefault('breakfastPaid',False)
        out.append(h)
    out+=list(gs.values())
    if pref!='cheap': out=[h for h in out if not re.search(r'hostel|dorm|backpack',h['name'],re.I) and (h.get('stars') or 2)>=2] or out
    # Sniadanie filtruje aplikacja przyciskiem, zeby po odznaczeniu bylo widac wszystkie hotele
    out.sort(key=lambda h:(h['overBudget'],-h['score']))
    for h in out:
        if str(h.get('key','')).startswith('Ch'): h['gkey']=h['key']
        h.pop('compare',None)
        if h.get('gkey'): h['gpage']=f"https://www.google.com/travel/hotels/entity/{h['gkey']}/prices?ts={ghotels.stay_token(ci,co)}&hl=pl&gl=pl&curr=PLN"
    return {'hotels':out,'nights':(x or g)['nights'],'rooms':R,'checkedAt':time.time(),'sources':[n for n,v in (('Xotelo',x),('Google Hotels',g)) if v],
      'note':'Ceny za pokój dla dwóch osób. Przy zielonym znaczniku to oferty serwisów z podatkami i opłatami, a link prowadzi do tego hotelu na Twoje daty. Podatek miejski płatny na miejscu może dojść osobno. Ostateczną kwotę, rodzaj pokoju i warunki odwołania potwierdzasz w serwisie.'}

# ---------- Pelna lista noclegow sprawdzana w tle ----------
# TripAdvisor (przez Xotelo) zna setki obiektow w kazdym miejscu, z cenami Booking.com, Agody, Trip.com i strony hotelu
# na konkretne daty. Google Hotels dokladamy z kurortami. Ceny sprawdzamy po kolei i wynik rosnie na oczach uzytkownika.
MAXL=1500;MAXCHK=1500
HJOBS={};_hj=threading.Lock()
def full_list(d):
    """Cala lista obiektow z TripAdvisora dla miejsca (do 1500), trzymana tydzien."""
    k='hlfull:'+d['id']
    v,_=store.get(k)
    if v: return v
    seen={}
    for off in range(0,MAXL,100):
        p=_page(d['ta'],'best_value',off,100)
        if p is None:
            if not seen: raise net.SourceDown('lista hoteli')
            break
        for h in p: seen.setdefault(h['key'],h)
        if len(p)<100: break
    r=[h for h in seen.values() if h.get('geo') and geo.km(d['lat'],d['lon'],h['geo']['latitude'],h['geo']['longitude'])<=90]
    if r: store.put(k,r,7*86400)
    return r
def _guess(h): return ((h.get('price_ranges') or {}).get('minimum') or 0)*net.fx('USD')
def _bf(h): return 'Breakfast included' in (h.get('merchandising_labels') or [])
def _order(L,minrating,est_key=None):
    """Kolejnosc sprawdzania cen: najpierw hotel z szacunku, potem na zmiane najtansze, ze sniadaniem i najlepiej oceniane."""
    # Ocena tylko ustawia kolejnosc: oceny w serwisach roznia sie (3/5 na TripAdvisorze bywa 7,7/10 na Bookingu), wiec nic nie wycinamy
    ok=sorted(L,key=lambda h:((h.get('review_summary') or {}).get('rating') or 0)<float(minrating or 0) and bool((h.get('review_summary') or {}).get('count')))
    cheap=sorted([h for h in ok if _guess(h)],key=_guess)
    bf=[h for h in ok if _bf(h)]
    best=sorted(ok,key=lambda h:-(((h.get('review_summary') or {}).get('rating') or 0)*math.log10(10+((h.get('review_summary') or {}).get('count') or 0))))
    out=[];seen=set()
    if est_key: out+=[h for h in L if h['key']==est_key];seen|={est_key}
    for trio in zip(*(x+[None]*(len(ok)-len(x)) for x in (cheap,bf,best))):
        for h in trio:
            if h and h['key'] not in seen: seen.add(h['key']);out.append(h)
    for h in ok:
        if h['key'] not in seen: seen.add(h['key']);out.append(h)
    return out
def _ta_hotel(h,d,r,ci,co,A,C,budget,pref):
    """Jeden obiekt z TripAdvisora z cenami na te daty, w ksztalcie, ktory rozumie aplikacja."""
    eur=net.fx('EUR');R=rooms_for(A,C);N=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
    sr={x['name']:round(x['rate']*eur) for x in r if x.get('rate') and x['rate']>0}
    if not sr: return None
    lk=links.hotel_links(h['name'],d['en'],ci,co,A,C,R)
    prices=sorted([{'site':'Strona hotelu' if k=='Official website' or k=='Official Site' else k,'night':v,'total':v*N*R,'url':lk.get(k) or lk['Google'],'via':k not in lk} for k,v in sr.items()],key=lambda x:x['total'])
    rs=h.get('review_summary') or {};g=h.get('geo') or {}
    x={'review_summary':rs,'geo':g,'_value':.5,'_breakfast':_bf(h),'_city':'city' in d['tags']}
    s,dist=score(x,pref,(d['lat'],d['lon']))
    total=prices[0]['total']
    return {'key':h['key'],'name':h['name'],'type':h.get('accommodation_type'),'rating':rs.get('rating'),'reviews':rs.get('count'),'image':h.get('image'),'url':h.get('url'),
            'lat':g.get('latitude'),'lon':g.get('longitude'),'distKm':round(dist,1) if 'city' in d['tags'] else None,'breakfast':_bf(h),'breakfastPaid':False,'amen':[],'stars':None,'score':s,
            'prices':prices,'bestNight':prices[0]['night'],'bestTotal':total,'overBudget':bool(budget and total>budget),'src':'ta'}
def _merge_google(job,d,ci,co,A,C,budget,pref,minrating,kind):
    try: g=search_google(d,ci,co,A,C,budget,pref,minrating,kind)
    except Exception as e: logging.warning('hotele google %s',str(e)[:120]);g=None
    if not g: return
    with job['lock']:
        by={_norm(h['name']):h for h in job['hotels']}
        for m in g['hotels']:
            h=by.get(_norm(m['name']))
            if h:
                h['gkey']=m['key'];h['amen']=m.get('amen') or [];h['stars']=m.get('stars');h['breakfast']=h['breakfast'] or m.get('breakfast');h['breakfastPaid']=bool(m.get('breakfastPaid')) and not h['breakfast']
                if m['bestTotal']<h['bestTotal']: h['prices'].insert(0,m['prices'][0]);h['bestTotal']=m['bestTotal'];h['bestNight']=m['bestNight'];h['overBudget']=bool(budget and h['bestTotal']>budget)
            else:
                m=dict(m);m.pop('compare',None);m['src']='google';m['gkey']=m['key'];job['hotels'].append(m)
        for h in job['hotels']:
            if h.get('gkey'): h['gpage']=f"https://www.google.com/travel/hotels/entity/{h['gkey']}/prices?ts={ghotels.stay_token(ci,co)}&hl=pl&gl=pl&curr=PLN"
        job['rev']+=1;job['google']=True
def _run(job,d,ci,co,A,C,budget,pref,minrating,kind):
    try:
        t=threading.Thread(target=_merge_google,args=(job,d,ci,co,A,C,budget,pref,minrating,kind),daemon=True);t.start()
        L=[]
        if d.get('ta'):
            try: L=full_list(d)
            except net.SourceDown: L=[]
        if kind!='all': L=[h for h in L if (h.get('accommodation_type') or '').lower()==kind]
        N=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days;R=rooms_for(A,C)
        if budget: L=[h for h in L if not _guess(h) or _guess(h)*N*R<=budget*2.2]
        ev=store.get(f'esth:{d["id"]}:{ci}:{co}:{A}:{C}')[0] or {};est=ev.get('key')
        if ev.get('rec') and est not in {h['key'] for h in L}: L=[ev['rec']]+L
        Q=_order(L,minrating,est)[:MAXCHK];job['total']=len(Q);job['all']=len(L)
        def one(h):
            r=_safe(h['key'],ci,co)
            x=_ta_hotel(h,d,r or [],ci,co,A,C,budget,pref) if r else None
            with job['lock']:
                job['checked']+=1
                if x and _norm(x['name']) not in {_norm(y['name']) for y in job['hotels']}: job['hotels'].append(x);job['rev']+=1
        with ThreadPoolExecutor(8) as ex: list(ex.map(one,Q))
        t.join(240)
        with job['lock']:
            if not job['hotels']: job['state']='done';job['empty']=True;job['fallback']=links.hotel_links('hotele',d['en'],ci,co,A,C,R);return
        job['state']='done'
        store.put(job['ck'],{'hotels':job['hotels'],'all':job['all'],'total':job['total']},4*3600)
    except Exception:
        logging.exception('hotele job');job['state']='error';job['error']='Nie udało się pobrać noclegów. Spróbuj za chwilę.'
def start(did,ci,co,A,C,budget=None,pref='balanced',minrating=0,kind='all'):
    d=geo.BYID.get(did)
    if not d: raise ValueError('Nie znam tego miejsca')
    a,b=dt.date.fromisoformat(ci),dt.date.fromisoformat(co)
    if (b-a).days<1: raise ValueError('Wymeldowanie musi być po zameldowaniu')
    sig=f'{did}|{ci}|{co}|{A}|{C}|{budget}|{pref}|{minrating}|{kind}'
    ck='hjob:'+sig
    with _hj:
        for k in [k for k,v in HJOBS.items() if time.time()-v['t']>3600]: del HJOBS[k]
        for v in HJOBS.values():
            if v['sig']==sig and v['state']!='error': return v['id']
        if sum(1 for v in HJOBS.values() if v['state']=='running')>=4: raise ValueError('Serwer sprawdza już kilka list hoteli. Spróbuj za minutę.')
        R=rooms_for(A,C);N=(b-a).days
        j={'id':__import__('uuid').uuid4().hex[:12],'sig':sig,'ck':ck,'state':'running','t':time.time(),'hotels':[],'rev':0,'checked':0,'total':0,'all':0,'lock':threading.Lock(),
           'rooms':R,'nights':N,'google':False}
        c,_=store.get(ck)
        if c: j.update(state='done',hotels=c['hotels'],all=c['all'],total=c['total'],checked=c['total'],google=True)
        HJOBS[j['id']]=j
    if j['state']=='running': threading.Thread(target=_run,args=(j,d,ci,co,A,C,budget,pref,minrating,kind),daemon=True).start()
    return j['id']
def status(i,n=0,g=0):
    """Nowe hotele od pozycji n. Gdy doszly dane z Google (wyposazenie, gwiazdki), raz cala lista."""
    j=HJOBS.get(i)
    if not j: raise ValueError('Lista hoteli wygasła. Otwórz noclegi jeszcze raz.')
    with j['lock']:
        full=(j['google'] and not g) or j['state']!='running'
        H=list(j['hotels']) if full else j['hotels'][n:]
        out={'state':j['state'],'checked':j['checked'],'total':j['total'],'all':j['all'],'n':len(j['hotels']),'full':full,'hotels':H,'rooms':j['rooms'],'nights':j['nights'],'google':j['google']}
    if j.get('empty'): out['empty']=True;out['fallback']=j.get('fallback')
    if j.get('error'): out['error']=j['error']
    out['note']='Ceny za pobyt z podatkami tam, gdzie serwis je podaje. Podatek miejski płatny na miejscu może dojść osobno. Ostateczną kwotę, rodzaj pokoju i warunki odwołania potwierdzasz w serwisie. Źródła: TripAdvisor (ceny Booking.com, Agoda, Trip.com i stron hoteli) oraz Google Hotels.'
    return out

# ---------- Hotel z linku do oferty (Booking, Agoda, Expedia, Hotels.com, Trip.com, Google) ----------
# Nie wchodzimy na strone serwisu: nazwe i daty czytamy z samego linku, a hotel szukamy w naszych zrodlach.
from urllib.parse import urlsplit,parse_qs,unquote
def parse_link(u):
    u=(u or '').strip()
    m=re.search(r'https?://\S+',u)
    if not m: raise ValueError('Wklej link do oferty, zaczynający się od https://')
    p=urlsplit(m.group(0));host=p.netloc.lower();path=unquote(p.path);q={k.lower():v[0] for k,v in parse_qs(p.query).items()}
    name=None;ci=co=None
    if 'booking.' in host:
        x=re.search(r'/hotel/[a-z]{2}/([^/.]+)',path);name=x and x.group(1)
        ci=q.get('checkin');co=q.get('checkout')
        if not ci and q.get('checkin_year'): ci=f"{q['checkin_year']}-{int(q['checkin_month']):02d}-{int(q['checkin_monthday']):02d}"
        if not co and q.get('checkout_year'): co=f"{q['checkout_year']}-{int(q['checkout_month']):02d}-{int(q['checkout_monthday']):02d}"
    elif 'agoda.' in host:
        x=re.search(r'/([^/]+)/hotel/',path);name=x and x.group(1)
        ci=q.get('checkin')
        if ci and q.get('los'): co=(dt.date.fromisoformat(ci)+dt.timedelta(days=int(q['los']))).isoformat()
    elif 'expedia.' in host:
        x=re.search(r'Hotels-(.+?)\.h\d+',path);name=x and x.group(1);ci=q.get('chkin');co=q.get('chkout')
    elif 'hotels.com' in host:
        x=re.search(r'/ho\d+/([^/]+)',path);name=x and x.group(1);ci=q.get('chkin');co=q.get('chkout')
    elif 'trip.com' in host:
        x=re.search(r'/hotels/[^/]*?hotel-detail-\d+/([^/]+)',path);name=x and x.group(1);ci=q.get('checkin');co=q.get('checkout')
    elif 'google.' in host and q.get('q'): name=q['q']
    if not name:
        segs=[s for s in path.split('/') if s and not re.fullmatch(r'[a-z]{2}(-[a-z]{2})?|hotel|hotels|rooms|\d+',s,re.I)]
        name=segs[-1] if segs else None
    if not name: raise ValueError('Z tego linku nie da się odczytać nazwy hotelu. Wpisz nazwę ręcznie.')
    name=re.sub(r'\.(?:[a-z]{2}(?:-[a-z]{2})?\.)?html?$','',name)
    name=re.sub(r'[-_+]+',' ',name).strip()
    for x in (ci,co):
        if x:
            try: dt.date.fromisoformat(x)
            except ValueError: ci=co=None
    return {'name':name,'ci':ci,'co':co,'site':host.replace('www.','')}
def from_link(link,did,ci,co,A,C,name=None):
    d=geo.BYID.get(did)
    if not d: raise ValueError('Nie znam tego miejsca')
    info=parse_link(link) if link else {'name':name,'ci':None,'co':None,'site':None}
    if name: info['name']=name
    ci=info['ci'] or ci;co=info['co'] or co
    if not ci or not co: raise ValueError('Brak dat pobytu')
    from tours.compare import same_hotel
    R=rooms_for(A,C)
    # 1. TripAdvisor: ceny z kilku serwisow, w tym Booking.com
    if d.get('ta'):
        try:
            for h in full_list(d):
                if same_hotel(info['name'],h['name']):
                    r=_safe(h['key'],ci,co)
                    x=_ta_hotel(h,d,r,ci,co,A,C,None,'balanced') if r else None
                    if not x:
                        g=h.get('geo') or {};rs=h.get('review_summary') or {}
                        x={'key':h['key'],'name':h['name'],'rating':rs.get('rating'),'reviews':rs.get('count'),'image':h.get('image'),'lat':g.get('latitude'),'lon':g.get('longitude'),'prices':[],'bestTotal':None,'breakfast':_bf(h),'amen':[]}
                    return {'hotel':x,'found':'ta','ci':ci,'co':co,'name':info['name'],'site':info['site'],'rooms':R}
        except net.SourceDown: pass
    # 2. Google Hotels
    try:
        from tours.compare import find_hotel
        h,ok=find_hotel(info['name'],d['en'],ci,co)
        if h and ok:
            N=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
            lk=links.hotel_links(h['name'],d['en'],ci,co,A,C,R)
            x={'key':h.get('id') or h['name'],'name':h['name'],'rating':h.get('rating'),'reviews':h.get('reviews'),'image':h.get('image'),'lat':h['lat'],'lon':h['lon'],'breakfast':h.get('breakfast')=='free','amen':[],
               'prices':[{'site':'Najniższa oferta w Google','night':h['nightPln'] if 'nightPln' in h else round(h['totalPln']/N),'total':h['totalPln']*R,'url':lk['Google']}],'bestTotal':h['totalPln']*R}
            if h.get('id'): x['gkey']=h['id']
            return {'hotel':x,'found':'google','ci':ci,'co':co,'name':info['name'],'site':info['site'],'rooms':R}
    except Exception as e: logging.warning('link google %s',str(e)[:120])
    # 3. Mapa: znamy chociaz polozenie, cene podaje uzytkownik
    try:
        import plan
        g=plan.geocode(f"{info['name']}, {d['en']}")
        if g and geo.km(d['lat'],d['lon'],g['lat'],g['lon'])<=90:
            return {'hotel':{'key':'map:'+info['name'],'name':info['name'].title(),'lat':g['lat'],'lon':g['lon'],'prices':[],'bestTotal':None,'amen':[]},'found':'map','ci':ci,'co':co,'name':info['name'],'site':info['site'],'rooms':R}
    except Exception: pass
    return {'hotel':None,'found':None,'ci':ci,'co':co,'name':info['name'],'site':info['site'],'rooms':R}
