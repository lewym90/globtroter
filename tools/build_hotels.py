#!/usr/bin/env python3
"""Lista hoteli dla kazdego kierunku, zapisana w repozytorium. Zrodlo bywa niedostepne,
wiec trzymamy ostatnia dobra wersje, a ceny i tak pobieramy na zywo. Nigdy nie konczy sie bledem."""
import json,os,sys,time,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_AGE=25*86400;BUDGET=float(os.environ.get('BUDGET_S','1500'))
KEEP=('name','key','accommodation_type','url','review_summary','price_ranges','geo','image','merchandising_labels')
def page(ta,sort,lim=50):
    u=f'https://data.xotelo.com/api/list?location_key=g{ta}&limit={lim}&offset=0&sort={sort}'
    try:
        j=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Globtroter/1.0'}),timeout=25))
        return (j.get('result') or {}).get('list') or []
    except Exception as e: print(' ',str(e)[:60],flush=True);return []
def main():
    ds=json.load(open(ROOT+'/data/destinations.json',encoding='utf8'));t0=time.time();ok=bad=skip=0
    os.makedirs(ROOT+'/data/hotels',exist_ok=True)
    for d in ds:
        if not d.get('ta'): continue
        p=f"{ROOT}/data/hotels/{d['id']}.json"
        if os.path.exists(p):
            try:
                o=json.load(open(p,encoding='utf8'))
                if time.time()-o['t']<MAX_AGE and len(o['r'])>=20: skip+=1;continue
            except Exception: pass
        if time.time()-t0>BUDGET: break
        seen={}
        for s,lim in(('best_value',50),('popularity',50),('best_value',30),('popularity',40),('best_value',20)):
            for h in page(d['ta'],s,lim): seen.setdefault(h['key'],{k:h.get(k) for k in KEEP})
            if len(seen)>=30: break
            time.sleep(1)
        if len(seen)>=5:
            json.dump({'t':int(time.time()),'r':list(seen.values())},open(p,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
            ok+=1;print(d['name'],len(seen),flush=True)
        else: bad+=1
    print('zapisane',ok,'nieudane',bad,'aktualne',skip)
if __name__=='__main__':
    try: main()
    except Exception as e: print('blad',e)
    sys.exit(0)
