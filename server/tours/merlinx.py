"""Wspolna obsluga stron biur na platformie MerlinX (VCMS): Dertour, TOP Touristik, Matimpex.
To nie jest biuro (nie ma go w OPS), tylko pomocnik dla modulow dertour/toptouristik/matimpex.

Jak dziala strona biura (sprawdzone 2026-11-08):
- Strona wyszukiwania <BASE>?transport=rtrip&des[]=<id kraju>:&depd=DD.MM.RRRR&retd=DD.MM.RRRR&dn=<hex miast>&ad=2&ch=0
  zawiera widget listy (data-widgetname="Widget\\Results\\TripListWidget" data-id="<id>"). Lista jest doladowywana
  przez POST <BASE>wapi/?<te same parametry> z cialem
  d[0][m]=<id widgetu>&d[0][d][resultType]=offers&d[0][d][page]=N&d[0][a]=<akcja>&c[rt]=offers-listing.
  Odpowiedz: JSON {"d":[{"d":{"roffers":[...], "moreOffersAvailable":bool, "offers":"<html>"}}],"status":"ok"}.
- Akcja 'getupdate' z d[0][d][allPages]=1 i page=N zwraca strony 0..N naraz (5 + 20*N ofert; tak strona
  odtwarza liste po powrocie). Akcja 'moreoffers' z page=N zwraca jedna strone (strona 0: 5 ofert, dalej po 20).
  Wiekszej strony nie ma (brak parametru rozmiaru w skrypcie strony). Pierwsze zapytanie: getupdate/allPages
  page=1 (25 ofert), dalej moreoffers page=2,3,... Kazde zapytanie to ok. 0,5 MB (lista w HTML + JSON), dlatego
  nie bierzemy allPages dla duzego N (10 MB i wiecej w jednym kawalku).
- Sortowanie: domyslne 'opc' = cena rosnaco (wybrane na stronie), wiec limit stron zostawia najtansze oferty.
  Przy rownych cenach kolejnosc miedzy zapytaniami bywa rozna: na granicy stron oferta z ta sama cena moze
  wypasc lub powtorzyc sie (powtorki usuwamy).
- Lista daje JEDNA oferte na hotel/produkt (najtanszy termin w zakresie dat). Liczby ofert serwis nie podaje
  (tylko moreOffersAvailable), wiec 'total' = liczba hoteli, gdy przeczytalismy wszystko, inaczej None.
- depd/retd: wylot >= depd i powrot <= retd. Bierzemy 1..ostatni dzien miesiaca (tak jak Exim), wiec wyjazd
  pod koniec miesiaca z powrotem w nastepnym nie wchodzi. Szerszy zakres nie pomaga: hotel jest pokazany raz,
  z najtanszym terminem, ktory moglby wypasc w nastepnym miesiacu.
- dn: nazwy miast wylotu zakodowane jako '0x'+hex(UTF-8), kilka po przecinku (sprawdzone na Matimpex).
- Cena: ofr_priceAdult (za osobe) i ofr_priceTotal (za 2 doroslych), tak jak na liscie i na stronie oferty
  ('Cena za os.', og:price). Czy TFG jest wliczony, mowi pole ofr_TFGIncluded (TOP: tak; Dertour: nie i strona
  oferty pisze 'TFG nie jest wliczony w cene', kwoty nie podaje, wiec jej nie doliczamy).
- Strona ma wbudowany mechanizm captcha (dla formularzy). Jesli zamiast JSON przyjdzie captcha albo blad z
  captcha, rzucamy http.Blocked i nie probujemy tego obchodzic.
robots.txt (dertour.pl, toptouristik.pl, matimpex.pl, 2026-11-08): reguly tylko dla wybranych botow
(Crawl-delay), nic dla User-agent * - sciezki /index/... dozwolone.
"""
import calendar,datetime,json,re,threading,urllib.parse
from . import http

ADULTS=2
# lotniska -> nazwy miast w slowniku depAjax MerlinX (wspolny dla wszystkich trzech stron)
DEP={'WAW':['Warszawa','Warszawa - Modlin','Warszawa - Radom'],'KTW':['Katowice'],'KRK':['Kraków'],'GDN':['Gdańsk'],
     'WRO':['Wrocław'],'POZ':['Poznań'],'RZE':['Rzeszów'],'LUZ':['Lublin'],'BZG':['Bydgoszcz'],'LCJ':['Łódź'],
     'SZZ':['Szczecin'],'OSZ':['Olsztyn - Mazury']}
