"""Plus Wakacje (pluswakacje.pl) - multiagent (MerlinX), oferty wielu organizatorow.

Zrodlo: lista wynikow renderowana na serwerze (bez JS):
  /l?,<kraj>,<miasta wylotu ;>,<wylot od>,<wylot do>,,,2,,,,samolot,,,,,,,,,<na strone>,<strona>,,,a;price,a;price
Kolejnosc pol ustalona przez wlasny endpoint strony 'bp/search/searchParamsToUrl'.
robots.txt (User-agent *): Disallow tylko /tempHidden/ (sprawdzone 2026-11-08).

Uwagi:
- Sortowanie po cenie rosnaco; jeden wiersz na hotel (najtanszy termin w zakresie).
- Lista podaje cene za osobe przy 2 doroslych ('zl/os.'); cena 'Razem' liczy sie dopiero na
  stronie oferty (zapytanie do systemu organizatora). total = ppp * 2; na sprawdzonych ofertach
  'Razem' z checkAvailability rownalo sie 2 x cena za osobe (patrz raport weryfikacji).
- Lista nie podaje liczby wynikow, wiec 'total' = None.
- Wyszukiwarka zawiera wyloty z Berlina i Pragi; bez 'origin' bierzemy tylko lotniska polskie.
"""
import calendar,datetime as dt,html,re,urllib.parse
from . import http

NAME='Plus Wakacje'
SITE='https://pluswakacje.pl'
PER_PAGE=100
ADULTS=2

# nazwy krajow z listy 'countryRegion' wyszukiwarki; kazdy sprawdzony zapytaniem z wynikami (2026-11-08)
COUNTRIES={'AE':'Emiraty Arabskie','AL':'Albania','BG':'Bułgaria','CV':'Wyspy Zielonego Przylądka','CY':'Cypr',
 'DO':'Dominikana','EG':'Egipt','ES':'Hiszpania','GR':'Grecja','HR':'Chorwacja','IT':'Włochy','MA':'Maroko',
 'ME':'Czarnogóra','MT':'Malta','MX':'Meksyk','PT':'Portugalia','TH':'Tajlandia','TN':'Tunezja','TR':'Turcja'}
# miasta wylotu (grupa 'samolot' w wyszukiwarce) -> IATA
CITY_IATA={'Warszawa':'WAW','Warszawa - Modlin':'WMI','Warszawa - Radom':'RDO','Katowice':'KTW','Kraków':'KRK',
 'Gdańsk':'GDN','Wrocław':'WRO','Poznań':'POZ','Rzeszów':'RZE','Lublin':'LUZ','Bydgoszcz':'BZG','Łódź':'LCJ',
 'Szczecin':'SZZ','Zielona Góra':'IEG','Berlin':'BER','Praga':'PRG'}
ORIGIN={'WAW':['Warszawa','Warszawa - Modlin','Warszawa - Radom'],'KTW':['Katowice'],'KRK':['Kraków'],
 'GDN':['Gdańsk'],'WRO':['Wrocław'],'POZ':['Poznań'],'RZE':['Rzeszów'],'LUZ':['Lublin'],'BZG':['Bydgoszcz'],
 'LCJ':['Łódź'],'SZZ':['Szczecin'],'OSZ':[]}   # OSZ: brak wylotow z Szyman w tej wyszukiwarce
PL_ALL=[c for c in CITY_IATA if c not in('Berlin','Praga')]
BOARD={'U':'Bez wyżywienia','B':'Śniadania','H':'Śniadania i obiadokolacje','F':'Pełne wyżywienie',
       'A':'All inclusive'}

def _enc(s): return urllib.parse.quote(s.replace(' ','+'),safe='+-;')

def list_url(cc,ym,cities,page=1,per=PER_PAGE):
    y,m=map(int,ym.split('-'))
    d1=f'{y:04d}-{m:02d}-01';d2=f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}'
    return (f"{SITE}/l?,{_enc(COUNTRIES[cc])},{_enc(';'.join(cities))},{d1},{d2},,,{ADULTS},,,,samolot"
            f",,,,,,,,,{per},{page},,,a;price,a;price")

