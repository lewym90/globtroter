"""Swiat Podrozy Oskar (oskar.com.pl): wypoczynek, objazdowki i wyjazdy 'Ekspres', glownie autokarem.

Zrodlo: publiczne REST API, ktore wola strona oskar.com.pl bez logowania:
  GET https://api.bookandgo.oskar.com.pl/api/www/offer/?adults=2&locations=<kraj>&date_range=<od>,<do>
      &stops=<przystanki>&ordering=full_price&limit=..&offset=..&timezone=Europe/Warsaw
robots.txt: oskar.com.pl zabrania tylko /login/; api.bookandgo.oskar.com.pl nie ma robots.txt (404),
wiec nic nie jest zabronione (sprawdzone 2026-11-08). Pobieramy tylko /api/www/offer/.

Uwagi (sprawdzone na zywo 2026-11):
- Jeden wiersz = jeden produkt (hotel albo program wycieczki) z najtanszym terminem i pokojem.
  'total' = count z API = liczba produktow, ktore podaje Oskar.
- date_range obejmuje caly pobyt (dateRange.lower >= od i upper <= do), jak na stronie. Autokar wyjezdza
  zwykle dzien przed poczatkiem pobytu, wiec 'dep' bierzemy z stop.departureDatetime (czas polski),
  'ret' z stop.returnDatetime, i odrzucamy wyjazdy spoza miesiaca.
- Przystanki: miasto ma osobny przystanek autokarowy (kind C) i lotniczy (kind F). Dla lotniska
  podajemy oba (np. KTW = autokar Katowice + lot z Katowic). 'from' = kod IATA dla lotu,
  a dla autokaru nazwa miasta z dopiskiem '(autokar)', zeby nie udawac lotu.
- Pokoj: lista wybiera najtanszy pokoj, czasem 3-4-osobowy. Dla 2 doroslych w takim pokoju strona
  dolicza 'Doplate do wolnego miejsca' (np. La Mirage: 2 x 1803,48 + 1350 = 4956,96 zl). Takich wierszy
  nie pokazujemy: dla tych produktow pytamy drugi raz z filtrem room_type=<pokoje 2-osobowe>
  (API to obsluguje, lista id po przecinku) i bierzemy pokoj dla 2 osob; jesli go nie ma, pomijamy produkt.
- Cena: fullPrice (grosze) = 'Cena za osobe' na stronie oferty po promocji (First Minute itp.).
  ppp = fullPrice zaokraglone do zlotych, total = 2 x fullPrice ('Laczna kwota' na stronie dla pokoju
  2-osobowego). Doplata za wyjazd z danego przystanku (stop.fee) jest w cenie strony, nie doliczamy jej.
- Link: format z term_id i stops (format z stop_id bez term_id raz pokazal cene katalogowa).
"""
import calendar,datetime as dt,json,re,unicodedata,urllib.parse
from . import http

NAME='Świat Podróży Oskar'
SITE='https://oskar.com.pl'
OP='oskar'
API='https://api.bookandgo.oskar.com.pl/api/www/offer/'
ADULTS=2
PER_PAGE=100
PAGES=5
# id krajow z /api/www/offer_filter/ (locations). Kazdy sprawdzony: count>0 dla 2027 (2026-11-08).
# Turcja ma u Oskara dwa id. Pominiete kraje bez nazwy w aplikacji (Luksemburg, Monako, San Marino, Watykan, Japonia).
# Egipt, Rumunia, USA i ZEA sa w slowniku, ale nie mialy zadnej oferty na 2027 - pominiete.
COUNTRIES={'AL':'4','AT':'6','BA':'9','BE':'7','BG':'10','CH':'44','CY':'1831','CZ':'13','DE':'33','DK':'14','EE':'15',
    'ES':'19','FI':'16','FR':'17','GB':'50','GE':'1865','GR':'18','HR':'11','HU':'49','IT':'51','LT':'26','LV':'28',
    'MA':'1885','ME':'12','MK':'29','MT':'30','NL':'20','NO':'34','PL':'35','PT':'36','RS':'41','SE':'45','SI':'1356',
    'SK':'42','TR':'1862,46'}
# Przystanki z offer_filter.stops: (autokar C, lot F). WAW = Warszawa (autokar) + Chopin + Modlin.
# OSZ: Oskar nie lata z Szyman; jest autokar z Olsztyna.
STOPS={'WAW':['60','1567','1568'],'KTW':['21','1560'],'KRK':['29','1561'],'GDN':['11','1559'],'WRO':['62','1569'],
       'POZ':['45','1564'],'RZE':['735','1565'],'LUZ':['34','1562'],'BZG':['6','2010'],'LCJ':['35','1563'],
       'SZZ':['54','1566'],'OSZ':['39']}
