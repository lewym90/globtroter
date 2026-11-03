"""Ryanair: ceny na kazdy dzien miesiaca, te same, ktore pokazuje ich strona. Jedno zapytanie to caly miesiac,
wiec dlugie okresy sprawdzamy bez ciaglego pytania Google. To nieoficjalne zrodlo: gdy zawiedzie, zostaje Google."""
import datetime as dt,threading,time
import geo,net
API='https://services-api.ryanair.com/farfnd'
_l=threading.Lock();_last=[0.0];_fails=[0];GAP=.25
class Down(Exception): pass
def _get(url,ttl):
    if _fails[0]>=5: raise Down('ryanair')
    with _l:
        w=_last[0]+GAP-time.time()
        if w>0: time.sleep(w)
        _last[0]=time.time()
    try:
        r=net.fetch_json(url,ttl=ttl,tries=1,timeout=12,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'});_fails[0]=0;return r
    except net.SourceDown as e:
        _fails[0]+=1;raise Down(str(e))
def reset(): _fails[0]=0
def status(): return {'fails':_fails[0]}
def routes(o):
    """Dokad lata Ryanair z tego lotniska. Jedno zapytanie, pusty zbior gdy zrodlo nie odpowiada."""
    a=dt.date.today()+dt.timedelta(days=2);b=a+dt.timedelta(days=330)
    try:
        j=_get(f'{API}/v4/oneWayFares?departureAirportIataCode={o}&outboundDepartureDateFrom={a}&outboundDepartureDateTo={b}&currency=PLN&market=pl-pl',3*86400)
        return {f['outbound']['arrivalAirport']['iataCode'] for f in j.get('fares') or []}
    except (Down,KeyError,TypeError): return set()
def month(o,d,ym):
    """{dzien: {price,dep,arr}} dla jednego kierunku. ym to 'RRRR-MM'."""
    j=_get(f'{API}/3/oneWayFares/{o}/{d}/cheapestPerDay?market=pl-pl&currency=PLN&outboundMonthOfDate={ym}-01',6*3600)
    out={}
    for f in (j.get('outbound') or {}).get('fares') or []:
        p=f.get('price') or {}
        if f.get('unavailable') or f.get('soldOut') or not p.get('value') or p.get('currencyCode')!='PLN' or not f.get('departureDate') or not f.get('arrivalDate'): continue
        out[f['day']]={'price':float(p['value']),'dep':f['departureDate'][:16],'arr':f['arrivalDate'][:16]}
    return out
def _yms(a,b):
    r=[];y,m=a.year,a.month
    while (y,m)<=(b.year,b.month):
        r.append(f'{y}-{m:02d}');m+=1
        if m>12: y,m=y+1,1
    return r
def fares(o,d,a,b):
    """Ceny dzien po dniu w obu kierunkach dla calego okresu."""
    t={};z={}
    for ym in _yms(a,b):
        t.update(month(o,d,ym));z.update(month(d,o,ym))
    return t,z
def grid(t,z,a,b,n):
    """Bilet w obie strony dla kazdego dnia wylotu w [a,b] przy n nocach, z dwoch cen w jedna strone."""
    r=[];day=a
    while day<=b:
        k=day.isoformat();e=(day+dt.timedelta(days=n)).isoformat()
        if k in t and e in z: r.append({'dep':k,'ret':e,'price':round(t[k]['price']+z[e]['price']),'src':'FR'})
        day+=dt.timedelta(days=1)
    return r
def _flight(o,d,f):
    """Czasy sa lokalne, wiec roznice stref wyrownujemy do pelnej godziny wedlug odleglosci."""
    x=geo.AIRPORTS[o];y=geo.AIRPORTS[d];est=geo.km(x['lat'],x['lon'],y['lat'],y['lon'])/13+30
    raw=(dt.datetime.fromisoformat(f['arr'])-dt.datetime.fromisoformat(f['dep'])).total_seconds()/60
    mins=round(raw+60*round((est-raw)/60))
    return {'price':f['price'],'stops':0,'min':mins,'selfTransfer':False,'legs':[{'airline':'FR','airlineName':'Ryanair','no':'','from':o,'to':d,'dep':f['dep'],'arr':f['arr'],'min':mins,'plane':None}]}
def trip(o,d,dep,ret,P):
    """Konkretny lot Ryanaira, gdy Google nie odpowiada. Cena za osobe razy liczba osob."""
    a=dt.date.fromisoformat(dep);b=dt.date.fromisoformat(ret)
    try: t,z=fares(o,d,a.replace(day=1),a);zz=month(d,o,ret[:7])
    except Down: return []
    if dep not in t or ret not in zz: return []
    f=_flight(o,d,t[dep]);g=_flight(d,o,zz[ret])
    return [{'total':round((f['price']+g['price'])*P),'out':f,'back':g,'source':'Ryanair'}]
