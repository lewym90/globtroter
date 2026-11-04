#!/usr/bin/env python3
"""Dodatkowe atrakcje z OpenStreetMap dla miejsc, gdzie Wikidata daje ich malo. Tylko obiekty z nazwa, bez duplikatow."""
import json,os,re,sys,time,unicodedata,urllib.parse,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=ROOT+'/data/attractions.json';MIN=15
URLS=['https://overpass-api.de/api/interpreter','https://overpass.private.coffee/api/interpreter','https://overpass.kumi.systems/api/interpreter']
def ask(q):
    for u in URLS:
        try:
            r=urllib.request.Request(u,data=urllib.parse.urlencode({'data':q}).encode(),headers={'User-Agent':'Globtroter/1.0 (non-commercial)'})
            return json.load(urllib.request.urlopen(r,timeout=120))['elements']
        except Exception as e: print(' ',u[8:24],str(e)[:60],flush=True);time.sleep(4)
    return None
def kind(t):
    if t.get('natural')=='beach': return 'beach'
    v=t.get('tourism');h=t.get('historic')
    if v in('museum','gallery'): return 'museum'
    if v=='viewpoint' or t.get('natural')in('peak','cave_entrance','waterfall'): return 'nature'
    if v=='zoo' or v=='aquarium' or v=='theme_park': return 'zoo'
    if h in('castle','fort'): return 'castle'
    if h in('ruins','archaeological_site'): return 'ruins'
    if h: return 'monument'
    if t.get('amenity')=='place_of_worship': return 'church'
    if t.get('leisure') in('park','garden','nature_reserve'): return 'park'
    return 'sight'
def norm(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode())
def main():
    ds=json.load(open(ROOT+'/data/destinations.json',encoding='utf8'));A=json.load(open(P,encoding='utf8'));t0=time.time()
    for d in sorted(ds,key=lambda d:len(A.get(d['id'],[]))):
        L=A.setdefault(d['id'],[])
        if len(L)>=MIN or time.time()-t0>4500: continue
        la,lo=d['lat'],d['lon'];w=.13
        b=f'({la-w},{lo-w},{la+w},{lo+w})'
        r=ask(f'[out:json][timeout:90];(nwr["tourism"~"^(attraction|museum|gallery|viewpoint|zoo|aquarium)$"]["name"]{b};nwr["natural"="beach"]["name"]{b};nwr["historic"~"^(castle|fort|ruins|archaeological_site|monument)$"]["name"]{b};nwr["leisure"~"^(park|nature_reserve)$"]["name"]["wikidata"]{b};);out center tags 200;')
        if r is None: continue
        have={norm(x['n']) for x in L};n=0
        sc=lambda e:(('wikidata' in e['tags'])*2+('wikipedia' in e['tags'])*2+('website' in e['tags']))
        for e in sorted(r,key=sc,reverse=True):
            t=e.get('tags',{});nm=t.get('name:pl') or t.get('name');c=e.get('center') or e
            if not nm or norm(nm) in have or 'lat' not in c or len(L)>=30: continue
            have.add(norm(nm));L.append({'n':nm,'lat':round(c['lat'],5),'lon':round(c['lon'],5),'l':sc(e),'t':kind(t),'q':f"osm{e['type'][0]}{e['id']}",'img':None,'web':t.get('website'),'h':(t.get('opening_hours') or '')[:120] or None});n+=1
        print(d['name'],n,len(L),flush=True);time.sleep(3)
        json.dump(A,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
if __name__=='__main__': main()
