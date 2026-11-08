"""Wspolna czesc adapterow biur na platformie Bluevendo (Best Reisen, OnHolidays).

Zrodlo: publiczny JSON, ktory sama strona wynikow /wyniki-wyszukiwania wola bez logowania i bez cookies:
  POST <SITE>/api/bv  {"method":"search-search","params":{...}}   (Content-Type: application/json)
Filtry: countryid[] (kraj), startdatefrom/enddateto (miesiac), startnodeid[] (miasta wylotu, nodeid
z GET /api/departure-cities), length[] (noce, puste = dowolne), page/numOnPage, ordername=customerprice
+ orderdirection=ASC (od najtanszych), transporttypeid=1 (samolot). Identyfikatory krajow i miast sa
INNE na kazdej stronie, wiec moduly operatorow podaja wlasne slowniki.
robots.txt obu stron (User-agent *) zabrania tylko /admin/*; /api/bv i /hotel/ sa dozwolone
(sprawdzone 2026-11-08).

Uwagi:
- Jeden wiersz = jedna oferta hotelu z najtanszym terminem w zakresie (mintrip). 'total' = response.total,
  czyli liczba ofert-hoteli, ktora podaje strona.
- enddateto ogranicza date POWROTU (sprawdzone: przy zakresie 1-30.06 zaden powrot nie wypada w lipcu),
  wiec jak na stronie biura wyjazdy z konca miesiaca z powrotem w nastepnym miesiacu nie wchodza.
- Cena: customertotalprice = 'Cena calkowita' na stronie oferty dla 2 doroslych (lot, hotel, wyzywienie,
  transfer - to, co biuro wlicza w cene pakietu). total = ta kwota, ppp = total / 2. Zwykle strona pokazuje
  tez 'Cena za osobe' = total / 2, ale bywa wyzsza (np. OnHolidays Castello Boutique: 'za osobe 2947',
  'calkowita 5009' - sprawdzone 2026-11-08), wiec ppp liczymy z ceny calkowitej, ktora sie placi.
- Zdarza sie, ze strona oferty pokazuje 'Brak dostepnych ofert dla tego hotelu' dla oferty z listy
  (tak samo dla linku wygenerowanego przez strone wynikow) - to blad/opoznienie po stronie biura.
- Link do oferty: /hotel/<kraj>/<region>/<hotel>?ids=<mintrip.id>_<departure>_<arrival>_<offerid>&ad=2&ch=
  (taki sam format generuje sama strona wynikow; Best Reisen dokleja &hid=<hotelid>).
"""
import calendar,json,re,unicodedata,urllib.parse
from . import http

ADULTS=2
BOARD={'sniadania':'Śniadania','tylko sniadania':'Śniadania','sniadanie':'Śniadania',
       '2 posilki':'Śniadania i obiadokolacje','sniadania i obiadokolacje':'Śniadania i obiadokolacje',
       'sniadanie i obiadokolacja':'Śniadania i obiadokolacje','3 posilki':'Pełne wyżywienie',
       'pelne wyzywienie':'Pełne wyżywienie','all inclusive':'All inclusive','ultra all inclusive':'All inclusive',
       'bez wyzywienia':'Bez wyżywienia'}
BOARD_CODE={'BB':'Śniadania','HB':'Śniadania i obiadokolacje','FB':'Pełne wyżywienie','AI':'All inclusive',
            'UAI':'All inclusive','RO':'Bez wyżywienia','SC':'Bez wyżywienia','OV':'Bez wyżywienia'}

def _ascii(t):
    return unicodedata.normalize('NFKD',(t or '').replace('ł','l').replace('Ł','L')).encode('ascii','ignore').decode().lower()
def slug(t):
    return re.sub(r'[^a-z0-9]+','-',_ascii(t)).strip('-')
def board(name,code=None):
    b=BOARD.get(_ascii(name).strip())
    return b or BOARD_CODE.get((code or '').upper()) or (name or '')
def stars(s):
    """'****' albo '4' albo '4.5' -> liczba gwiazdek (None gdy brak)."""
    s=(s or '').strip()
    if not s: return None
    if set(s)=={'*'}: return len(s)
    try: v=float(s.replace(',','.'))
    except ValueError: return None
    if not 0<v<=6: return None
    return int(v) if v==int(v) else v

def month(ym):
    y,m=map(int,ym.split('-'));return f'{y:04d}-{m:02d}-01',f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}'

def nodes(cfg,origin):
    """Lista nodeid miast wylotu: jedno lotnisko (WAW = Chopin+Modlin+Radom) albo wszystkie polskie."""
    if origin: return list(cfg['NODES'].get(origin,[]))
    return [n for v in cfg['NODES'].values() for n in v]

def body(cfg,cc,ym,origin,page,per_page):
    a,b=month(ym)
    return {'method':'search-search','params':{'searchrooms':[{'adults':ADULTS,'infants':0,'childage':[]}],
        'price':{'start':'0','end':'100000'},'length':[],'startdatefrom':a,'enddateto':b,'imgsize':['600x0'],
        'transporttypeid':'1','regionid':[],'cityid':[],'countryid':[cfg['COUNTRIES'][cc]],
        'ordername':'customerprice','orderdirection':'ASC','page':str(page),'numOnPage':per_page,
        'maintenanceid':[],'classificationid':[],'componentstype':[],'startnodeid':nodes(cfg,origin),
        'standards':[],'hoteltypeid':[],'hotelid':[]}}

