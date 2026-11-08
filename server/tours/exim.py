"""Exim Tours (www.exim.pl, platforma DER Touristik / Fischer).

Zrodlo: publiczny JSON, ktory sama strona wynikow /wyszukanie wola bez logowania:
  /api/searchapi/getsearchresult?d=<id regionow>&dd=<od>&rd=<do>&nn=<noce>&tt=1&to=<lotniska>&ac1=2
      &sortby=PriceTotal&sortorder=0&pitg=<na strone>&pstg=<pominiete>
robots.txt Exim: 'User-agent: * / allow: /' (sprawdzone 2026-11-08).

Uwagi:
- Lista zwraca JEDNA oferte na hotel: najtansza w podanym zakresie dat (dla tych lotnisk i nocy).
  'total' = toursCount, czyli liczba hoteli, ktora podaje Exim.
- dd/rd to zakres calego pobytu (wylot >= dd i powrot <= rd), tak jak w wyszukiwarce Exim.
  Dla miesiaca bierzemy 1..ostatni dzien, wiec wyjazdy z konca miesiaca z powrotem w nastepnym
  miesiacu nie wchodza (tak samo pokazuje strona Exim dla takiego zakresu).
- Cena: tour.price.total = 'Calkowita cena' dla 2 doroslych z listy Exim (lot, transfer, hotel,
  wyzywienie; to, co Exim wlicza w cene katalogowa). ppp = total / doroslych, bo Exim czasem
  daje drugiej osobie inna cene (np. 1449 + 809), a pokazuje cene calkowita.
- Lista ma flage priceIsCurrent=false: to cena z wyszukiwarki, strona oferty liczy ja ponownie.
"""
import calendar,json,urllib.parse
from . import http

NAME='Exim Tours'
SITE='https://www.exim.pl'
API=SITE+'/api/searchapi/getsearchresult'
PER_PAGE=50
ADULTS=2
NIGHTS='|'.join(str(i) for i in range(1,17))   # opcje Exim: 1-6, 7-9, 10-16 nocy

# id regionow (dest) z /api/searchfilter/getfilter; kazdy kraj sprawdzony zapytaniem (toursCount>0, 2026-11-08)
COUNTRIES={
 'AE':'64087|64094|64089|64090|64091|64086|64092',
 'AL':'63258|63294|63443',
 'BG':'63486|63484|63483',
 'CY':'63541|63542|63540',
 'DO':'63865|63864',
 'EG':'64419|64420|64425|64423',
 'ES':'63226|63241|63242|63243|63455|63244|63213|63245|74459|74460|63284|74461|74463|74464|63349|63350|63354|74465',
 'FR':'63210|63268',
 'GR':'63219|63220|63281|63316|63319|63324|63333|63362|63424|63402|63431|63409|63472|63471',
 'HR':'63250|63289|63326|63249|63251',
 'IT':'63212|63215|63457|63255|63425|63296|63298|63329|63330|63376|63391|219502|63406|63410|63429|219503|63426|63444|63454|63456|63459|63229',
 'KE':'63725',
 'LK':'64077',
 'MA':'63707|63710',
 'ME':'63487',
 'MT':'63581|63580',
 'MU':'63738',
 'MX':'63982',
 'PT':'63208|63222|63348|63395|63419|63343',
 'TH':'64144|64146|64128|64140|64126|64127',
 'TN':'63252|63447',
 'TR':'64157|63448|63288',
 'TZ':'63763|63765',
}
# lotniska Exim (filtr 'to'); WAW = Chopin + Modlin + Radom
AIRPORTS={'BZG':'4401','GDN':'1149','KTW':'1862','KRK':'1825','LUZ':'4382','LCJ':'4378','POZ':'2854',
          'RZE':'3095','WAW':'3850|4380|4381','WRO':'3911'}
PL_ALL='|'.join(AIRPORTS.values())
BOARD={1:'Śniadania',2:'Śniadania i obiadokolacje',3:'Pełne wyżywienie',5:'All inclusive',6:'Bez wyżywienia'}

def _params(cc,ym,origin):
    y,m=map(int,ym.split('-'))
    return {'ac1':str(ADULTS),'d':COUNTRIES[cc],'dd':f'{y:04d}-{m:02d}-01',
            'rd':f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}','nn':NIGHTS,'tt':'1',
            'to':AIRPORTS[origin] if origin else PL_ALL,'sortby':'PriceTotal','sortorder':'0'}

def _qs(p): return urllib.parse.urlencode(p,safe='|')

def list_url(cc,ym,origin=None):
    return SITE+'/wyszukanie?'+_qs(_params(cc,ym,origin))

def _int(x):
    try: return int(round(float(x)))
    except (TypeError,ValueError): return None

def parse(text,ym=None):
    """JSON odpowiedzi getsearchresult -> lista ofert (filtr miesiaca wylotu, jesli ym)."""
    d=json.loads(text) if isinstance(text,(str,bytes)) else text
    out=[]
    for t in d.get('tours') or []:
        tr=t.get('tour') or {};h=t.get('hotel') or {}
        dt=tr.get('date') or {};dep=dt.get('from');ret=dt.get('to')
        if not dep or not t.get('detailUrl'): continue
        if ym and not dep.startswith(ym): continue
        pr=tr.get('price') or {};total=_int(pr.get('total'))
        if not total: continue
        room=(tr.get('rooms') or [{}])[0]
        nad=len(room.get('adults') or []) or ADULTS
        try: seg=tr['flight']['departure']['segments'][0]['airport']
        except (KeyError,IndexError,TypeError): seg={}
        bc=h.get('breadcrumbs') or {}
        place=', '.join(x for x in (bc.get('destination'),bc.get('area')) if x)
        ty=h.get('trustYou') or {}
        # TrustYou w Exim ma skale 0-5 (np. 3.7 'Przecietnie'); x2 daje skale 0-10
        rating=round(ty['score']*2,1) if ty.get('score') and ty.get('reviewsCount') else None
        st=h.get('starsCount')
        out.append({'op':'exim','name':h.get('name') or '','stars':(int(st) if st==int(st) else st) if st else None,
            'place':place,'dep':dep,'ret':ret,'nights':tr.get('nightsCount'),
            'board':BOARD.get(room.get('mealId'),room.get('meal') or ''),
            'from':seg.get('fromIATA') or seg.get('from') or '',
            'ppp':round(total/nad),'adults':nad,'total':total,'rating':rating,'kind':'wypoczynek',
            'url':SITE+t['detailUrl']})
    return out

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper()
    if origin: origin=origin.upper()
    if cc not in COUNTRIES or (origin and origin not in AIRPORTS):
        return {'offers':[],'total':0,'complete':True,'url':SITE}
    p=_params(cc,ym,origin);url=SITE+'/wyszukanie?'+_qs(p)
    offers=[];total=None;page=0;complete=False
    while page<limit_pages:
        q=dict(p,sc='residential',pitg=str(PER_PAGE),pstg=str(page*PER_PAGE))
        d=json.loads(http.get(API+'?'+_qs(q),headers={'Accept':'application/json'}))
        total=d.get('toursCount') or 0
        n=len(d.get('tours') or [])
        offers+=parse(d,ym);del d
        page+=1
        if n<PER_PAGE or page*PER_PAGE>=total: complete=True;break
    return {'offers':offers,'total':total,'complete':complete,'url':url}
