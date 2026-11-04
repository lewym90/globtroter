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
        w=_last[0]+.45-time.time()
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
    """Koszt noclegu na konkretny termin: mediana zywych cen pieciu dobrze ocenianych hoteli.
    Liczy sie data: targi albo swieta potrafia podniesc ceny kilkukrotnie."""
    if not d.get('ta'): return _est_google(d,ci,co,A,C)
    try:
        L=[h for h in _list(d) if (h.get('review_summary') or {}).get('rating',0)>=4][:5]
        if not L: return _est_google(d,ci,co,A,C)
        eur=net.fx('EUR');vals=[]
        # Rownolegle: kolejka w _rates pilnuje odstepow, a nie czekamy na kazdy hotel po kolei
        with ThreadPoolExecutor(5) as ex: res=list(ex.map(lambda h:_quick(h['key'],ci,co),L))
        for r in res:
            p=[x['rate'] for x in r if x.get('rate') and x['rate']>0]
            if p: vals.append(min(p)*eur)
        if len(vals)<2: return _est_google(d,ci,co,A,C)
        vals.sort();night=vals[len(vals)//2]
        n=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
        R=rooms_for(A,C)
        return {'night':round(night),'rooms':R,'total':round(night*n*R),'est':True,'samples':len(vals)}
    except Exception: return _est_google(d,ci,co,A,C)
def _est_google(d,ci,co,A,C):
    L=ghotels.search(d,ci,co)
    if not L: return None
    v=sorted(h['nightPln'] for h in L if (h['rating'] or 0)>=4) or sorted(h['nightPln'] for h in L)
    night=v[len(v)//2];n=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days;R=rooms_for(A,C)
    return {'night':night,'rooms':R,'total':night*n*R,'est':True,'samples':len(v)}
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
            h['amen']=m['amen'];h['stars']=m.get('stars');h['breakfast']=h['breakfast'] or m['breakfast'];h['breakfastPaid']=m['breakfastPaid'] and not h['breakfast']
            if m['bestTotal']<h['bestTotal']:
                h['prices'].insert(0,m['prices'][0]);h['bestTotal']=m['bestTotal'];h['bestNight']=m['bestNight']
        else: h.setdefault('amen',[]);h.setdefault('breakfastPaid',False)
        out.append(h)
    out+=list(gs.values())
    if pref!='cheap': out=[h for h in out if not re.search(r'hostel|dorm|backpack',h['name'],re.I) and (h.get('stars') or 2)>=2] or out
    if breakfast: out=[h for h in out if h['breakfast']] or out
    out.sort(key=lambda h:(h['overBudget'],-h['score']))
    return {'hotels':out,'nights':(x or g)['nights'],'rooms':R,'checkedAt':time.time(),'sources':[n for n,v in (('Xotelo',x),('Google Hotels',g)) if v],
      'note':'To ceny orientacyjne z pośredników, za pokój dla dwóch osób. Ten sam hotel potrafi różnić się między serwisami o kilkanaście, a nawet ponad 30%, a przy rezerwacji cena może być inna, zależnie od pokoju, warunków odwołania i podatku lokalnego. Ostateczną kwotę i śniadanie zobaczysz dopiero w serwisie.'}
