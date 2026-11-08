"""Grecos Holiday (grecos.pl): wypoczynek w Grecji i na Cyprze.

Zrodlo: publiczne JSON, ktore strona listy ofert (/wakacje) wola sama:
  /api/sitecore/OffersList/LoadMoreOffers?DateOfDeparture=YYYYMMDD&DateOfReturn=YYYYMMDD&DurationInterval=n:n&Dest=..&From=..
robots.txt (User-agent *) blokuje /sitecore (prefiks), /api/sitecore/productfeed/getproductfeed i katalogi techniczne;
/api/sitecore/OffersList/ jest dozwolone. Jedno zapytanie zwraca od razu caly wynik (bez stron),
ale tylko JEDEN wiersz na hotel: najtanszy termin w podanym oknie.

Daty: DateOfDeparture = najwczesniejszy wylot, DateOfReturn = najpozniejszy POWROT (nie wylot).
DurationInterval = dlugosc pobytu liczona w dniach kalendarzowych (data powrotu - data wylotu).
Dla miesiaca M pytamy osobno o kazda dlugosc n: wylot >= 1. dzien M, powrot <= ostatni dzien M + n,
dlugosc dokladnie n. Wtedy wylot <= ostatni dzien M, czyli dostajemy dokladnie wyloty w M
(lacznie z wyjazdami, ktore wracaja w nastepnym miesiacu), najtanszy na hotel dla kazdej dlugosci.
Powrot = wylot + n. Noclegi: Grecos podaje 'Duration' (tyle 'dni' pokazuje strona oferty); liczba noclegow
na stronie oferty = min(Duration, n) (sprawdzone na 110 terminach z HotelAllOffersAsJson).

Ceny: Merlin_AdultPrice = cena za 1 doroslego, Merlin_FullPriceParsed = razem za 2 doroslych
(Adults=2&Children=0). Strona oferty pokazuje te same kwoty ('X ZŁ' i 'Y ZŁ / 1 DOROSŁY'); Grecos nie dolicza
do nich osobno TFG/TFP. Odpowiedz serwera IIS dla 'deflate' jest surowym deflate, dlatego prosimy tylko o gzip.
"""
import calendar,datetime as dt,json,re,urllib.parse
from . import http

NAME='Grecos'
SITE='https://www.grecos.pl'
# Id regionow z listy 'Kierunek' na grecos.pl/wakacje (sprawdzone 2026-11-08; Grecos nie sprzedaje innych krajow).
_GR=['3344','1324','2302','4385','6745','83','84','56429','89','5985','1459','3272','1493','149','150','177','1066']
_CY=['17','127']
COUNTRIES={'GR':','.join(_GR),'CY':','.join(_CY)}
# Lotniska z listy 'Wylot z' (wartosci From). Warszawa = Chopin + Modlin; Radom jest osobna pozycja na stronie.
FROM={'KTW':'KTW','WAW':'WAW,WMI','KRK':'KRK','GDN':'GDN','WRO':'WRO','POZ':'POZ','RZE':'RZE','LUZ':'LUZ','BZG':'BZG','LCJ':'LCJ','RDO':'RDO'}
CITY={'Katowice':'KTW','Warszawa':'WAW','Warszawa Modlin':'WMI','Warszawa - Radom':'RDO','Radom':'RDO','Kraków':'KRK','Gdańsk':'GDN',
      'Wrocław':'WRO','Poznań':'POZ','Rzeszów':'RZE','Lublin':'LUZ','Bydgoszcz':'BZG','Łódź':'LCJ','Zielona Góra':'IEG'}
# Dlugosci (dni od wylotu do powrotu), o ktore pytamy dokladnie (sezon 2027 ma tylko te: 3,7,8,10,11,12,14,15).
SPANS=[7,14,10,11,8,15,12,3]
# Pozostale dlugosci sprawdzamy jednym zapytaniem na zakres (powrot <= koniec miesiaca + gorna granica): pusty wynik
# znaczy, ze takich wyjazdow z tego miesiaca nie ma; jesli cos jest, pytamy dokladnie o kazda dlugosc z zakresu.
PROBES=[(1,2),(4,6),(9,9),(13,13),(16,21)]
BOARD={'all inclusive':'All inclusive','śniadanie':'Śniadania','śniadania':'Śniadania','śniadanie i obiadokolacja':'Śniadania i obiadokolacje',
       'śniadania i obiadokolacje':'Śniadania i obiadokolacje','pełne wyżywienie':'Pełne wyżywienie','bez wyżywienia':'Bez wyżywienia'}
_STARS={'one':1,'two':2,'three':3,'four':4,'five':5}
API=SITE+'/api/sitecore/OffersList/LoadMoreOffers?'

def _num(s):
    d=re.sub(r'\D','',str(s or ''))
    return int(d) if d else None
def _stars(css):
    m=re.match(r'(one|two|three|four|five)-stars',css or '')
    if not m: return None
    return _STARS[m.group(1)]+(0.5 if 'stars-plus' in css else 0)
