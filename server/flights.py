"""Jedyna brama do Google Flights. Wszystkie zapytania ida przez jedna kolejke:
stale odstepy, ponawianie po 429, wylacznik awaryjny i pamiec cen.
Rozroznia: pusty wynik (brak lotow) od bledu (nie wiadomo). To kluczowe dla wiarygodnosci."""
import datetime as dt,logging,os,random,threading,time
import store
log=logging.getLogger('flights')
GAP=float(os.environ.get('GLOBTROTER_GF_GAP','4'))
CURRENCY='PLN'
_lock=threading.Lock();_last=[0.0];_block=[0.0];_fails=[0]
class Unavailable(Exception): "Zrodlo chwilowo niedostepne: wynik nieznany, nie 'brak lotow'."
_E=None
def _fli():
    global _E
    if _E is None:
        from fli.search import SearchDates,SearchFlights
        from fli import models as m
        _E=(SearchDates,SearchFlights,m)
    return _E
def status():
    return {'blockedFor':max(0,round(_block[0]-time.time())),'fails':_fails[0]}
def _call(fn):
    """Wykonuje fn w kolejce. Po 429 czeka coraz dluzej; po serii bledow zglasza Unavailable."""
    delays=[12,30,75]
    for attempt in range(len(delays)+1):
        with _lock:
            now=time.time()
            if _block[0]>now:
                wait=_block[0]-now
                if wait>120: raise Unavailable('Google Flights: przerwa ochronna')
                time.sleep(wait)
            wait=_last[0]+GAP+random.uniform(0,1.2)-time.time()
            if wait>0: time.sleep(wait)
            _last[0]=time.time()
            try:
                r=fn();_fails[0]=0;return r
            except Exception as e:
                msg=repr(e);lim='429' in msg or 'rate' in msg.lower()
                log.warning('GF blad %s',msg[:200])
                _fails[0]+=1
                if attempt>=len(delays):
                    _block[0]=time.time()+180
                    raise Unavailable(msg[:160])
                _last[0]=time.time()+(delays[attempt] if lim else 2)
    raise Unavailable('wyczerpane proby')
def _ap(code):
    return getattr(_fli()[2].Airport,code)
def _seg(o,d,day):
    m=_fli()[2]
    return m.FlightSegment(departure_airport=[[_ap(x),0] for x in o],arrival_airport=[[_ap(x),0] for x in d],travel_date=day)
def _pax(a,c,inf=0):
    return _fli()[2].PassengerInfo(adults=a,children=c,infants_on_lap=inf)
def _leg(l):
    return {'airline':l.airline.name,'airlineName':l.airline.value,'no':l.flight_number,'from':l.departure_airport.name,'to':l.arrival_airport.name,
            'dep':l.departure_datetime.isoformat(timespec='minutes'),'arr':l.arrival_datetime.isoformat(timespec='minutes'),'min':l.duration,'plane':getattr(l,'aircraft',None)}
def _flight(x):
    return {'price':x.price,'stops':x.stops,'min':x.duration,'selfTransfer':bool(getattr(x,'self_transfer',False)),'legs':[_leg(l) for l in x.legs]}
def valid_flight(f,o=None,d=None,day=None):
    """Odrzuca rekordy niespojne, zamiast je pokazac."""
    try:
        L=f['legs']
        if not L or not f['price'] or f['price']<=0: return False
        if o and L[0]['from'] not in o: return False
        if d and L[-1]['to'] not in d: return False
        if day and L[0]['dep'][:10]!=day: return False
        for a,b in zip(L,L[1:]):
            if a['to']!=b['from']: return False
        for l in L:
            if l['min'] is None or l['min']<=0: return False
        return True
    except Exception: return False
def oneway(origins,dests,day,adults=1,children=0,stops=None):
    """Ceny dla kazdej pary lotnisk w jednym zapytaniu (do 7x7)."""
    key=f"ow:{','.join(sorted(origins))}:{','.join(sorted(dests))}:{day}:{adults}:{children}:{stops}"
    v,age=store.get(key)
    if v is not None: return v,age
    SD,SF,m=_fli()
    kw={}
    if stops==0: kw['stops']=m.MaxStops.NON_STOP
    f=m.FlightSearchFilters(passenger_info=_pax(adults,children),flight_segments=[_seg(origins,dests,day)],trip_type=m.TripType.ONE_WAY,**kw)
    r=_call(lambda:SF().search(f,currency=CURRENCY,country='PL',language='pl')) or []
    out=[g for g in map(_flight,r) if valid_flight(g,origins,dests,day)]
    store.put(key,out,6*3600)
    return out,0