def _txt(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def last_page(text):
    p=[int(x) for x in re.findall(r",\d+,(\d+),,,[ad];[a-zA-Z]+",text)]
    return max(p) if p else 1

def parse(text):
    """HTML listy wynikow -> lista ofert (bez filtrowania)."""
    out=[]
    for it in text.split("class='item offersList_item'")[1:]:
        it=it.split("</a>")[0]
        nid=re.search(r"data-notes-entity-id='([^']*)'",it)
        if not nid: continue
        f=html.unescape(nid.group(1)).split('|')   # id|wiek|kod|wyzywienie (X)|transport|miasto|wylot|powrot
        if len(f)<8: continue
        dep,ret,city=f[6],f[7],f[5].strip()
        try: nights=(dt.date.fromisoformat(ret)-dt.date.fromisoformat(dep)).days
        except ValueError: continue
        pr=re.search(r"<div class='price'>\s*([\d\s]+)\s*zł",it)
        if not pr: continue
        ppp=int(re.sub(r'\D','',pr.group(1)))
        name=re.search(r"<h3>(.*?)</h3>",it,re.S);loc=re.search(r"<p class='local'[^>]*>(.*?)</p>",it,re.S)
        st=re.search(r"<span class='stars'[^>]*>(.*?)</span>",it,re.S)
        stars=html.unescape(st.group(1)).count('★')+0.5*html.unescape(st.group(1)).count('½') if st else 0
        loc=[x.strip() for x in _txt(loc.group(1)).split('/')] if loc else []
        bm=re.search(r'\(([A-Z]+)\)\s*$',f[3].strip())
        meal=re.search(r"ico-ofr-meal\.svg\);'>(.*?)</p>",it,re.S)
        board=BOARD.get(bm.group(1)) if bm else None
        if not board: board=(_txt(meal.group(1)) if meal else '') or re.sub(r'\s*\([A-Z]+\)\s*$','',f[3]).strip()
        board=board.strip('() ')
        board=board[:1].upper()+board[1:]
        out.append({'op':'pluswakacje','name':_txt(name.group(1)) if name else '','stars':(int(stars) if stars==int(stars) else stars) or None,
            'place':', '.join(loc[1:]),'dep':dep,'ret':ret,'nights':nights,'board':board,
            'from':CITY_IATA.get(city,city),'ppp':ppp,'adults':ADULTS,'total':ppp*ADULTS,'rating':None,
            'kind':'objazd' if any('Objazd' in x for x in loc) else 'wypoczynek','url':None,'_id':f[0]})
    # linki: kazdy element listy to <a href='ofr-...' class='item offersList_item'>
    links=re.findall(r"<a href='(ofr-[^']+)'[^>]*class='item offersList_item'",text)
    if len(links)==len(out):
        for o,l in zip(out,links): o['url']=SITE+'/'+html.unescape(l)
    for o in out: o.pop('_id')
    return [o for o in out if o['url']]

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper()
    if origin: origin=origin.upper()
    cities=ORIGIN.get(origin,[]) if origin else PL_ALL
    if cc not in COUNTRIES or not cities:
        return {'offers':[],'total':0,'complete':True,'url':SITE}
    want={CITY_IATA[c] for c in cities}
    offers=[];seen=set();page=1;last=1;complete=False
    while page<=min(limit_pages,last):
        t=http.get(list_url(cc,ym,cities,page))
        last=max(last,last_page(t))
        for o in parse(t):
            k=o['url'].split('?')[0],o['dep'],o['ret'],o['from'],o['ppp']
            if k in seen or not o['dep'].startswith(ym) or o['from'] not in want: continue
            seen.add(k);offers.append(o)
        del t
        if page>=last: complete=True
        page+=1
    return {'offers':offers,'total':None,'complete':complete,'url':list_url(cc,ym,cities,1,9)}
