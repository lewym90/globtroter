"""Itaka (itaka.pl): oferty z listy wynikow wyszukiwania.

Strona /wyniki-wyszukiwania/wakacje/<kraj>/ jest renderowana na serwerze (Next.js) i ma oferty
jako dane w <script id="__NEXT_DATA__">. Jeden wiersz = jeden hotel (najtansza oferta), 15 na strone,
sortowanie order=priceAsc (od najtanszych).

Uwagi o parametrach (sprawdzone na zywo 2026-11):
- dateFrom ogranicza date WYLOTU od dolu, dateTo ogranicza date POWROTU od gory. Dlatego dla miesiaca
  pytamy dateTo = koniec miesiaca + 14 dni i sami odrzucamy wyloty spoza miesiaca. Hotel, ktorego
  najtansza oferta w tym oknie wypada po koncu miesiaca, nie pojawi sie wcale (strona pokazuje tylko
  jedna oferte na hotel), wiec lista dla miesiaca moze byc niepelna o takie hotele.
- departuresByPlane przyjmuje liste kodow po przecinku. Nieznany kod strona ignoruje i zwraca wszystko,
  lacznie z ofertami z dojazdem wlasnym (bez lotu) - takie oferty zawsze odrzucamy, a lotnisko wylotu
  sprawdzamy z nazwy w danych.
- Bez departuresByPlane strona daje glownie oferty z dojazdem wlasnym, wiec dla origin=None podajemy
  wszystkie obslugiwane lotniska.
- robots.txt (User-agent *) zabrania /reservation*, /booking*, /api*, /_next/static/, /zapytanie-ofertowe/*,
  /rabat-za-newsletter, /regulamin. Pobieramy tylko /wyniki-wyszukiwania/.

Ceny: 'ppp' i 'total' ZAWIERAJA obowiazkowe oplaty doliczane przez Itake na stronie oferty
(additionalPayments, obecnie TFG + TFP = 20 zl od osoby; w ofercie widac "1 289 zl +20 zl (TFG i TFP)").
Lista podaje cene katalogowa bez nich. Ceny dla 2 doroslych.
Ocena klientow: Itaka podaje w skali 0-6; przeliczamy na 0-10 (x/6*10).
"""
import calendar,datetime as dt,json,re,unicodedata,urllib.parse as up
from . import http

NAME='Itaka'
SITE='https://www.itaka.pl'
OP='itaka'
# Zweryfikowane 2026-11: kazdy slug zwraca oferty z tego kraju (nieznany slug zwraca wszystkie kraje).
COUNTRIES={'ES':'hiszpania','GR':'grecja','TR':'turcja','EG':'egipt','BG':'bulgaria','HR':'chorwacja','IT':'wlochy',
    'PT':'portugalia','CY':'cypr','AL':'albania','TN':'tunezja','MA':'maroko','MT':'malta','ME':'czarnogora'}
# Kody lotnisk Itaki (zweryfikowane: kazdy daje loty z tego miasta). WMI Itaka nie zna (ignoruje), Radom jest
# u Itaki jako "Warszawa-Radom", wiec WAW = Okecie + Modlin + Radom. Szczytno-Szymany to u Itaki SZY.
ORIGINS={'WAW':['WAW','WMI','RDO'],'KTW':['KTW'],'KRK':['KRK'],'GDN':['GDN'],'WRO':['WRO'],'POZ':['POZ'],'RZE':['RZE'],
    'LUZ':['LUZ'],'BZG':['BZG'],'LCJ':['LCJ'],'SZZ':['SZZ'],'OSZ':['SZY']}
# Nazwa miasta wylotu w danych Itaki -> nasz kod.
CITY={'katowice':'KTW','warszawa-okecie':'WAW','warszawa-modlin':'WAW','warszawa-radom':'WAW','warszawa':'WAW','radom':'WAW',
    'krakow':'KRK','gdansk':'GDN','wroclaw':'WRO','poznan':'POZ','rzeszow':'RZE','lublin':'LUZ','bydgoszcz':'BZG',
    'lodz':'LCJ','szczecin':'SZZ','olsztyn-mazury':'OSZ','szczytno':'OSZ','olsztyn':'OSZ'}
KIND={'holidays':'wypoczynek','roundTrip':'objazd','cityBreak':'city break'}
PATH={'roundTrip':'wycieczki','cityBreak':'city-break'}
PER_PAGE=15
BOARD={'all inclusive':'All inclusive','ultra all inclusive':'All inclusive','sniadania':'Śniadania','2 posilki':'Śniadania i obiadokolacje',
    'sniadania i obiadokolacje':'Śniadania i obiadokolacje','3 posilki':'Pełne wyżywienie','pelne wyzywienie':'Pełne wyżywienie',
    'bez wyzywienia':'Bez wyżywienia'}

def _ascii(t):
    return unicodedata.normalize('NFKD',t.replace('ł','l').replace('Ł','L')).encode('ascii','ignore').decode().lower()
def slug(t):
    return re.sub(r'[^a-z0-9]+','-',_ascii(t.replace('&',' and ').replace('´',''))).strip('-')
def city_code(title):
    return CITY.get(_ascii(title or '').strip())

def board(t):
    """Nazwa wyzywienia Itaki -> nazwa z kontraktu ('2 posilki' = sniadania i obiadokolacje); nieznana zostaje bez zmian."""
    return BOARD.get(_ascii(t or '').strip(),t) if t else None

def _month(ym):
    y,m=map(int,ym.split('-'));a=dt.date(y,m,1);b=dt.date(y,m,calendar.monthrange(y,m)[1]);return a,b