CITY={c:k for k,v in DEP.items() for c in v}
# w wynikach nazwa bywa inna niz w slowniku (TOP: 'Modlin'); filtr dn 'Warszawa - Modlin' zwraca te oferty
CITY.update({'Modlin':'WAW','Radom':'WAW','Warszawa-Modlin':'WAW','Warszawa-Radom':'WAW','Olsztyn-Mazury':'OSZ','Szczytno':'OSZ'})
MON={'sty':1,'lut':2,'mar':3,'kwi':4,'maj':5,'cze':6,'lip':7,'sie':8,'wrz':9,'paz':10,'paź':10,'lis':11,'gru':12}
BOARD={'śniadanie':'Śniadania','śniadania':'Śniadania','śniadanie i obiadokolacja':'Śniadania i obiadokolacje',
       'śniadania i obiadokolacje':'Śniadania i obiadokolacje','dwa posiłki':'Śniadania i obiadokolacje',
       'pełne wyżywienie':'Pełne wyżywienie','all inclusive':'All inclusive','bez wyżywienia':'Bez wyżywienia',
       'według programu':'Według programu'}
KIND={'wczasy':'wypoczynek','objazd':'objazd','wycieczka objazdowa':'objazd','objazdówka':'objazd','city break':'city break'}
HDR={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','X-Requested-With':'XMLHttpRequest',
     'Accept':'application/json, text/javascript, */*; q=0.01'}

def hexname(s): return '0x'+s.encode('utf-8').hex()

def params(des,ym,origin,extra=()):
    """Parametry listy (kolejnosc jak na stronie). des = id kraju MerlinX, np. '15'."""
    y,m=map(int,ym.split('-'))
    cities=DEP[origin] if origin else [c for v in DEP.values() for c in v]
    p=[('transport','rtrip'),('des[]',f'{des}:'),('depd',f'01.{m:02d}.{y:04d}'),
       ('retd',f'{calendar.monthrange(y,m)[1]:02d}.{m:02d}.{y:04d}'),('dn',','.join(hexname(c) for c in cities))]
    return p+list(extra)+[('ad',str(ADULTS)),('ch','0')]

def qs(p): return urllib.parse.urlencode(p,safe=',')

def _date(s,fallback=None):
    """'15.06.2027' albo '14 Maj 2027' -> '2027-06-15'."""
    s=(s or '').strip()
    m=re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})$',s)
    if m: d,mo,y=m.groups()
    else:
        m=re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})$',s)
        if not m or m.group(2).lower()[:3] not in MON: return fallback
        d,mo,y=m.group(1),MON[m.group(2).lower()[:3]],m.group(3)
    try: return datetime.date(int(y),int(mo),int(d)).isoformat()
    except ValueError: return fallback

def _int(x):
    try: return int(round(float(str(x).replace(' ','').replace(',','.'))))
    except (TypeError,ValueError): return None

def _stars(c):
    c=_int(c)
    if not c: return None
    return c//10 if c%10==0 else c/10

def _board(s):
    s=(s or '').strip()
    return BOARD.get(s.lower(),s)

def load(text):
    """Odpowiedz wapi -> slownik danych widgetu; captcha/blokada -> http.Blocked."""
    if isinstance(text,dict): d=text
    else:
        try: d=json.loads(text)
        except ValueError:
            if re.search(r'(?i)captcha|turnstile|challenge',text or ''): raise http.Blocked('MerlinX: captcha')
            raise IOError('MerlinX: odpowiedz nie jest JSON')
    try: x=d['d'][0]
    except (KeyError,IndexError,TypeError): raise IOError('MerlinX: nieznany format odpowiedzi')
    if not x.get('d'):
        e=str(x.get('e') or '')
        if re.search(r'(?i)captcha|block|robot',e): raise http.Blocked('MerlinX: '+e[:80])
        raise IOError('MerlinX: blad '+e[:80])
    return x['d']