FLIGHT={1567:'WAW',1568:'WMI',1560:'KTW',1561:'KRK',1559:'GDN',1569:'WRO',1564:'POZ',1565:'RZE',1562:'LUZ',
        2010:'BZG',1563:'LCJ',1566:'SZZ'}
SAME={'WAW':{'WAW','WMI'}}
# Typy pokoi dla dokladnie 2 doroslych (z /api/offer/sell_accommodation/<termin>/ dla wszystkich ofert, 2026-11-08).
# Pokoje '2 osobowy + 1 dostawka' (16, 17) maja miejsce dla dziecka - pomijamy je, bo moze dojsc doplata.
ROOMS2=[4,7,8,10]
KIND={1:('wypoczynek','wypoczynek'),2:('objazd','objazdowka'),3:('city break','ekspres')}
BOARD={'bez wyzywienia':'Bez wyżywienia','sniadanie':'Śniadania','sniadania':'Śniadania',
       'sniadanie i obiadokolacja':'Śniadania i obiadokolacje','sniadanie, obiad i kolacja':'Pełne wyżywienie',
       'all-inclusive':'All inclusive','all inclusive':'All inclusive','obiadokolacje':'Obiadokolacje',
       'zgodnie z programem':'Zgodnie z programem'}

def _ascii(t):
    return unicodedata.normalize('NFKD',(t or '').replace('ł','l').replace('Ł','L')).encode('ascii','ignore').decode().lower()
def slug(t): return re.sub(r'[^a-z0-9]+','-',_ascii(t)).strip('-')
def board(t): return BOARD.get(_ascii(t).strip(),t or '')

def _last_sunday(y,m):
    d=dt.date(y,m,calendar.monthrange(y,m)[1]);return d-dt.timedelta((d.weekday()+1)%7)
def local_date(iso):
    """'2027-06-08T05:00:00Z' (UTC) -> data w Polsce (CET/CEST wg regul UE), bez bazy stref czasowych."""
    t=dt.datetime.strptime(iso[:19],'%Y-%m-%dT%H:%M:%S')
    a=dt.datetime.combine(_last_sunday(t.year,3),dt.time(1));b=dt.datetime.combine(_last_sunday(t.year,10),dt.time(1))
    return (t+dt.timedelta(hours=2 if a<=t<b else 1)).date().isoformat()

def _month(ym):
    y,m=map(int,ym.split('-'));return f'{y:04d}-{m:02d}-01',f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}'
def _stops(origin):
    return STOPS[origin] if origin else [s for v in STOPS.values() for s in v]
def params(cc,ym,origin,offset=0,extra=None):
    a,b=_month(ym)
    q={'adults':str(ADULTS),'locations':COUNTRIES[cc],'date_range':f'{a},{b}','stops':','.join(_stops(origin)),
       'limit':str(PER_PAGE),'offset':str(offset),'ordering':'full_price','timezone':'Europe/Warsaw'}
    q.update(extra or {});return q
def _qs(q): return urllib.parse.urlencode(q,safe=',')
def list_url(cc,ym,origin=None):
    a,b=_month(ym)
    return SITE+'/oferty?'+_qs({'adults':str(ADULTS),'locations':COUNTRIES[cc],'date_range':f'{a},{b}','stops':','.join(_stops(origin))})

def _country(locs):
    for l in locs or []:
        while l:
            if l.get('kind')=='CR': return l.get('name')
            l=l.get('parentLocation')
    return None
def _place(locs):
    if not locs: return ''
    l=locs[0];chain=[]
    while l:
        if l.get('kind')!='CR': chain.append(l.get('name'))
        l=l.get('parentLocation')
    return ', '.join(x for x in reversed(chain) if x)

def from_code(stop):
    if stop.get('id') in FLIGHT: return FLIGHT[stop['id']]
    return f"{stop.get('name')} (autokar)" if stop.get('kind')=='C' else stop.get('name')

def room_ok(r):
    """Pokoj dla dokladnie 2 doroslych (albo wyjazd bez noclegu wyceniony dla 2 osob)."""
    rt=r.get('roomType') or {}
    return rt.get('adults')==ADULTS and not rt.get('children')

