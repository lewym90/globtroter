"""Sun & Fun Holidays (sunfun.pl): wczasy samolotem (Egipt, Turcja, Tunezja, Bulgaria, Samos, Cypr Polnocny).

Zrodlo: publiczny GraphQL, ktory wola sama strona bez logowania i bez cookies:
  POST https://www.sunfun.pl/graphql?lang=pl
  1) SearchFlights {depCity, arrCities, dateFrom} -> dni z lotami (data, kierunek, rejsy z dlugosciami pobytu).
     Odpowiedz ma najwyzej 12 dni lotow; kolejne bierzemy, przesuwajac dateFrom na ostatni dzien z odpowiedzi
     (kursor 'after' zwraca pusta liste).
  2) SearchResults {depCity, arrCity, date, duration, airline, flightNo} -> hotele dla jednego terminu
     (10 na strone, od najtanszych). Czytamy pierwsza strone kazdego terminu.
robots.txt (User-agent *) zabrania /admin, /obj-*, /objednavka/*, /rezervace/*, /cestovni-*, /doplnkove-sluzby/*,
/dodatkowe-uslugi/*; /graphql i strony hoteli /<kraj>/<kierunek>/<hotel>/ sa dozwolone (sprawdzone 2026-11-08).

Uwagi:
- Zapytan jest duzo (1 na termin = dzien x dlugosc pobytu; Egipt z Katowic w czerwcu to ok. 90 terminow),
  wiec czytamy najwyzej PAGES zapytan na wyszukiwanie: najpierw terminy 7-nocne rozlozone rowno po miesiacu,
  potem inne dlugosci. Gdy nie starczy, complete=False. Jeden hotel = jedna (najtansza) oferta.
- Cena: price.total = cena za pokoj dla 2 doroslych, jak na stronie hotelu ('Cena calkowita');
  pricePerPerson = cena za osobe. Lista bywa chwilowo nieaktualna po obnizce (strona hotelu liczy z nowszego
  cennika - 05.11.2026 lista dawala 5502 zl, a strona 5382 zl), dlatego APPROX = True: ceny sa orientacyjne.
- Ocena klientow Sun & Fun jest w procentach ('97 %'); przeliczamy na 0-10.
- Cypr = Cypr Polnocny (Famagusta, Bafra); Grecja = tylko Samos.
"""
import calendar,datetime as dt,json,re,urllib.parse
from . import http

NAME='Sun & Fun'
SITE='https://www.sunfun.pl'
OP='sunfun'
GQL=SITE+'/graphql?lang=pl'
APPROX=True
ADULTS=2
PAGES=30            # najwiecej zapytan (loty + wyniki) na jedno wyszukiwanie
FLIGHT_CALLS=6      # najwiecej zapytan o loty na jedno miasto wylotu
# kierunki (arrCity) z SearchSearchForm; kazdy kraj sprawdzony: sa loty w 2027 (2026-11-08)
COUNTRIES={'EG':['46','52'],'TR':['100'],'TN':['35','726'],'BG':['87'],'GR':['949']}  # Cypr u Sun&Fun to Cypr Polnocny, nie pokazujemy go jako Cypr
# depCity z SearchSearchForm. Brak KRK, BZG, SZZ, OSZ. WAW = Okecie (Modlinu Sun & Fun nie ma).
DEP={'KTW':3,'WAW':2,'GDN':5,'WRO':6,'POZ':7,'LCJ':8,'RZE':9,'LUZ':11}
# kody wyzywienia widziane w odpowiedziach (2026-11): AI, AIS, 24AI, PREAI, UAI, BB, HB, BO
BOARD={'AI':'All inclusive','UAI':'All inclusive','AIS':'All inclusive','24AI':'All inclusive','PREAI':'All inclusive',
       'BB':'Śniadania','HB':'Śniadania i obiadokolacje','FB':'Pełne wyżywienie','BO':'Bez wyżywienia','RO':'Bez wyżywienia'}

def board(key,value):
    k=(key or '').upper();v=(value or '').strip()
    if k in BOARD: return BOARD[k]
    if 'ALL INCLUSIVE' in v.upper(): return 'All inclusive'
    return v.capitalize() if v.isupper() else v