def parse(text,op,base,ym=None,kind='wypoczynek',origin=None):
    """JSON wapi (lub jego czesc d) -> oferty. Filtr: miesiac wylotu (ym) i polskie lotnisko (origin albo dowolne z DEP)."""
    x=text if isinstance(text,dict) and 'roffers' in text else load(text)
    out=[]
    for o in x.get('roffers') or []:
        if not o.get('detailsUrl') or not o.get('obj_name'): continue
        frm=CITY.get((o.get('trp_depDesc') or '').strip())
        if not frm or (origin and frm!=origin): continue
        om=re.search(r'/(\d{8})/',o.get('ofr_omnibusUrl') or '')
        fb=f'{om.group(1)[:4]}-{om.group(1)[4:6]}-{om.group(1)[6:]}' if om else None
        dep=_date(o.get('trp_depDateFull'),fb)
        nights=_int(o.get('trp_stay'))
        if not dep or (ym and not dep.startswith(ym)): continue
        ret=_date(o.get('trp_rDepDateFull'))
        if not ret and nights: ret=(datetime.date.fromisoformat(dep)+datetime.timedelta(days=nights)).isoformat()
        ppp=_int(o.get('ofr_priceAdult'));total=_int(o.get('ofr_priceTotal'))
        if not ppp: continue
        if not total: total=ppp*ADULTS
        place=', '.join(dict.fromkeys(v for v in (o.get('obj_region'),o.get('obj_city')) if v))
        out.append({'op':op,'name':o['obj_name'].strip(),'stars':_stars(o.get('obj_category')),'place':place,
            'dep':dep,'ret':ret,'nights':nights,'board':_board(o.get('obj_xServiceIdAsDesc') or o.get('obj_xServiceDesc')),
            'from':frm,'ppp':ppp,'adults':ADULTS,'total':total,'rating':None,
            'kind':KIND.get((o.get('obj_typeAsDesc') or '').strip().lower(),kind),
            'url':urllib.parse.urljoin(base,o['detailsUrl'])})
    return out

_wid={};_wl=threading.Lock()
def widget(base,p):
    """Id widgetu listy ze strony wyszukiwania (jedno zwykle zapytanie; pamietane w procesie)."""
    with _wl:
        if base in _wid: return _wid[base]
    t=http.get(base+'?'+qs(p))
    m=re.search(r'data-widgetname="Widget\\+Results\\+TripListWidget"\s*data-id="(\d+)"',t)
    if not m:
        if re.search(r'(?i)cf-turnstile|captcha-form|g-recaptcha',t): raise http.Blocked('MerlinX: captcha')
        raise IOError('MerlinX: brak widgetu listy na '+base)
    with _wl: _wid[base]=m.group(1)
    return m.group(1)

def _body(wid,page,action):
    b=[('d[0][m]',wid),('d[0][d][resultType]','offers'),('d[0][d][page]',str(page))]
    if action=='getupdate': b.append(('d[0][d][allPages]','1'))
    return urllib.parse.urlencode(b+[('d[0][a]',action),('c[rt]','offers-listing')])

def search(op,base,countries,cc,ym,origin=None,limit_pages=40,extra=(),kind='wypoczynek'):
    cc=cc.upper()
    if origin: origin=origin.upper()
    if cc not in countries or (origin and origin not in DEP):
        return {'offers':[],'total':0,'complete':True,'url':base}
    p=params(countries[cc],ym,origin,extra);url=base+'?'+qs(p)
    wid=widget(base,p);api=base+'wapi/?'+qs(p)
    offers=[];seen=set();page=1;n=0;more=True
    while more and n<limit_pages:
        action='getupdate' if n==0 else 'moreoffers'
        try: x=load(http.get(api,data=_body(wid,page,action),headers=HDR))
        except IOError:
            with _wl: _wid.pop(base,None)   # id widgetu moglo sie zmienic: nastepne wyszukiwanie pobierze strone
            raise
        n+=1
        more=bool(x.get('moreOffersAvailable')) and bool(x.get('roffers'))
        for o in parse(x,op,base,ym,kind,origin):
            k=o['url'].split('&id=')[-1]
            if k in seen: continue
            seen.add(k);offers.append(o)
        del x;page+=1
    complete=not more
    return {'offers':offers,'total':len(offers) if complete else None,'complete':complete,'url':url}
