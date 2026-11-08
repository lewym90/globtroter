"""Dertour Polska (www.dertour.pl, platforma MerlinX; opis mechanizmu w merlinx.py).

Lista: wakacje samolotem, /index/wakacje_samolotem/, sortowanie cena rosnaco, jedna oferta na hotel.
Cena: 'Cena za os.' i suma dla 2 doroslych z listy (to samo na stronie oferty). Dertour NIE wlicza TFG
(strona oferty: 'Turystyczny Fundusz Gwarancyjny nie jest wliczony w cene'; kwota nie jest podana).
robots.txt: brak regul dla User-agent * (sprawdzone 2026-11-08).
"""
from . import merlinx

NAME='Dertour'
SITE='https://www.dertour.pl'
BASE=SITE+'/index/wakacje_samolotem/'
KIND='wypoczynek'
# id krajow MerlinX z getDestinationsAjax; kazdy sprawdzony zapytaniem (oferty z polskich lotnisk, 12.2026-12.2027,
# 2026-11-08). Bez ofert wtedy: AT, CZ, EG, EE, FR, ID, IE, IS, CU, MY, DE, ZA, US, CH, HU, GB - pominiete.
COUNTRIES={'AL':'3269','BR':'47','BG':'3','HR':'5','CY':'6','ME':'8','DO':'10','AE':'372','GR':'14','ES':'15',
 'QA':'38441','KE':'19','MV':'24','MT':'26','MA':'27','MU':'28','MX':'29','OM':'4534','PT':'31','SC':'2925',
 'LK':'36','TH':'49','TZ':'2989','TR':'39','VN':'3030','IT':'44'}

def list_url(cc,ym,origin=None):
    return BASE+'?'+merlinx.qs(merlinx.params(COUNTRIES[cc],ym,origin))

def parse(text,ym=None,origin=None):
    return merlinx.parse(text,'dertour',BASE,ym,KIND,origin)

def search(cc,ym,origin=None,limit_pages=40):
    return merlinx.search('dertour',BASE,COUNTRIES,cc,ym,origin,limit_pages,kind=KIND)