def parse(text,ym=None,origin=None,rooms=True):
    """JSON /api/www/offer/ -> oferty. rooms=True: tylko pokoje dla 2 doroslych (bez doplaty do wolnego miejsca)."""
    d=json.loads(text) if isinstance(text,(str,bytes)) else text
    out=[]
    for r in d.get('results') or []:
        p=r.get('product') or {};st=r.get('stop') or {};tm=r.get('term') or {};rt=r.get('roomType') or {}
        if (r.get('transport') or {}).get('kind') not in ('C','F'): continue      # dojazd wlasny
        if not st.get('departureDatetime') or not st.get('returnDatetime') or not p.get('id'): continue
        if rooms and not room_ok(r): continue
        dep,ret=local_date(st['departureDatetime']),local_date(st['returnDatetime'])
        if ym and dep[:7]!=ym: continue
        stop={'id':st.get('id'),'name':st.get('name'),'kind':'F' if (r.get('transport') or {}).get('kind')=='F' else 'C'}
        frm=from_code(stop)
        if origin and str(st.get('id')) not in STOPS.get(origin,[]): continue      # inny przystanek niz zapytany
        try: price=float(r['fullPrice'])/100
        except (KeyError,TypeError,ValueError): continue
        if price<=0: continue
        kind,kslug=KIND.get((p.get('kind') or {}).get('id'),('wypoczynek','wypoczynek'))
        name=(p.get('name') or '').strip();m=re.search(r'\s*(\*{1,5})\s*$',name)
        stars=len(m.group(1)) if m else None
        if m: name=name[:m.start()].strip()
        dr=r.get('dateRange') or {};pr=r.get('promotion') or {};bd=r.get('board') or {}
        q={'adults':str(ADULTS),'children':'0','boards':str(bd.get('id') or ''),'date_range':f"{dr.get('lower')},{dr.get('upper')}",
           'nights':str(tm.get('nightStay')),'term_id':str(tm.get('id')),'stops':str(st.get('id')),'own_transport':'false',
           'room_type':str(rt.get('id') or ''),'promotion':str(pr.get('id') or 0),'multi_room':'false'}
        url=f"{SITE}/oferta/{kslug}/{slug(_country(r.get('locations')) or '')}/{slug(p.get('name'))}/{p['id']}?"+_qs(q)
        out.append({'op':OP,'name':name,'stars':stars,'place':_place(r.get('locations')) or _country(r.get('locations')) or '','dep':dep,'ret':ret,
            'nights':tm.get('nightStay'),'board':board(bd.get('name')),'from':frm,'ppp':round(price),'adults':ADULTS,
            'total':round(price*ADULTS),'rating':None,'kind':kind,'url':url})
    return out

def _get(q): return json.loads(http.get(API+'?'+_qs(q),headers={'Accept':'application/json'}))

def search(cc,ym,origin=None,limit_pages=PAGES):
    cc=cc.upper();origin=origin.upper() if origin else None
    if cc not in COUNTRIES: return {'offers':[],'total':0,'complete':True,'url':SITE}
    if origin and origin not in STOPS: return {'offers':[],'total':0,'complete':True,'url':list_url(cc,ym,None)}
    pages=min(limit_pages or PAGES,PAGES);rows=[];total=None;complete=False
    for p in range(pages):
        d=_get(params(cc,ym,origin,p*PER_PAGE))
        total=d.get('count') or 0;res=d.get('results') or [];rows+=res
        if not d.get('next') or len(res)<PER_PAGE: complete=True;break
    by={}
    for r in rows: by.setdefault((r.get('product') or {}).get('id'),r)
    # produkty, ktorych najtanszy pokoj nie jest dla 2 osob: drugi raz tylko z pokojami 2-osobowymi
    rooms2=sorted({str(i) for i in ROOMS2}|{str(r['roomType']['id']) for r in rows if room_ok(r) and (r.get('roomType') or {}).get('id')},key=int)
    bad=[str(k) for k,r in by.items() if k and not room_ok(r)]
    for i in range(0,len(bad),50):
        d=_get(params(cc,ym,origin,0,{'products':','.join(bad[i:i+50]),'room_type':','.join(rooms2)}))
        for r in d.get('results') or []:
            k=(r.get('product') or {}).get('id')
            if k in by and room_ok(r): by[k]=r
    offers=parse({'results':list(by.values())},ym,origin)
    offers.sort(key=lambda o:o['ppp'])
    return {'offers':offers,'total':total,'complete':complete,'url':list_url(cc,ym,origin)}
