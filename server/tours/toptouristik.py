"""TOP Touristik (toptouristik.pl, platforma MerlinX; opis mechanizmu w merlinx.py).

Lista: wczasy samolotem, /index/samolotem/, sortowanie cena rosnaco, jedna oferta na hotel.
Cena: 'Cena za os.' i suma dla 2 doroslych z listy; TOP wlicza TFG (ofr_TFGIncluded=1).
Strona ma mechanizm captcha (captchaAvailable=1). Przy captcha/blokadzie merlinx rzuca http.Blocked; nie obchodzimy.
W wynikach Modlin nazywa sie 'Modlin' (filtr dn 'Warszawa - Modlin' dziala).
robots.txt: brak regul dla User-agent * (sprawdzone 2026-11-08).
"""
from . import merlinx

NAME='TOP Touristik'
SITE='https://toptouristik.pl'
BASE=SITE+'/index/samolotem/'
KIND='wypoczynek'
# id krajow MerlinX z getDestinationsAjax; wszystkie 14 sprawdzone zapytaniem (oferty z polskich lotnisk, 2026-11-08)
COUNTRIES={'AL':'3269','BG':'3','HR':'5','CY':'6','ME':'8','EG':'11','GR':'14','ES':'15','MT':'26','MA':'27',
 'PT':'31','US':'3629','TR':'39','IT':'44'}

def list_url(cc,ym,origin=None):
    return BASE+'?'+merlinx.qs(merlinx.params(COUNTRIES[cc],ym,origin))

def parse(text,ym=None,origin=None):
    return merlinx.parse(text,'toptouristik',BASE,ym,KIND,origin)

def search(cc,ym,origin=None,limit_pages=40):
    return merlinx.search('toptouristik',BASE,COUNTRIES,cc,ym,origin,limit_pages,kind=KIND)
