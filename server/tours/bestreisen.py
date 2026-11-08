"""Best Reisen (bestreisengroup.pl): platforma Bluevendo, wspolny kod w tours/bvplatform.py.

Specyfika:
- Wyszukiwarka jest wolna: zapytanie z jednym miastem wylotu 13-45 s, bez filtra miasta (wszystkie
  polskie lotniska) ok. 50 s na strone. Dlatego czytamy najwyzej PAGES stron po 100 ofert, od najtanszych
  (ordername=customerprice ASC), i dajemy dlugi limit czasu na zapytanie.
- Duzo krotkich (3-5 nocy) pakietow z liniami niskokosztowymi; ceny dynamiczne (potrafia sie zmienic
  miedzy wyszukaniem a otwarciem oferty o kilkadziesiat zl).
- rateaverage jest zawsze puste, wiec rating = None.
- APPROX = True: ceny na liscie sa dynamiczne (pakiety z liniami niskokosztowymi) i bywa, ze strona oferty
  liczy inna kwote niz lista z tej samej chwili (08.11.2026: Maritime Apartments lista 1374 zl/os.,
  strona 1564 zl/os.; 5 innych ofert zgodnych co do zlotowki). Czasem strona oferty pokazuje 'Wystapil blad'
  takze dla linku, ktory generuje sama strona wynikow.
"""
from . import bvplatform as bv

NAME='Best Reisen'
SITE='https://bestreisengroup.pl'
OP='bestreisen'
PAGES=3
APPROX=True
# countryid z x-regionlist; kazdy kraj sprawdzony zapytaniem (total>0 dla miesiaca 2027, wylot z Polski, 2026-11-08).
# Pominiete: Barbados (141) i Singapur (91) - dzialaja, ale aplikacja nie ma dla nich nazwy kraju.
COUNTRIES={'AE':'18','AL':'211','BG':'23','CV':'117','CY':'107','DO':'85','EG':'12','ES':'37','GR':'73','HR':'94',
    'ID':'29','IT':'79','JM':'132','LK':'15','MA':'35','ME':'93','MT':'86','MU':'19','MV':'16','MX':'24','OM':'74',
    'PT':'36','QA':'169','SC':'17','TH':'20','TN':'13','TR':'22','TZ':'21','US':'83'}
# nodeid z GET /api/departure-cities (kod IATA w tej samej liscie). WAW = Chopin + Modlin + Radom. Brak OSZ.
NODES={'WAW':['13','120','243'],'KTW':['14'],'KRK':['17'],'GDN':['18'],'WRO':['16'],'POZ':['15'],'RZE':['168'],
    'LUZ':['123'],'BZG':['167'],'LCJ':['36'],'SZZ':['122']}
CFG={'OP':OP,'SITE':SITE,'COUNTRIES':COUNTRIES,'NODES':NODES,'SAME':{'WAW':{'WAW','WMI','RDO'}},
     'HID':True,'PER_PAGE':100,'PAGES':PAGES,'TIMEOUT':120,'RATE_SCALE':None}

def parse(text,ym=None,origin=None): return bv.parse(text,CFG,ym,origin)
def list_url(cc,ym,origin=None): return bv.list_url(CFG,cc,ym,origin)
def search(cc,ym,origin=None,limit_pages=PAGES): return bv.search(CFG,cc,ym,origin,limit_pages)
