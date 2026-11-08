"""Matimpex (www.matimpex.pl, city breaki samolotem; platforma MerlinX, opis mechanizmu w merlinx.py).

Lista: /index/city_breaki/ z oft=F (jak na stronie), sortowanie cena rosnaco, jedna oferta na wycieczke
(najtanszy termin w miesiacu). Oferta mala (kilkanascie wycieczek 4-dniowych). 'name' to nazwa wycieczki
(np. 'City Break w Rzymie 4 dni'); 'stars' to kategoria hotelu z MerlinX.
Cena: za osobe i za 2 doroslych z listy (na stronie oferty og:price i data-person-price).
robots.txt: brak regul dla User-agent * (sprawdzone 2026-11-08).
"""
from . import merlinx

NAME='Matimpex'
SITE='https://www.matimpex.pl'
BASE=SITE+'/index/city_breaki/'
KIND='city break'
EXTRA=[('oft','F')]
# id krajow MerlinX z getDestinationsAjax; wszystkie 8 sprawdzone zapytaniem (oferty z polskich lotnisk, 2026-11-08)
COUNTRIES={'FR':'13','GR':'14','ES':'15','MT':'26','PT':'31','HU':'41','GB':'43','IT':'44'}

def list_url(cc,ym,origin=None):
    return BASE+'?'+merlinx.qs(merlinx.params(COUNTRIES[cc],ym,origin,EXTRA))

def parse(text,ym=None,origin=None):
    return merlinx.parse(text,'matimpex',BASE,ym,KIND,origin)

def search(cc,ym,origin=None,limit_pages=40):
    return merlinx.search('matimpex',BASE,COUNTRIES,cc,ym,origin,limit_pages,EXTRA,KIND)
