#!/usr/bin/env python3
"""Dolacza wynik automatu do najnowszej bazy atrakcji. Plik to jedna linia, wiec git nie umie go scalic,
a kilka automatow pracuje rownolegle. Tylko dodajemy i uzupelniamy, nic nie kasujemy."""
import json,re,sys,unicodedata
def norm(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',str(s).lower()).encode('ascii','ignore').decode())
def merge(base,new):
    n=0
    for city,L in new.items():
        B=base.setdefault(city,[]);q={x.get('q'):x for x in B};nm={norm(x['n']):x for x in B}
        for x in L:
            o=q.get(x.get('q')) or nm.get(norm(x['n']))
            if o is None:
                B.append(x);q[x.get('q')]=x;nm[norm(x['n'])]=x;n+=1
            else:
                for k,v in x.items():
                    if v and not o.get(k): o[k]=v
    return n
if __name__=='__main__':
    base=json.load(open(sys.argv[1],encoding='utf8'));new=json.load(open(sys.argv[2],encoding='utf8'))
    print('nowych',merge(base,new))
    json.dump(base,open(sys.argv[1],'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
