#!/usr/bin/env python3
"""Porownuje liczby z kazdego opisu z artykulem zrodlowym. Liczba bez pokrycia trafia do raportu, nic nie jest kasowane."""
import json,os,re,time,urllib.parse as U,urllib.request as Q
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def get(u):
    for i in range(4):
        try:return json.load(Q.urlopen(Q.Request(u,headers={'User-Agent':'Globtroter/1.0 (non-commercial; github.com/lewym90/globtroter)'}),timeout=30))
        except Exception:time.sleep(6*(i+1))
    return None
A=json.load(open(ROOT+'/data/attractions.json',encoding='utf8'));C={'opisy':0,'strona ok':0,'brak strony':0,'blad':0,'liczby':0,'zgodne':0,'inne zrodla':0};B=[];t0=time.time()
for city,L in A.items():
    for x in L:
        u=x.get('src')
        if not u or not x.get('d'):continue
        C['opisy']+=1
        if time.time()-t0>17000:continue
        h=U.urlsplit(u)
        if 'wikipedia.org' not in h.netloc:C['inne zrodla']+=1;continue
        j=get(f'https://{h.netloc}/w/api.php?action=query&format=json&redirects=1&prop=extracts&explaintext=1&titles='+U.quote(U.unquote(h.path.split('/wiki/',1)[-1])))
        time.sleep(.7)
        if not j:C['blad']+=1;continue
        p=list(j['query']['pages'].values())[0]
        if 'missing' in p:C['brak strony']+=1;B.append({'c':city,'n':x['n'],'u':u,'p':'brak strony'});continue
        C['strona ok']+=1
        s=re.sub(r'(?<=\d)[\s .,](?=\d{3}\b)','',p.get('extract',''))
        N=re.findall(r'\b\d{3,6}\b',re.sub(r'(?<=\d)[\s ](?=\d{3}\b)','',x['d']))
        M=[n for n in N if n not in s];C['liczby']+=len(N);C['zgodne']+=len(N)-len(M)
        if M:B.append({'c':city,'n':x['n'],'u':u,'p':M,'d':x['d']})
json.dump({'C':C,'B':B},open(ROOT+'/data/opisy_raport.json','w',encoding='utf8'),ensure_ascii=False,indent=0);print(C,len(B))
