"""TUI Poland (tui.pl): wypoczynek samolotem.

Zrodlo: stale strony list ofert (landing pages) renderowane po stronie serwera; oferty sa w <script id="__NEXT_DATA__">
(JSON albo base64(JSON)), w props.pageProps.initialOffersData[0].offers, 20 na strone, kolejne strony ?page=N,
sortowanie zawsze od najtanszej.
robots.txt (User-agent *) zabrania m.in. /api/, /hotel/offers/, /hotel/configurator/, /feed/, /directions/,
/direction-flights/, /city-holidays/, /checkout/, /pz/, /rezerwacja-*. Pobieramy tylko /wypoczynek/<kraj>/wyloty-z-<miasto>,
/wypoczynek/<kraj>/oferty-wakacje-samolotem i /wypoczynek/<kraj>/oferty-first-minute-lato (dozwolone).
Wyszukiwarka z filtrami (…?q=startDate…) ma na serwerze pusta liste, a oferty doczytuje z /api/ (zabronione),
wiec NIE da sie zapytac TUI o miesiac ani o liczbe noclegow. Robimy tak:
  - strona kraju z danego miasta (wyloty-z-…, tylko 6-8 noclegow, kazdy sezon) albo, bez miasta, oferty-wakacje-samolotem
    (6-15 noclegow), a dodatkowo oferty-first-minute-lato (lato, 6-15 noclegow, wszystkie lotniska);
  - zostawiamy oferty z wylotem w zadanym miesiacu (i z zadanego lotniska).
Kazda lista pokazuje JEDNA, najtansza oferte na hotel dla calego zakresu dat tej strony. Hotel, ktorego najtanszy termin
wypada w innym miesiacu, nie pojawi sie wcale, choc TUI moze miec go tez w zadanym miesiacu. Wynik jest wiec
niepelny z natury zrodla; liczba 'total' (ile TUI ma ofert na ten miesiac) nie jest nigdzie podana.

Ceny: tak jak na liscie TUI (discountPerPersonPrice / discountFullPrice dla '2 Dorosłych + 0 Dzieci').
Nie da sie ich potwierdzic na stronie oferty, bo cena ladowana jest tam przez /api/ (zabronione dla nas).
Link do oferty (/wypoczynek/<kraj>/<region>/<hotel>/OfferCodeWS/<kod>) nie jest zabroniony przez robots.txt;
offerCode zaczyna sie od kodu IATA lotniska wylotu i zawiera daty.
"""
import base64,datetime as dt,json,re
from . import http

APPROX=True
PAGES=100
NAME='TUI'
SITE='https://www.tui.pl'
# Slugi krajow ze strony (destinations.xml + lista kierunkow w wyszukiwarce, sprawdzone 2026-11-08).
# Wyspy Kanaryjskie TUI prowadzi jako osobny kierunek: dla ES czytamy oba.
COUNTRIES={'ES':('hiszpania','wyspy-kanaryjskie'),'GR':('grecja',),'TR':('turcja',),'EG':('egipt',),'BG':('bulgaria',),
           'HR':('chorwacja',),'IT':('wlochy',),'PT':('portugalia',),'CY':('cypr',),'AL':('albania',),'TN':('tunezja',),
           'MA':('maroko',),'MT':('malta',),'ME':('czarnogora',)}
# Strony 'wyloty-z-…' (custom_lp.xml). OSZ: TUI nie lata ze Szczytna.
CITY={'KTW':'wyloty-z-katowic','WAW':'wyloty-z-warszawy','KRK':'wyloty-z-krakowa','GDN':'wyloty-z-gdanska','WRO':'wyloty-z-wroclawia',
      'POZ':'wyloty-z-poznania','RZE':'wyloty-z-rzeszowa','LUZ':'wyloty-z-lublina','BZG':'wyloty-z-bydgoszczy','LCJ':'wyloty-z-lodzi',
      'SZZ':'wyloty-ze-szczecina'}
# Kody lotnisk TUI (pierwsze 3 znaki offerCode). Warszawa: TUI ma 'Warszawa-Chopina', 'Warszawa-Modlin', 'Warszawa-Radom'.
AIRPORTS={'WAW':('WAW','WMI','RDO')}
BOARD={'all inclusive':'All inclusive','śniadanie':'Śniadania','dwa posiłki':'Śniadania i obiadokolacje',
       'trzy posiłki':'Pełne wyżywienie','bez wyżywienia':'Bez wyżywienia'}

def _nd(html):
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: raise IOError('tui: brak __NEXT_DATA__')
    t=m.group(1).strip()
    try: return json.loads(t)
    except ValueError: return json.loads(base64.b64decode(t))
def _num(s):
    d=re.sub(r'[^\d]','',str(s if s is not None else ''))
    return int(d) if d else None
def _date(s):
    m=re.match(r'(\d{2})\.(\d{2})\.(\d{4})$',(s or '').strip())
    return dt.date(int(m.group(3)),int(m.group(2)),int(m.group(1))) if m else None