def list_url(cc,ym,origin,page=1):
    a,b=_month(ym);q={'dateFrom':a.strftime('%d.%m.%Y'),'dateTo':(b+dt.timedelta(14)).strftime('%d.%m.%Y')}
    codes=ORIGINS[origin] if origin else sorted({c for v in ORIGINS.values() for c in v})
    q['departuresByPlane']=','.join(codes);q['order']='priceAsc'
    if page>1: q['page']=page
    return f"{SITE}/wyniki-wyszukiwania/wakacje/{COUNTRIES[cc]}/?"+up.urlencode(q,safe='.')

def _data(text):
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',text,re.S)
    if not m: raise ValueError('itaka: brak __NEXT_DATA__')
    pp=json.loads(m.group(1))['props']['pageProps']
    for q in pp.get('initialQueryState',{}).get('queries',[]):
        mr=(((q.get('state') or {}).get('data') or {}).get('main') or {}).get('multiRoomRates')
        if mr is not None: return mr
    raise ValueError('itaka: brak listy ofert w __NEXT_DATA__')

def total_count(text):
    return _data(text).get('ratesCount')

def parse(text,cc=None,ym=None,origin=None):
    """Oferty z HTML strony wynikow. Filtruje: tylko z lotem, wylot w miesiacu ym, z lotniska origin, kraj cc."""
    rows=_data(text).get('list') or [];out=[]
    for o in rows:
        segs=o.get('segments') or []
        fl=[s for s in segs if s.get('type')=='flight']
        main=[s for s in segs if s.get('type') in('hotel','trip')]
        if not fl or not main: continue          # dojazd wlasny albo nieznany ksztalt
        h=main[0];c=h.get('content') or {}
        frm=city_code(fl[0]['departure'].get('title'))
        if origin and frm!=origin: continue
        dep,ret=fl[0]['beginDate'],fl[-1]['endDate']
        if ym and dep[:7]!=ym: continue
        geo=c.get('geographicalIdentifiers') or []
        country=[g for g in geo if g.get('type')=='country']
        if cc and COUNTRIES.get(cc) and country and country[0]['id']!=COUNTRIES[cc]: continue
        pg=(o.get('participantGroups') or [None])[0]
        if not pg or not pg.get('participants'): continue
        ad=[p for p in pg['participants'] if p.get('type')=='adult']
        extra=lambda p:sum(x.get('amount',0) for x in p.get('additionalPayments') or [])
        ppp=round((ad[0]['price']+extra(ad[0]))/100)
        tot=round((pg['price']+sum(extra(p) for p in pg['participants']))/100)
        hp=(h.get('participantGroups') or [{}])[0]
        brd=board((hp.get('mealGroup') or hp.get('meal') or {}).get('title'))
        reg=[g for g in geo if g.get('type')!='country']
        rt=o.get('rateType');stars=c.get('hotelRating')
        cr=(c.get('reviews') or {}).get('customersRating')
        try: nights=(dt.date.fromisoformat(h['endDate'])-dt.date.fromisoformat(h['beginDate'])).days
        except Exception: nights=None
        if rt=='roundTrip' or not nights: nights=(dt.date.fromisoformat(ret)-dt.date.fromisoformat(dep)).days
        prov=reg[-1]['id'] if reg else ''
        rid=up.quote(up.quote(pg['rateId'],safe=''),safe='')
        parts=[PATH.get(rt,'wczasy'),country[0]['id'] if country else '',prov,f"{slug(c.get('title',''))},{o.get('supplierObjectId')}"]
        url=SITE+'/'+'/'.join(x for x in parts if x)+'/?id='+rid
        out.append({'op':OP,'name':c.get('title'),'stars':(stars/10 if stars else None),
            'place':', '.join(g['title'] for g in reg) or (country[0]['title'] if country else ''),
            'dep':dep,'ret':ret,'nights':nights,'board':brd,'from':frm or fl[0]['departure'].get('title'),
            'ppp':ppp,'adults':len(ad),'total':tot,'rating':(round(cr/6*10,1) if cr else None),
            'kind':KIND.get(rt,'wypoczynek'),'url':url})
    return out

def search(cc,ym,origin=None,limit_pages=40):
    if cc not in COUNTRIES: return {'offers':[],'total':0,'complete':True,'url':SITE}
    if origin and origin not in ORIGINS: return {'offers':[],'total':0,'complete':True,'url':list_url(cc,ym,None)}
    first=list_url(cc,ym,origin);offers=[];seen=set();total=None;complete=False
    for p in range(1,limit_pages+1):
        t=http.get(list_url(cc,ym,origin,p))
        if total is None: total=total_count(t)
        rows=_data(t).get('list') or [];n=len(rows)
        if p==1 and origin and rows and not any(city_code(([x for x in r.get('segments') or [] if x.get('type')=='flight'] or [{}])[0]
                                                         .get('departure',{}).get('title'))==origin for r in rows):
            # Itaka nie ma lotow z tego lotniska do tego kraju i zignorowala filtr (pokazuje wszystko) - koniec
            return {'offers':[],'total':0,'complete':True,'url':first}
        for o in parse(t,cc,ym,origin):
            if o['url'] not in seen: seen.add(o['url']);offers.append(o)
        if n<PER_PAGE or p*PER_PAGE>=(total or 0): complete=True;break
    offers.sort(key=lambda o:o['ppp'])
    # total = liczba hoteli, ktora Itaka podaje dla tego zapytania (okno powrotu do konca miesiaca + 14 dni),
    # wiec zawiera tez hotele, ktorych oferta wylatuje juz w nastepnym miesiacu.
    return {'offers':offers,'total':total,'complete':complete,'url':first}
