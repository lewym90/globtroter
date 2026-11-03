"""Hotele: lista i ceny z wielu stron (Xotelo, dane TripAdvisora). Ceny zawsze z czasem sprawdzenia.
Xotelo podaje srednia cene za noc pokoju; pobieramy w EUR i przeliczamy po kursie NBP."""
import datetime as dt,math,threading,time
from concurrent.futures import ThreadPoolExecutor
import geo,links,net
API='https://data.xotelo.com/api'
def rooms_for(A,C): return max(1,math.ceil((A+C)/3) if C else math.ceil(A/2))
def _list(ta,sort,limit=40):
    j=net.fetch_json(f'{API}/list?location_key=g{ta}&limit={limit}&offset=0&sort={sort}',ttl=7*86400)
    if j.get('error'): raise net.SourceDown(str(j['error']))
    return (j.get('result') or {}).get('list') or []
_rl=threading.Lock();_last=[0.0]
def _rates(key,ci,co):
    with _rl:
        w=_last[0]+.45-time.time()
        if w>0:time.sleep(w)
        _last[0]=time.time()
    j=net.fetch_json(f'{API}/rates?hotel_key={key}&chk_in={ci}&chk_out={co}&currency=EUR',ttl=4*3600,tries=2)
    if j.get('error'): return None
    return (j.get('result') or {}).get('rates') or []
def estimate(d,ci,co,A,C):
    """Koszt noclegu na konkretny termin: mediana zywych cen pieciu dobrze ocenianych hoteli.
    Liczy sie data: targi albo swieta potrafia podniesc ceny kilkukrotnie."""
    if not d.get('ta'): return None
    try:
        L=[h for h in _list(d['ta'],'best_value') if (h.get('review_summary') or {}).get('rating',0)>=4][:5]
        if not L: return None
        eur=net.fx('EUR');vals=[]
        for h in L:
            r=_safe(h['key'],ci,co) or []
            p=[x['rate'] for x in r if x.get('rate') and x['rate']>0]
            if p: vals.append(min(p)*eur)
        if len(vals)<2: return None
        vals.sort();night=vals[len(vals)//2]
        n=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
        R=rooms_for(A,C)
        return {'night':round(night),'rooms':R,'total':round(night*n*R),'est':True,'samples':len(vals)}
    except Exception: return None
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
def search(did,ci,co,A,C,budget=None,pref='balanced',minrating=0,kind='all',breakfast=False):
    d=geo.BYID.get(did)
    if not d: raise ValueError('Nie znam tego miejsca')
    R=rooms_for(A,C)
    if not d.get('ta'): return {'hotels':[],'unsupported':True,'fallback':links.hotel_links('hotele',d['en'],ci,co,A,C,R)}
    a,b=dt.date.fromisoformat(ci),dt.date.fromisoformat(co);N=(b-a).days
    if N<1: raise ValueError('Wymeldowanie musi być po zameldowaniu')
    seen={}
    for s in('best_value','popularity'):
        for h in _list(d['ta'],s,50): seen.setdefault(h['key'],h)
    L=list(seen.values())
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
    if not ok: return {'hotels':[],'noOffers':len(top)>0,'fallback':links.hotel_links('hotele',d['en'],ci,co,A,C,R)}
    lo=min(h['_min'] for h in ok);hi=max(h['_min'] for h in ok)
    for h in ok: h['_value']=1-(h['_min']-lo)/max(1,hi-lo)
    res=[]
    for h in ok:
        s,dist=score(h,pref,(d['lat'],d['lon']))
        rs=h.get('review_summary') or {}
        lk=links.hotel_links(h['name'],d['en'],ci,co,A,C,R)
        prices=sorted([{'site':'Strona hotelu' if k=='Official Site' else k,'night':v,'total':v*N*R,'url':lk.get(k) or lk['Google']} for k,v in h['_rates'].items()],key=lambda x:x['night'])
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
