#!/usr/bin/env python3
"""Przewodnik w aplikacji: maly plik z atrakcjami dla kazdego miejsca (data/guide/<id>.json) i informacje o krajach (data/countries.json).
Telefon pobiera tylko plik ogladanego miejsca, a nie cala baze."""
import json,os,sys
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,R+'/server')
import countries
A=json.load(open(R+'/data/attractions.json',encoding='utf8'));D=json.load(open(R+'/data/destinations.json',encoding='utf8'))
os.makedirs(R+'/data/guide',exist_ok=True)
K=('n','lat','lon','t','img','web','h','d','de','src')
for d in D:
    L=sorted(A.get(d['id'],[]),key=lambda x:-x.get('l',0))
    out={'a':[{k:x[k] for k in K if x.get(k) not in (None,'')} for x in L]}
    s=json.dumps(out,ensure_ascii=False,separators=(',',':'))
    p=f"{R}/data/guide/{d['id']}.json"
    if not os.path.exists(p) or open(p,encoding='utf8').read()!=s: open(p,'w',encoding='utf8').write(s)
C={cc:countries.info(cc) for cc in sorted({d['cc'] for d in D})}
json.dump(C,open(R+'/data/countries.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
print(len(D),'miejsc',sum(len(A.get(d['id'],[])) for d in D),'atrakcji')
