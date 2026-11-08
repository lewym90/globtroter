"""Kompas Tour (kompastour.pl): wczasy samolotem, glownie Turcja, Egipt, Tajlandia, Bulgaria, Czarnogora.

Zrodlo: lista ofert w HTML serwera (strona, ktora widzi uzytkownik), parametry po przecinkach:
  /l?,<Kraj>,<miasta wylotu ;>,<wyjazd po RRRR-MM-DD>,,,<powrot przed RRRR-MM-DD>,2,,,,samolot,,,,,,,,,<na strone>,<strona>,,,a;price
'a;price' = cena rosnaco (domyslne na stronie). Rozmiar strony: strona oferuje 9, serwer przyjmuje tez 50
(ok. 0,3 MB); bierzemy 50. Liczby ofert strona nie podaje, tylko numery stron.
Lista daje jedna oferte na hotel (najtanszy termin w zakresie); link ofr-...html?q=... prowadzi do tego terminu.
robots.txt: User-agent * -> Disallow tylko /tempHidden/ (sprawdzone 2026-11-08).

Uwagi:
- 'Wyjazd po'/'Powrot przed' = wylot >= 1. dnia i powrot <= ostatniego dnia miesiaca (wyjazd pod koniec miesiaca
  z powrotem w nastepnym nie wchodzi, jak w Exim).
- Cena: 'X zl/os.' z listy = 'X zl / os.' na stronie oferty (cena dla 2 doroslych w pokoju, za osobe).
  total = ppp * 2. Strona zastrzega, ze cena moze nie obejmowac doplat (zakladka 'Doplaty').
- Termin i miasto wylotu z atrybutu data-notes-entity-id ('id|wiek|TO|wyzywienie|transport|miasto|wylot|powrot').
"""
import calendar,datetime,html,re,urllib.parse
from . import http
from .merlinx import DEP,CITY

NAME='Kompas Tour'
SITE='https://kompastour.pl'
PER_PAGE=50
ADULTS=2
# nazwy krajow jak w wyszukiwarce; sprawdzone zapytaniem (oferty samolotem, 11.2026-12.2027, 2026-11-08).
# Bez ofert: Grecja, Hiszpania, Albania, Tunezja, Cypr, Chorwacja, Wlochy, Maroko, ZEA, Portugalia i inne egzotyczne.
COUNTRIES={'TR':'Turcja','EG':'Egipt','BG':'Bułgaria','ME':'Czarnogóra','TH':'Tajlandia'}
BOARD={'all inclusive':'All inclusive','ultra all inclusive':'Ultra all inclusive','śniadanie':'Śniadania','śniadania':'Śniadania',
       'śniadanie i obiadokolacja':'Śniadania i obiadokolacje','śniadania i obiadokolacje':'Śniadania i obiadokolacje',
       'pełne wyżywienie':'Pełne wyżywienie','bez wyżywienia':'Bez wyżywienia','wszystko w cenie':'All inclusive'}

def _path(cc,ym,origin,page=None):
    y,m=map(int,ym.split('-'))
    q=lambda s:urllib.parse.quote_plus(s,safe=';')
    f=[q(COUNTRIES[cc]),q(';'.join(DEP[origin])) if origin else '',f'{y:04d}-{m:02d}-01','','',
       f'{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}',str(ADULTS),'','','','samolot']+['']*8
    f+=[str(PER_PAGE),str(page)] if page else ['','']
    return 'l?,'+','.join(f+['','','a;price'])

def list_url(cc,ym,origin=None): return SITE+'/'+_path(cc,ym,origin)

def _int(s):
    s=re.sub(r'\D','',s or '');return int(s) if s else None

def parse(text,ym=None,origin=None):
    """HTML listy -> oferty (tylko polskie lotniska; filtr miesiaca wylotu i lotniska, jesli podane)."""
    out=[]
    for b in text.split("<a href='ofr-")[1:]:
        url=SITE+'/ofr-'+html.unescape(b.split("'",1)[0])
        n=re.search(r"data-notes-entity-id='([^']*)'",b)
        if not n: continue
        p=html.unescape(n.group(1)).split('|')
        if len(p)<8: continue
        city=p[5].strip();dep=p[6];ret=p[7];frm=CITY.get(city)
        if not frm or (origin and frm!=origin) or (ym and not dep.startswith(ym)): continue
        pr=re.search(r"<div class='price'>\s*([\d\s\xa0]+)zł",b)
        ppp=_int(pr.group(1)) if pr else None
        if not ppp: continue
        name=re.search(r"<h3>(.*?)</h3>",b,re.S);name=html.unescape(name.group(1)).strip() if name else html.unescape(re.search(r"title='([^']*)'",b).group(1))
        st=re.search(r"<span class='stars'[^>]*>(.*?)</span>",b,re.S)
        stars=None
        if st:
            s=html.unescape(st.group(1));full=s.count('★');stars=(full+0.5 if '½' in s or '⯪' in s else full) or None
        loc=re.search(r"<p class='local'[^>]*>(.*?)</p>",b,re.S)
        parts=[x.strip() for x in html.unescape(loc.group(1)).split('/')] if loc else []
        place=', '.join(parts[1:]) or (parts[0] if parts else '')
        meal=re.search(r"ico-ofr-meal\.svg\);'>(.*?)</p>",b,re.S);meal=html.unescape(meal.group(1)).strip() if meal else p[3]
        try: nights=(datetime.date.fromisoformat(ret)-datetime.date.fromisoformat(dep)).days
        except ValueError: nights=None
        out.append({'op':'kompastour','name':name,'stars':stars,'place':place,'dep':dep,'ret':ret,'nights':nights,
            'board':BOARD.get(meal.lower(),meal),'from':frm,'ppp':ppp,'adults':ADULTS,'total':ppp*ADULTS,'rating':None,
            'kind':'wypoczynek','url':url})
    return out

def _pages(text):
    return max([int(x) for x in re.findall(r"class='pagiv2_number[^']*'>(\d+)<",text)]+[1])

def search(cc,ym,origin=None,limit_pages=40):
    cc=cc.upper()
    if origin: origin=origin.upper()
    if cc not in COUNTRIES or (origin and origin not in DEP):
        return {'offers':[],'total':0,'complete':True,'url':SITE}
    offers=[];seen=set();page=1;last=1
    while page<=last and page<=limit_pages:
        t=http.get(SITE+'/'+_path(cc,ym,origin,page))
        if "offer-list-bp" not in t and re.search(r'(?i)captcha|cf-turnstile',t): raise http.Blocked('kompastour.pl: captcha')
        last=_pages(t)
        for o in parse(t,ym,origin):
            k=o['url'].split('.html')[0]+o['dep']+o['from']
            if k not in seen: seen.add(k);offers.append(o)
        del t;page+=1
    complete=page>last
    return {'offers':offers,'total':len(offers) if complete else None,'complete':complete,'url':list_url(cc,ym,origin)}