Q_FLIGHTS="""query SearchFlights($request: SearchV2RequestInput!, $first: Int) {
  search_flights(request: $request, first: $first) {
    totalCount
    flights { date depCity arrCity destination country departureAirportCode isSoldOut
      items { flightNo duration isSoldOut airline departureAirportCode returnDate } }
  }
}"""
Q_RESULTS="""query SearchResults($request: SearchV2RequestInput!) {
  searchV2(request: $request) {
    hotels {
      price { total }
      rooms { variants { pricePerPerson pricePerRoom isSelected board { key value } room { key value } } }
      idHotel name url stars destinationName regionName countryName isPriceFrom
      rating { rating ratingCount }
    }
    pagination { page pageCount itemsPerPage totalItems }
    resultUrl
    error
  }
}"""

def _post(op,query,variables):
    r=http.get(GQL,data=json.dumps([{'operationName':op,'variables':variables,'query':query}]),
               headers={'Content-Type':'application/json','Accept':'application/json','Origin':SITE})
    d=json.loads(r);d=d[0] if isinstance(d,list) else d
    if d.get('errors') and not d.get('data'): raise IOError('sunfun: '+str(d['errors'])[:200])
    return d.get('data') or {}

def _month(ym):
    y,m=map(int,ym.split('-'));return f'{y:04d}-{m:02d}-01',f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}'

def flights_request(dep,cc,date_from):
    return {'request':{'arrCity':None,'depCity':dep,'rooms':[{'adults':ADULTS,'children':[]}],'dateFrom':date_from,'dateTo':None,
            'date':None,'durations':[],'specification':{},'arrCities':COUNTRIES[cc],'arrCityCheckboxes':[],'duration':None},'first':12}
def results_request(t,page=1):
    r={'arrCity':int(t['arrCity']),'depCity':t['depCity'],'rooms':[{'adults':ADULTS,'children':[]}],
       'dateFrom':t['date'],'dateTo':None,'date':t['date'],'durations':[],'airline':t['airline'],'duration':t['duration'],
       'specification':{},'arrCities':[],'flightNo':t['flightNo']}
    if page>1: r['page']=page
    return {'request':r}

def terms(flights,ym):
    """Lista terminow (dzien lotu x dlugosc) z wylotem w miesiacu ym, bez wyprzedanych."""
    out=[];seen=set()
    for f in flights:
        if not f.get('date','').startswith(ym) or f.get('isSoldOut'): continue
        for i in f.get('items') or []:
            if i.get('isSoldOut') or not i.get('duration'): continue
            k=(f['date'],f.get('arrCity'),i.get('flightNo'),i['duration'])
            if k in seen: continue
            seen.add(k)
            out.append({'date':f['date'],'arrCity':f.get('arrCity'),'depCity':f.get('depCity'),'flightNo':i.get('flightNo'),
                        'airline':i.get('airline'),'duration':i['duration'],'ret':i.get('returnDate'),
                        'from':i.get('departureAirportCode') or f.get('departureAirportCode')})
    return out

def pick(ts,n):
    """Najwyzej n terminow: najpierw 7-nocne, potem pozostale; w kazdej grupie rowno rozlozone po datach."""
    a=sorted([t for t in ts if t['duration']==7],key=lambda t:t['date']);b=sorted([t for t in ts if t['duration']!=7],key=lambda t:t['date'])
    out=[]
    for g in (a,b):
        k=n-len(out)
        if k<=0: break
        out+=g if len(g)<=k else [g[int(i*len(g)/k)] for i in range(k)]
    return out

def _stars(s):
    m=re.match(r'STAR_(\d)(?:_(\d))?$',s or '')
    if not m: return None
    return float(f'{m.group(1)}.{m.group(2)}') if m.group(2) else int(m.group(1))

def _rating(r):
    try:
        if r and r.get('ratingCount'): return round(float(str(r['rating']).replace('%','').replace(',','.').strip())/10,1)
    except (TypeError,ValueError): pass
    return None

