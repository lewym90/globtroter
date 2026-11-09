#!/usr/bin/env python3
"""Zdjecia miejsc: usuwa pliki, ktorych nie ma juz w Wikimedia Commons, a miejscom z mala liczba zdjec
dobiera zdjecia z Commons, w ktorych tytule jest nazwa miejsca. Uruchamiane w GitHub Actions."""
import json,os,re,time,urllib.parse as U,urllib.request as Q
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));P=R+'/data/photos.json'
UA={'User-Agent':'Globtroter/1.0 (non-commercial travel planner; https://github.com/lewym90/globtroter)'}
API='https://commons.wikimedia.org/w/api.php?'
def get(q):
    for i in range(6):
        try:
            with Q.urlopen(Q.Request(API+U.urlencode({**q,'format':'json','formatversion':2}),headers=UA),timeout=60) as r: return json.load(r)
        except Exception as e: time.sleep(5*(i+1))
    raise IOError('commons')
PH=json.load(open(P,encoding='utf8'));D=json.load(open(R+'/data/destinations.json',encoding='utf8'))
# 1. czy pliki istnieja
names=sorted({x['f'] for L in PH.values() for x in L});gone=set()
for i in range(0,len(names),50):
    j=get({'action':'query','titles':'|'.join('File:'+n for n in names[i:i+50])})
    norm={x['to']:x['from'] for x in j['query'].get('normalized',[])}
    for p in j['query']['pages']:
        if p.get('missing') and not p.get('known'): gone.add(norm.get(p['title'],p['title'])[5:])
    time.sleep(.5)
for k in PH: PH[k]=[x for x in PH[k] if x['f'] not in gone]
print('usuniete',len(gone),sorted(gone)[:20])
# 2. dobor dla miejsc z mala liczba zdjec
AMB={'side':['Antalya','Turkey','Manavgat'],'burgas':['Bulgaria'],'sal':['Cape Verde'],'boa-vista':['Cape Verde']}  # nazwy wieloznaczne: szukamy z dopiskiem
BAD=re.compile(r'hotel|resort|aéroport|airport|autoroute|summit|president|minister|meets|conference|map|karte|carte|logo|flag|coat|wappen|plan|diagram|location|locator|\.svg|\.png|\.tif|stamp|sign|poster|panorama-small',re.I)
for d in D:
    have=PH.get(d['id'],[])
    if len(have)>=5: continue
    seen={x['f'] for x in have};add=[]
    base=(d.get('en') or d['name']).split(' (')[0]
    Q2=[base+' '+X for X in AMB.get(d['id'],[])] if d['id'] in AMB else [d.get('en') or d['name'],d['name'].split(' (')[0]]
    for nm in dict.fromkeys(Q2):
        j=get({'action':'query','generator':'search','gsrnamespace':6,'gsrlimit':40,'gsrsearch':f'intitle:"{nm}" filetype:bitmap','prop':'imageinfo','iiprop':'size|mime'})
        for p in sorted(j.get('query',{}).get('pages',[]),key=lambda p:p.get('index',0)):
            f=p['title'][5:];ii=(p.get('imageinfo') or [{}])[0]
            if f in seen or BAD.search(f) or ii.get('mime')!='image/jpeg' or ii.get('width',0)<1200 or ii.get('width',0)<ii.get('height',0): continue
            seen.add(f);add.append({'f':f,'n':d['name']})
            if len(have)+len(add)>=8: break
        if len(have)+len(add)>=8: break
        time.sleep(.5)
    if add: PH[d['id']]=have+add;print('dodane',d['id'],len(add),[a['f'] for a in add][:3])
json.dump(PH,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
