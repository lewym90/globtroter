"""Regent (regent.pl) - city breaki samolotem.

Zrodlo: HTML renderowany na serwerze. /robots.txt zwraca 404 (brak ograniczen, sprawdzone 2026-11-08).
  1. lista wycieczek: /webit.php?destinationto=REGENT|<KRAJ>|&wylot=DD.MM.RRRR&powrot=DD.MM.RRRR
     - wiersz = wycieczka; linki 'Rezerwuj z wylotem z X' prowadza do osobnej strony dla kazdego miasta wylotu
     - lista nie ma dat ani cen terminow ('cena od' nie jest powiazana z data)
  2. strona wycieczki dla miasta wylotu: tabela 'Terminy - Wylot z: X' z datami i cena za osobe
  3. link terminu: /webit.php?onepage=20&adults=2&...&md=<hash> (krok rezerwacji dla tego terminu)
Cena z tabeli to cena za osobe przy 2 doroslych z oplatami (lotniskowa i fundusze); strona rezerwacji
dla 2 osob pokazuje 'Razem' = 2 x ta cena (sprawdzone na probce), wiec total = 2 x ppp.
Wiele zapytan: 1 lista + 1 strona na (wycieczka, miasto wylotu); limit_pages ogranicza strony wycieczek.
"""
import calendar,datetime as dt,html,re,urllib.parse
from . import http

NAME='Regent'
SITE='https://www.regent.pl'
ADULTS=2
# kraje z listy kierunkow Regent; kazdy sprawdzony zapytaniem z wynikami (2026-11-08)
COUNTRIES={'ES':'HISZPANIA','FR':'FRANCJA','GB':'WIELKA BRYTANIA','GR':'GRECJA','IT':'WLOCHY'}
# miasto wylotu z listy (tekst linku) -> IATA
CITY_IATA={'Warszawa':'WAW','Modlin':'WMI','Radom':'RDO','Katowice':'KTW','Kraków':'KRK','Gdańsk':'GDN',
 'Wrocław':'WRO','Poznań':'POZ','Rzeszów':'RZE','Lublin':'LUZ','Bydgoszcz':'BZG','Łódź':'LCJ',
 'Szczecin':'SZZ','Szczytno':'OSZ','Szymany':'OSZ','Olsztyn':'OSZ'}
GROUP={'WAW':{'WAW','WMI','RDO'}}
BOARD={'BB':'Śniadania','HB':'Śniadania i obiadokolacje','FB':'Pełne wyżywienie','AI':'All inclusive',
       'RO':'Bez wyżywienia','OV':'Bez wyżywienia'}

def _d(x): return x.strftime('%d.%m.%Y')

def list_url(cc,ym):
    y,m=map(int,ym.split('-'))
    a=dt.date(y,m,1);b=dt.date(y,m,calendar.monthrange(y,m)[1])+dt.timedelta(days=14)  # powrot moze wypasc w nastepnym miesiacu
    return SITE+'/webit.php?destinationto='+urllib.parse.quote(f'REGENT|{COUNTRIES[cc]}|',safe='|')+f'&wylot={_d(a)}&powrot={_d(b)}'

def _abs(u):
    u=html.unescape(u).strip()
    if u.startswith('//'): u='https:'+u
    elif u.startswith('/'): u=SITE+u
    return urllib.parse.quote(u,safe=':/?&=,%|.-_~')

def _txt(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def parse_list(text):
    """HTML listy -> [{'name','place','country','board','deps':[(miasto,IATA,url)]}]"""
    out=[]
    for tr in re.split(r'<tr class="off_tr_bgd">',text)[1:]:
        n=re.search(r'class="off_nazwa">\s*<a href="[^"]+">(.*?)</a>',tr,re.S)
        if not n: continue
        pl=re.search(r'class="off_panstwo">(.*?)</div>',tr,re.S);co=re.search(r'class="off_region">(.*?)</div>',tr,re.S)
        w=re.search(r'class="off_wyz">(.*?)</span>',tr,re.S)
        deps=[]
        for u,c in re.findall(r'class="linkhre"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',tr,re.S):
            c=_txt(c);deps.append((c,CITY_IATA.get(c,c),_abs(u)))
        out.append({'name':_txt(n.group(1)),'place':_txt(pl.group(1)) if pl else '','country':_txt(co.group(1)) if co else '',
                    'board':_txt(w.group(1)) if w else '','deps':deps})
    return out

def parse(text,name='',place='',board='',frm='',ym=None):
    """HTML strony wycieczki (jedno miasto wylotu) -> oferty, po jednej na termin."""
    i=text.find('id="terminy-i-ceny"')
    if i<0: return []
    s=text[i:text.find('</table>',i)]
    if not frm:
        m=re.search(r'Wylot z:\s*([^<]+)',s);frm=m.group(1).strip() if m else ''
    out=[]
    for r in s.split('<tr class="off_tr_bgd">')[1:]:
        d=re.findall(r'class="off_daty">(\d\d)\.(\d\d)\.(\d{4})</span>',r)
        c=re.search(r'class="off_cena">(.*?)</div>\s*</td>',r,re.S)
        u=re.search(r'href="([^"]*webit\.php\?onepage=[^"]+)"',r)
        if len(d)<2 or not c or not u: continue
        dep=dt.date(int(d[0][2]),int(d[0][1]),int(d[0][0]));ret=dt.date(int(d[1][2]),int(d[1][1]),int(d[1][0]))
        if ym and dep.strftime('%Y-%m')!=ym: continue
        t=re.sub(r'<strike>.*?</strike>','',c.group(1),flags=re.S|re.I)
        t=re.sub(r'<div[^>]*div-omnibus.*?</div>','',t,flags=re.S)   # 'najnizsza cena z 30 dni'
        p=re.search(r'(\d[\d ]*)\s*PLN',_txt(t))
        if not p: continue
        ppp=int(p.group(1).replace(' ',''))
        t0=re.search(r'class="off_termin" title="([^"]*)"',r)
        out.append({'op':'regent','name':name or (html.unescape(t0.group(1)) if t0 else ''),'stars':None,'place':place,
            'dep':dep.isoformat(),'ret':ret.isoformat(),'nights':(ret-dep).days,'board':BOARD.get(board.upper(),board),
            'from':frm,'ppp':ppp,'adults':ADULTS,'total':ppp*ADULTS,'rating':None,'kind':'city break',
            'url':html.unescape(u.group(1))})
    return out

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper()
    if origin: origin=origin.upper()
    url=list_url(cc,ym) if cc in COUNTRIES else SITE
    if cc not in COUNTRIES: return {'offers':[],'total':0,'complete':True,'url':url}
    want=GROUP.get(origin,{origin}) if origin else None
    trips=parse_list(http.get(url))
    todo=[(t,c,i,u) for t in trips for c,i,u in t['deps'] if (want is None and len(i)==3) or (want and i in want)]
    offers=[]
    for t,c,i,u in todo[:limit_pages]:
        offers+=parse(http.get(u),t['name'],t['place'],t['board'],i,ym)
    offers.sort(key=lambda o:o['ppp'])
    return {'offers':offers,'total':None,'complete':len(todo)<=limit_pages,'url':url}