def parse(text,term):
    """Odpowiedz SearchResults dla jednego terminu -> oferty. term: dict z terms() (data, powrot, noce, lotnisko)."""
    d=json.loads(text) if isinstance(text,(str,bytes)) else text
    d=d[0] if isinstance(d,list) else d
    s=((d.get('data') or d).get('searchV2')) or {}
    out=[]
    for h in s.get('hotels') or []:
        vv=[v for rm in h.get('rooms') or [] for v in rm.get('variants') or []]
        v=([x for x in vv if x.get('isSelected')] or vv or [None])[0]
        tot=(h.get('price') or {}).get('total')
        if not v or not tot or not h.get('url') or not h.get('name'): continue
        tot=int(round(float(tot)));ppp=int(round(float(v.get('pricePerPerson') or tot/ADULTS)))
        b=v.get('board') or {}
        pl=[]
        for x in (h.get('destinationName'),h.get('regionName')):
            x=re.sub(r'\s+',' ',x or '').strip()
            if x and x not in pl: pl.append(x)
        place=', '.join(pl)
        out.append({'op':OP,'name':h['name'].strip(),'stars':_stars(h.get('stars')),'place':place,
            'dep':term['date'],'ret':term['ret'],'nights':term['duration'],
            'board':board(b.get('key'),b.get('value')),
            'from':term['from'],'ppp':ppp,'adults':ADULTS,'total':tot,'rating':_rating(h.get('rating')),
            'kind':'wypoczynek','url':SITE+urllib.parse.quote(h['url'],safe="/?=&%:,;+-_.~")})
    return out

def search(cc,ym,origin=None,limit_pages=PAGES):
    cc=cc.upper();origin=origin.upper() if origin else None
    if cc not in COUNTRIES or (origin and origin not in DEP): return {'offers':[],'total':0,'complete':True,'url':SITE}
    budget=min(limit_pages or PAGES,PAGES);a,b=_month(ym);calls=0;complete=True
    ts=[]
    for code in ([origin] if origin else list(DEP)):
        day=a;seen=set();fl=[]
        for _ in range(FLIGHT_CALLS):
            if calls>=budget: complete=False;break
            F=(_post('SearchFlights',Q_FLIGHTS,flights_request(DEP[code],cc,day)).get('search_flights') or {});calls+=1
            got=[f for f in F.get('flights') or [] if (f['date'],f.get('arrCity')) not in seen]
            for f in got: seen.add((f['date'],f.get('arrCity')));fl.append(f)
            dates=sorted(f['date'] for f in F.get('flights') or [])
            if len(F.get('flights') or [])<12 or not dates or dates[-1]>b: break
            nxt=dates[-1] if got else (dt.date.fromisoformat(dates[-1])+dt.timedelta(1)).isoformat()
            if nxt==day: nxt=(dt.date.fromisoformat(day)+dt.timedelta(1)).isoformat()
            day=nxt
        else: complete=False
        ts+=terms(fl,ym)
    left=max(0,budget-calls);chosen=pick(ts,left)
    if len(chosen)<len(ts): complete=False
    best={};total=0;url=None;more=[]
    def take(t,page):
        nonlocal total,url
        s=(_post('SearchResults',Q_RESULTS,results_request(t,page)).get('searchV2') or {})
        if s.get('error'): return 1
        pg=s.get('pagination') or {}
        if page==1: total+=pg.get('totalItems') or 0
        url=url or (SITE+s['resultUrl'] if s.get('resultUrl') else None)
        for o in parse({'data':{'searchV2':s}},t):
            k=o['url'].split('?')[0]
            if k not in best or o['ppp']<best[k]['ppp']: best[k]=o
        return pg.get('pageCount') or 1
    for t in chosen:
        n=take(t,1);calls+=1
        more+=[(t,p) for p in range(2,n+1)]
    # dalsze strony (drozsze hotele) tylko, jesli zostal limit zapytan
    for t,p in more:
        if calls>=budget: complete=False;break
        take(t,p);calls+=1
    offers=sorted(best.values(),key=lambda o:o['ppp'])
    # total = suma ofert (hotel x termin), ktore Sun & Fun podaje dla przeczytanych terminow; None gdy nie wszystkie
    return {'offers':offers,'total':total if complete else None,'complete':complete,'url':url or SITE}