def calendar(o,d,start,end,nights,adults=1,children=0,stops=None,fresh=False):
    """Kalendarz: najtanszy lot w obie strony na kazda date wylotu (max 60 dni)."""
    key=f'grid:{o}:{d}:{start}:{end}:{nights}:{adults}:{children}:{stops}'
    v,age=store.get(key)
    if v is not None and not fresh: return v,age
    SD,SF,m=_fli()
    a=dt.date.fromisoformat(start);ret=(a+dt.timedelta(days=nights)).isoformat()
    kw={'stops':m.MaxStops.NON_STOP} if stops==0 else {}
    f=m.DateSearchFilters(trip_type=m.TripType.ROUND_TRIP,passenger_info=_pax(adults,children),**kw,
        flight_segments=[_seg([o],[d],start),_seg([d],[o],ret)],from_date=start,to_date=end,duration=nights)
    def run():
        try: return SD().search(f,currency=CURRENCY,country='PL',language='pl')
        except TypeError: raise RuntimeError('SearchDates bez waluty')
    r=_call(run) or []
    out=[]
    for x in r:
        day=x.date[0].date().isoformat();back=x.date[1].date().isoformat() if len(x.date)>1 else None
        if x.price and x.price>0 and back: out.append({'dep':day,'ret':back,'price':x.price})
    out=sorted(out,key=lambda g:g['dep'])
    store.put(key,out,20*3600)
    if not fresh: remember([o,d,start,end,nights,adults,children,stops])
    return out,0
def remember(q):
    L=store.get('warmlist')[0] or []
    L=[x for x in L if x[0]!=q][-150:]+[[q,time.time()]]
    store.put('warmlist',L,30*86400)
def warm(limit=40):
    """Noca odswieza kalendarze szukane w ostatnich dwoch tygodniach, zeby rano wyniki byly od razu."""
    L=[x for x in (store.get('warmlist')[0] or []) if time.time()-x[1]<14*86400 and x[0][3]>=dt.date.today().isoformat()]
    n=0
    for q,_ in L[::-1][:limit]:
        try: calendar(*q,fresh=True);n+=1
        except Unavailable: break
        except Exception: continue
    return n
def roundtrip(o,d,dep,ret,adults=1,children=0,top=5,stops=None):
    """Konkretne loty tam i z powrotem: to jest potwierdzenie ceny."""
    key=f'rt:{o}:{d}:{dep}:{ret}:{adults}:{children}:{top}:{stops}'
    v,age=store.get(key)
    if v is not None: return v,age
    SD,SF,m=_fli()
    kw={'stops':m.MaxStops.NON_STOP} if stops==0 else {}
    f=m.FlightSearchFilters(trip_type=m.TripType.ROUND_TRIP,passenger_info=_pax(adults,children),flight_segments=[_seg([o],[d],dep),_seg([d],[o],ret)],**kw)
    r=_call(lambda:SF().search(f,top_n=top,currency=CURRENCY,country='PL',language='pl')) or []
    out=[]
    for t in r:
        if not isinstance(t,tuple) or len(t)!=2: continue
        a,b=map(_flight,t)
        if a['price'] is None and b['price'] is None: continue
        total=b['price'] or a['price']
        a['price']=b['price']=total
        if valid_flight(a,[o],[d],dep) and valid_flight(b,[d],[o],ret):
            out.append({'total':total,'out':a,'back':b})
    out.sort(key=lambda g:g['total'])
    if out: store.put(key,out,3*3600)
    return out,0
def separate(o,d,dep,ret,adults=1,children=0,stops=None):
    """Zapas: dwa bilety w jedna strone. U tanich linii to ta sama cena co w obie strony."""
    a,_=oneway([o],[d],dep,adults,children,stops)
    b,_=oneway([d],[o],ret,adults,children,stops)
    if not a or not b: return []
    pa=min(a,key=lambda x:x['price']);pb=min(b,key=lambda x:x['price'])
    return [{'total':pa['price']+pb['price'],'out':dict(pa),'back':dict(pb),'separate':True}]