def list_url(cfg,cc,ym,origin=None,regions=None):
    """Link do tej samej listy na stronie biura (strona wynikow filtruje po regionach, nie po kraju)."""
    a,b=month(ym)
    q={}
    if regions: q['regions']=','.join(regions)
    q.update({'departurenodes':','.join(nodes(cfg,origin)),'startdate':a,'startdateto':b,'adults':str(ADULTS),
              'transporttypeid':'1','ordername':'price','orderdirection':'ASC'})
    return cfg['SITE']+'/wyniki-wyszukiwania?'+urllib.parse.urlencode(q)

_REG={}
def regions(cfg,cc):
    """Id regionow kraju z x-regionlist (tylko do linku dla uzytkownika; blad = link bez regionow)."""
    site=cfg['SITE']
    if site not in _REG:
        try:
            r=json.loads(http.get(site+'/api/bv',data=json.dumps({'method':'x-regionlist','params':{'request':{'transporttypeid':1}}}),
                                  headers={'Content-Type':'application/json','Accept':'application/json'},tries=1))
            R={}
            for x in r['data']['response']['regions']['region']: R.setdefault(x['countryid'],[]).append(x['regionid'])
            _REG[site]=R
        except Exception: return None
    return _REG[site].get(cfg['COUNTRIES'].get(cc))

def _items(d):
    r=(d.get('data') or {}).get('response') or {}
    it=(r.get('items') or {}).get('item') or []
    return [it] if isinstance(it,dict) else it,r.get('total')

def _int(x):
    try: return int(round(float(x)))
    except (TypeError,ValueError): return None

def parse(text,cfg,ym=None,origin=None):
    """Odpowiedz search-search -> oferty. Filtry: wylot w miesiacu ym, wylot z polskiego lotniska (origin)."""
    d=json.loads(text) if isinstance(text,(str,bytes)) else text
    items,_=_items(d);out=[]
    codes=cfg['SAME'].get(origin,{origin}) if origin else set(cfg['NODES'])|{c for v in cfg['SAME'].values() for c in v}
    for x in items:
        t=x.get('mintrip') or {}
        dep,ret=t.get('startdate'),t.get('enddate')
        if not dep or not ret or not x.get('hotelname'): continue
        if ym and not dep.startswith(ym): continue
        if str(x.get('transporttypeid') or '1')!='1': continue
        frm=(t.get('departurecode') or '').upper()
        if frm not in codes: continue              # np. Berlin, Praga, Budapeszt
        tot=_int(x.get('customertotalprice')) or _int(x.get('totalprice'))
        if not tot: continue
        ppp=round(tot/ADULTS)     # 'Cena calkowita' / 2 (patrz uwaga o cenie na gorze)
        try: nights=int(t.get('staylength'))
        except (TypeError,ValueError): nights=None
        ids=f"{t.get('id')}_{t.get('departure')}_{t.get('arrival')}_{x.get('offerid')}"
        path='/'.join(slug(v) for v in (x.get('countryname'),x.get('regionname'),x.get('hotelname')))
        url=f"{cfg['SITE']}/hotel/{path}?ids={ids}&ad={ADULTS}&ch="+(f"&hid={x.get('hotelid')}" if cfg.get('HID') else '')
        ra=x.get('rateaverage')
        try: rating=round(float(ra)*cfg['RATE_SCALE'],1) if ra and cfg.get('RATE_SCALE') else None
        except (TypeError,ValueError): rating=None
        out.append({'op':cfg['OP'],'name':x['hotelname'].strip(),'stars':stars(x.get('standard')),
            'place':', '.join(v.strip() for v in (x.get('regionname'),x.get('cityname')) if v and v.strip()),
            'dep':dep,'ret':ret,'nights':nights,
            'board':board(x.get('maintenancename') or t.get('maintenancename'),x.get('maintenancecode') or t.get('maintenancecode')),
            'from':frm,'ppp':ppp,'adults':ADULTS,'total':tot,'rating':rating,'kind':'wypoczynek','url':url})
    return out

def search(cfg,cc,ym,origin=None,limit_pages=None):
    cc=cc.upper();origin=origin.upper() if origin else None
    if cc not in cfg['COUNTRIES']: return {'offers':[],'total':0,'complete':True,'url':cfg['SITE']}
    if origin and origin not in cfg['NODES']:
        return {'offers':[],'total':0,'complete':True,'url':list_url(cfg,cc,ym,None,regions(cfg,cc))}
    pages=min(limit_pages or cfg['PAGES'],cfg['PAGES'])
    offers=[];seen=set();total=None;complete=False
    for p in range(1,pages+1):
        raw=http.get(cfg['SITE']+'/api/bv',data=json.dumps(body(cfg,cc,ym,origin,p,cfg['PER_PAGE'])),
                     headers={'Content-Type':'application/json','Accept':'application/json'},
                     timeout=cfg.get('TIMEOUT',60),tries=2)
        d=json.loads(raw)
        if not d.get('success',True): raise IOError(f"{cfg['OP']}: odpowiedz bez success")
        items,total=_items(d);total=_int(total) or 0
        for o in parse(d,cfg,ym,origin):
            if o['url'] not in seen: seen.add(o['url']);offers.append(o)
        # strona bywa krotsza niz numOnPage (np. 93 ze 100 przy total 495), wiec konczymy wg total
        if not items or p*cfg['PER_PAGE']>=total: complete=True;break
    offers.sort(key=lambda o:o['ppp'])
    return {'offers':offers,'total':total,'complete':complete,'url':list_url(cfg,cc,ym,origin,regions(cfg,cc))}
