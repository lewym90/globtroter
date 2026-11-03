#!/usr/bin/env python3
"""Krok 5: usuwa z atrakcji dziela sztuki stojace w muzeach i kosciolach (to nie jest osobny punkt zwiedzania)."""
import json,os,sys,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_data import sparql,ROOT
P=ROOT+'/data/attractions.json'
A=json.load(open(P,encoding='utf8'))
ids=sorted({x['q'] for L in A.values() for x in L})
bad=set()
for i in range(0,len(ids),150):
    v=' '.join('wd:'+q for q in ids[i:i+150])
    q='SELECT DISTINCT ?i WHERE { VALUES ?i {%s} ?i wdt:P31 ?t. VALUES ?t {wd:Q860861 wd:Q179700 wd:Q3305213 wd:Q838948} {?i wdt:P276 ?x} UNION {?i wdt:P195 ?x} }'%v
    bad|={r['i']['value'].rsplit('/',1)[1] for r in sparql(q)};time.sleep(1)
n=0
for k in A:
    b=len(A[k]);A[k]=[x for x in A[k] if x['q'] not in bad];n+=b-len(A[k])
json.dump(A,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
print('usuniete',n,[x['n'] for x in A['rzym'][:14]])