def page_data(html):
    """Zwraca (lista surowych ofert, pagination) albo (None, None), gdy strona nie ma listy (np. brak takiej trasy)."""
    pp=_nd(html).get('props',{}).get('pageProps',{})
    io=(pp.get('initialOffersData') or [None])[0]
    if not io: return None,None
    return io.get('offers') or [],io.get('pagination') or {}

def parse(text,adults=2):
    """Strona listy TUI (HTML z __NEXT_DATA__) albo gotowa lista ofert -> oferty w formacie kontraktu."""
    rows=page_data(text)[0] if isinstance(text,str) else text
    out=[]
    for r in rows or []:
        try:
            dep=_date(r.get('departureDate'));ret=_date(r.get('returnDate'))
            ppp=_num(r.get('discountPerPersonPrice'));tot=_num(r.get('discountFullPrice'))
            code=r.get('offerCode') or '';url=r.get('offerUrl') or ''
            if not(dep and ppp and r.get('hotelName') and url.startswith('/') and re.match(r'[A-Z]{3}',code)): continue
            if r.get('soldOut'): continue
            m=re.match(r'(\d+) Doros',r.get('participants') or '')
            ad=int(m.group(1)) if m else adults
            if 'Dzieci' in (r.get('participants') or '') and not re.search(r'\+ 0 Dzieci',r['participants']): continue
            bc=[b.get('label') for b in r.get('breadcrumbs') or [] if b.get('label')]
            place=', '.join(x for x in [bc[1] if len(bc)>1 else (bc[0] if bc else ''),(r.get('city') or '').strip()] if x)
            b=(r.get('boardType') or '').strip()
            st=r.get('hotelStandard')
            ta=r.get('tripAdvisorRating')
            n=r.get('duration')
            out.append({'op':'tui','name':r['hotelName'].strip(),'stars':st if isinstance(st,(int,float)) and st>0 else None,
                'place':place,'dep':dep.isoformat(),'ret':ret.isoformat() if ret else None,
                'nights':n if isinstance(n,int) and 'nocleg' in (r.get('durationText') or 'nocleg') else None,
                'board':BOARD.get(b.lower(),b),'from':code[:3],
                'ppp':ppp,'adults':ad,'total':tot if tot else ppp*ad,
                # TripAdvisor (skala 1-5) przeliczony na 0-10.
                'rating':round(float(ta)*2,1) if isinstance(ta,(int,float)) and ta>0 else None,
                'kind':'wypoczynek' if url.startswith('/wypoczynek/') else 'objazd' if url.startswith('/wycieczki') else 'wypoczynek',
                'url':SITE+url})
        except (TypeError,ValueError,KeyError,AttributeError): continue
    return out

def _sources(cc,origin):
    """Listy do przeczytania: (glowne, dodatkowe)."""
    slugs=COUNTRIES[cc]
    if origin: main=['/wypoczynek/%s/%s'%(s,CITY[origin]) for s in slugs]
    else: main=['/wypoczynek/%s/oferty-wakacje-samolotem'%s for s in slugs]
    extra=['/wypoczynek/%s/oferty-first-minute-lato'%s for s in slugs]
    return main,extra

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper()
    if cc not in COUNTRIES or (origin and origin not in CITY):
        return {'offers':[],'total':0,'complete':True,'url':SITE+'/wypoczynek'}
    main,extra=_sources(cc,origin)
    codes=AIRPORTS.get(origin,(origin,)) if origin else None
    offers=[];seen=set();used=[0];incomplete=[False]

    def want(o): return o['dep'].startswith(ym) and (codes is None or o['from'] in codes)
    def take(rows):
        for o in parse(rows):
            if want(o) and o['url'] not in seen: seen.add(o['url']);offers.append(o)
    def fetch(path,n):
        used[0]+=1
        return page_data(http.get(SITE+path+('?page=%d'%n if n>1 else '')))
    def read(paths,fallback=None):
        """Czyta listy na zmiane (strona 1 kazdej, potem 2 …), zeby limit stron rozlozyl sie rowno."""
        state=[]  # [path, next page, pagesCount]
        for p in paths:
            if used[0]>=limit_pages: incomplete[0]=True;return
            rows,pg=fetch(p,1)
            if rows is None and fallback:   # TUI nie ma takiej strony (np. brak lotow z tego miasta do tego kraju)
                fp=fallback(p)
                if used[0]>=limit_pages: incomplete[0]=True;return
                rows,pg=fetch(fp,1);p=fp
            if rows is None: continue
            take(rows);state.append([p,2,int(pg.get('pagesCount') or 1)])
        while True:
            act=[s for s in state if s[1]<=s[2]]
            if not act: return
            for s in act:
                if used[0]>=limit_pages: incomplete[0]=True;return
                rows,_=fetch(s[0],s[1]);s[1]+=1
                if rows is None: s[1]=s[2]+1;continue
                take(rows)
    read(main,fallback=(lambda p:p.rsplit('/',1)[0]+'/oferty-wakacje-samolotem') if origin else None)
    read(extra)
    offers.sort(key=lambda o:(o['ppp'],o['dep']))
    return {'offers':offers,'total':None,'complete':not incomplete[0],'url':SITE+main[0]}
