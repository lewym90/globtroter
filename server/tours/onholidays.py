"""OnHolidays (onholidays.pl): platforma Bluevendo, wspolny kod w tours/bvplatform.py.

Specyfika: szybka (ok. 2-3 s na zapytanie), mala oferta (kilkadziesiat hoteli na kraj i miesiac).
Identyfikatory krajow i miast wylotu sa inne niz w Best Reisen. Link do oferty bez &hid.
rateaverage jest puste, wiec rating = None.
"""
from . import bvplatform as bv

NAME='OnHolidays'
SITE='https://onholidays.pl'
OP='onholidays'
PAGES=5
# countryid z x-regionlist; kazdy kraj sprawdzony zapytaniem (total>0 dla miesiaca 2027, 2026-11-08).
# Slowenia (15) jest na liscie regionow, ale nie dala ani jednej oferty lotniczej (02, 04, 06, 09.2027) - pominieta.
COUNTRIES={'AL':'25','BG':'12','CY':'23','EG':'19','ES':'27','GR':'16','HR':'13','IT':'21','MA':'30','MT':'33','PT':'31'}
# nodeid z GET /api/departure-cities. WAW = Chopin + Modlin + Radom. Brak BZG, LCJ, SZZ, OSZ.
NODES={'WAW':['4','62','71'],'KTW':['5'],'KRK':['65'],'GDN':['27'],'WRO':['8'],'POZ':['6'],'RZE':['33'],'LUZ':['67']}
CFG={'OP':OP,'SITE':SITE,'COUNTRIES':COUNTRIES,'NODES':NODES,'SAME':{'WAW':{'WAW','WMI','RDO'}},
     'HID':False,'PER_PAGE':100,'PAGES':PAGES,'TIMEOUT':60,'RATE_SCALE':None}

def parse(text,ym=None,origin=None): return bv.parse(text,CFG,ym,origin)
def list_url(cc,ym,origin=None): return bv.list_url(CFG,cc,ym,origin)
def search(cc,ym,origin=None,limit_pages=PAGES): return bv.search(CFG,cc,ym,origin,limit_pages)
