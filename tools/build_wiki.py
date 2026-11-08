#!/usr/bin/env python3
"""Krotkie opisy atrakcji z polskiej Wikipedii. Atrakcje bez polskiego artykulu zostaja bez opisu, niczego nie zmyslamy."""
import json,os,re,sys,time,urllib.parse,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=ROOT+'/data/attractions.json'
ONLY=set(filter(None,os.environ.get('ONLY','').split(',')))  # np. ONLY=hurghada,side: tylko te kierunki
def get(u):
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Globtroter/1.0 (non-commercial; github.com/lewym90/globtroter)'}),timeout=30))
        except Exception as e: print(str(e)[:70],flush=True);time.sleep(5*(i+1))
    return {}
def main():
    A=json.load(open(P,encoding='utf8'));items=[x for k,v in A.items() if not ONLY or k in ONLY for x in v if 'd' not in x and str(x['q']).startswith('Q')]
    t0=time.time();titles={}
    qs=sorted({x['q'] for x in items})
    for i in range(0,len(qs),50):
        j=get('https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=sitelinks&sitefilter=plwiki&ids='+'|'.join(qs[i:i+50]))
        for q,e in (j.get('entities') or {}).items():
            t=((e.get('sitelinks') or {}).get('plwiki') or {}).get('title')
            if t: titles[q]=t
        time.sleep(.3)
    print('tytuly',len(titles),flush=True)
    ts=sorted(set(titles.values()));txt={}
    for i in range(0,len(ts),20):
        if time.time()-t0>1500: break
        j=get('https://pl.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts&exintro=1&explaintext=1&exsentences=2&exlimit=20&titles='+urllib.parse.quote('|'.join(ts[i:i+20])))
        q=j.get('query') or {}
        back={n['to']:n['from'] for n in q.get('normalized',[])+q.get('redirects',[])}
        for p in (q.get('pages') or {}).values():
            e=re.sub(r'\s+',' ',p.get('extract') or '').strip()
            if len(e)>=40:
                k=p['title'];txt[back.get(k,k)]=e[:320]
        time.sleep(.3)
    n=0
    for x in items:
        t=titles.get(x['q'])
        if t in txt: x['d']=txt[t];n+=1
    json.dump(A,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
    print('opisy',n,'z',len(items))
if __name__=='__main__':
    main()