def _date(s):
    m=re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})',s or '')
    return dt.date(int(m.group(3)),int(m.group(2)),int(m.group(1))) if m else None
def _q(cc,first,ret_max,span,origin):
    p={'DateOfDeparture':first.strftime('%Y%m%d'),'DateOfReturn':ret_max.strftime('%Y%m%d')}
    if span: p['DurationInterval']='%d:%d'%span
    p.update({'ObjectType':'H,R,AP','Dest':COUNTRIES[cc]})
    if origin: p['From']=FROM[origin]
    p.update({'Adults':'2','Children':'0','pageFrom':'0','setFilters':'true'})
    return urllib.parse.urlencode(p,safe=',:')

def _get(cc,first,ret_max,span,origin):
    rows=json.loads(http.get(API+_q(cc,first,ret_max,span,origin),headers={'Accept-Encoding':'gzip'}))
    if not isinstance(rows,list): raise IOError('grecos: nieoczekiwana odpowiedz')
    return rows

def parse(text,span=None,adults=2):
    """Wiersze z LoadMoreOffers -> oferty. span = dokladna liczba dni wylot->powrot uzyta w zapytaniu (DurationInterval n:n);
    bez niej nie znamy daty powrotu i liczby noclegow (ret/nights = None)."""
    rows=json.loads(text) if isinstance(text,str) else text
    out=[]
    for r in rows or []:
        try:
            dep=_date(r.get('Merlin_ParsedStartFullDate'))
            ppp=_num(r.get('Merlin_AdultPrice'));tot=_num(r.get('Merlin_FullPriceParsed'))
            if not(dep and ppp and r.get('Hotel_Name') and r.get('Merlin_Id') and r.get('Hotel_OfferUrlWithOfferCode')): continue
            d=_num(r.get('Merlin_Duration'))
            ret=dep+dt.timedelta(days=span) if span else None
            nights=(min(d,span) if d else span) if span else None
            city=(r.get('Merlin_FlightFrom') or '').strip()
            b=(r.get('Merlin_BoardStandardDesc') or '').strip()
            place=', '.join(x for x in [(r.get('Hotel_Location_Name') or '').strip(),(r.get('Merlin_City') or '').strip()] if x)
            out.append({'op':'grecos','name':r['Hotel_Name'].strip(),
                'stars':_stars(r.get('Hotel_Standard_Stars_Css')) or _stars(r.get('Hotel_Local_Standard_Stars_Css')),
                'place':place,'dep':dep.isoformat(),'ret':ret.isoformat() if ret else None,'nights':nights,
                'board':BOARD.get(b.lower(),b),'from':CITY.get(city,city),
                'ppp':ppp,'adults':adults,'total':tot if tot else ppp*adults,
                # Hotel_AverageRating jest zawsze '0' i nie wiadomo, w jakiej skali bylby podany.
                'rating':None,'kind':'wypoczynek',
                'url':SITE+r['Hotel_OfferUrlWithOfferCode']+r['Merlin_Id']+(r.get('Query_AdultsChildenQueryString') or '&Adults=%d&Children=0'%adults)})
        except (TypeError,ValueError,KeyError): continue
    return out

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper();y,m=int(ym[:4]),int(ym[5:7])
    first=dt.date(y,m,1);last=dt.date(y,m,calendar.monthrange(y,m)[1])
    link=SITE+'/wakacje?'+_q(cc,first,last,None,origin) if cc in COUNTRIES and (origin is None or origin in FROM) else SITE+'/wakacje'
    if cc not in COUNTRIES or (origin and origin not in FROM):
        return {'offers':[],'total':0,'complete':True,'url':link}
    seen=set();offers=[];done=0;todo=[(n,n) for n in SPANS]+[('probe',p) for p in PROBES];skipped=0
    while todo:
        if done>=limit_pages: skipped=len(todo);break
        a,b=todo.pop(0)
        if a=='probe':
            lo,hi=b
            if lo==hi: a,b=lo,hi
            else:
                rows=_get(cc,first,last+dt.timedelta(days=hi),(lo,hi),origin);done+=1
                if rows:    # cokolwiek (takze wylot w nastepnym miesiacu) -> pytamy dokladnie
                    todo[0:0]=[(n,n) for n in range(lo,hi+1)]
                continue
        rows=_get(cc,first,last+dt.timedelta(days=a),(a,a),origin);done+=1
        for o in parse(rows,span=a):
            if not o['dep'].startswith(ym) or o['url'] in seen: continue
            seen.add(o['url']);offers.append(o)
    offers.sort(key=lambda o:(o['ppp'],o['dep']))
    # Grecos nie podaje liczby dla takiego zestawu zapytan (strona pokazuje 'Znaleziono N' tylko dla jednego okna dat).
    return {'offers':offers,'total':None,'complete':not skipped,'url':link}
