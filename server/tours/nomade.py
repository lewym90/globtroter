"""Nomade (nomade.pl, polska galaz czeskiego Nomade: egzotyka i luksusowe wczasy, pakiety dynamiczne).

Zrodlo: fragment HTML, ktory doladowuje sama strona /wyszukiwane-wycieczki (formularz MagicWare):
  GET /ajax/vysledky-vyhledani?StartDateFrom=RRRR-MM-DD&StartDateTo=RRRR-MM-DD&DestinationID=<id>&DepartureStationID=<id,id>
Serwer filtruje po datach wylotu, kraju i miejscu wylotu (kilka id po przecinku) i zwraca CALA liste w jednym
zapytaniu (brak stronicowania; ~100 KB na kraj). Lista daje jeden wiersz na produkt: najtanszy termin z podanego
zakresu i podanych lotnisk; link prowadzi do tego terminu (TermID, DateFrom, DateTo, Nights, DepartureStationID).
robots.txt nomade.pl: Disallow m.in. /api, /e/, /WebServices; /ajax/ i strony ofert dozwolone (sprawdzone 2026-11-08).

Uwagi:
- Lotniska Nomade: Warszawa (83), Modlin (146), Krakow (76), Poznan (162), Gdansk (78), a takze Berlin i Wieden.
  Bierzemy tylko polskie: origin=None -> wszystkie polskie naraz (wtedy serwer daje najtanszy z nich).
- Cena: 'cena od' z listy (ta sama na stronie terminu, pole 'Cena'). To cena za osobe (pakiet dla 2 doroslych;
  strona tego wprost nie pisze, ale kwoty, np. 3402 zl za 3 noce w 5* na Mykonos z lotem, sa za osobe).
  total = ppp * 2. Strona zastrzega, ze w pakietach dynamicznych cena jest liczona ponownie przy rezerwacji.
- 'total' w wyniku = liczba produktow na liscie (wszystkie, complete=True).
"""
import calendar,html,re,urllib.parse
from . import http

NAME='Nomade'
SITE='https://nomade.pl'
API=SITE+'/ajax/vysledky-vyhledani'
ADULTS=2
# DestinationID z formularza wyszukiwania; kazdy sprawdzony zapytaniem (produkty z polskich lotnisk, 11.2026-12.2027,
# 2026-11-08). BR i KH maja tylko produkty laczone (Argentyna+Brazylia, Tajlandia+Kambodza).
# Bez produktow wtedy: Maroko (1446), RPA (309), Polinezja Francuska (307) - pominiete.
COUNTRIES={'AG':'1355','AR':'290','BB':'1336','BR':'286','CR':'338','DO':'339','ES':'311','GR':'313','ID':'264',
 'KE':'308','KH':'289','LK':'284','MU':'280','MV':'288','MX':'278','MY':'304','NA':'337','PH':'285','SC':'279',
 'TH':'282','TZ':'277','US':'1365','VN':'283'}
STATIONS={'WAW':'83,146','KRK':'76','POZ':'162','GDN':'78'}
STATION_IATA={'83':'WAW','146':'WAW','76':'KRK','162':'POZ','78':'GDN'}
PL_ALL='83,146,76,162,78'
BOARD={'śniadanie':'Śniadania','buffet breakfast':'Śniadania','śniadanie i obiadokolacja':'Śniadania i obiadokolacje',
       'pełne wyżywienie':'Pełne wyżywienie','all inclusive':'All inclusive','bez wyżywienia':'Bez wyżywienia'}
KIND={'wypoczynek':'wypoczynek','wypoczynek 2w1':'wypoczynek','zwiedzanie i wypoczynek':'objazd'}

def _params(cc,ym,origin):
    y,m=map(int,ym.split('-'))
    return {'StartDateFrom':f'{y:04d}-{m:02d}-01','StartDateTo':f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}',
            'DestinationID':COUNTRIES[cc],'DepartureStationID':STATIONS[origin] if origin else PL_ALL}

def _qs(p): return urllib.parse.urlencode(p,safe=',')

def list_url(cc,ym,origin=None):
    return SITE+'/wyszukiwane-wycieczki?'+_qs(_params(cc,ym,origin))

def _txt(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()

def parse(text,ym=None,origin=None):
    """Fragment HTML listy -> oferty (tylko polskie lotniska; filtr miesiaca wylotu i lotniska, jesli podane)."""
    out=[]
    for b in text.split('<div class="ss-extract-line">')[1:]:
        h=re.search(r'class="ss-extract-line-head__title-product[^"]*">\s*<a href="([^"]+)"[^>]*>(.*?)</a>',b,re.S)
        if not h: continue
        url=html.unescape(h.group(1));q=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        frm=STATION_IATA.get(q.get('DepartureStationID'))
        dep=q.get('DateFrom');ret=q.get('DateTo')
        if not frm or not dep or (origin and frm!=origin) or (ym and not dep.startswith(ym)): continue
        pr=re.search(r'ss-extract-line-foot__price">.*?<strong>([\d\s\xa0]+)</strong>\s*PLN',b,re.S)
        if not pr: continue
        ppp=int(re.sub(r'\D','',pr.group(1)))
        name=_txt(h.group(2));st=re.search(r'\s(\d(?:[.,]5)?)\*$',name)
        stars=None
        if st:
            name=name[:st.start()].strip();v=float(st.group(1).replace(',','.'));stars=int(v) if v==int(v) else v
        dst=re.search(r'title-destination[^>]*>(.*?)</div>',b,re.S)
        links=[_txt(x) for x in re.findall(r'<a [^>]*>(.*?)</a>',dst.group(1),re.S)] if dst else []
        place=', '.join(links[1:]) or (links[0] if links else '')
        sp=re.search(r'species-product[^>]*>(.*?)</span>',b,re.S);sp=_txt(sp.group(1)) if sp else ''
        di=re.search(r'foot__diet">.*?<span class="">(.*?)</span>',b,re.S);di=_txt(di.group(1)) if di else ''
        try: nights=int(q.get('Nights'))
        except (TypeError,ValueError): nights=None
        out.append({'op':'nomade','name':name,'stars':stars,'place':place,'dep':dep,'ret':ret,'nights':nights,
            'board':BOARD.get(di.lower(),di),'from':frm,'ppp':ppp,'adults':ADULTS,'total':ppp*ADULTS,'rating':None,
            'kind':KIND.get(sp.lower(),'wypoczynek'),'url':url})
    return out

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper()
    if origin: origin=origin.upper()
    if cc not in COUNTRIES or (origin and origin not in STATIONS):
        return {'offers':[],'total':0,'complete':True,'url':SITE}
    p=_params(cc,ym,origin)
    t=http.get(API+'?'+_qs(p))
    if re.search(r'(?i)captcha|cf-turnstile',t) and 'ss-extract-line' not in t: raise http.Blocked('nomade.pl: captcha')
    offers=parse(t,ym,origin)
    return {'offers':offers,'total':len(offers),'complete':True,'url':list_url(cc,ym,origin)}
