#!/usr/bin/env python3
"""Restauracje z OpenStreetMap dla kazdego kierunku. Uruchamiane przez GitHub Actions.
Nigdy nie konczy sie bledem: czego nie uda sie pobrac dzis, pobierze nastepny przebieg."""
import json,os,sys,time,urllib.parse,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSTS=['https://overpass-api.de/api/interpreter','https://overpass.private.coffee/api/interpreter','https://overpass.kumi.systems/api/interpreter']
UA={'User-Agent':'Globtroter/1.0 (non-commercial travel planner; github.com/lewym90/globtroter)','Content-Type':'application/x-www-form-urlencoded'}
MAX_AGE=30*86400;BUDGET=float(os.environ.get('BUDGET_S','1500'))
def parse(raw):
    """Zamienia odpowiedz Overpass na krotkie rekordy, najpelniejsze wpisy najpierw."""
    out=[];seen=set()
    for e in raw.get('elements',[]):
        g=e.get('center') or e;t=e.get('tags',{});n=t.get('name')
        if not n or n in seen or 'lat' not in g or t.get('opening_hours')=='off' or 'disused:amenity' in t: continue
        seen.add(n)
        w=t.get('website') or t.get('contact:website')
        s=sum(1 for k in('website','contact:website','opening_hours','phone','contact:phone','outdoor_seating','wheelchair') if k in t)
        r={'n':n,'c':t.get('cuisine','').replace(';',', ').replace('_',' '),'lat':round(g['lat'],5),'lon':round(g['lon'],5),'s':s}
        if t.get('opening_hours'): r['h']=t['opening_hours']
        if w and w.startswith('http'): r['w']=w
        out.append(r)
    return sorted(out,key=lambda x:-x['s'])[:160]
def fetch(lat,lon):
    q=f'[out:json][timeout:25];nwr["amenity"="restaurant"]["name"](around:2800,{lat},{lon});out center tags 450;'
    body=urllib.parse.urlencode({'data':q}).encode()
    for h in HOSTS:
        try:
            with urllib.request.urlopen(urllib.request.Request(h,data=body,headers=UA),timeout=32) as r: return json.loads(r.read())
        except Exception as e: print(' ',h.split('/')[2],str(e)[:70],flush=True);time.sleep(4)
    return None
def main():
    ds=json.load(open(ROOT+'/data/destinations.json',encoding='utf8'));t0=time.time();ok=bad=skip=0
    os.makedirs(ROOT+'/data/food',exist_ok=True)
    for d in ds:
        p=f"{ROOT}/data/food/{d['id']}.json"
        if os.path.exists(p):
            try:
                if time.time()-json.load(open(p,encoding='utf8'))['t']<MAX_AGE: skip+=1;continue
            except Exception: pass
        if time.time()-t0>BUDGET: print('koniec czasu, reszta w nastepnym przebiegu');break
        raw=fetch(d['lat'],d['lon'])
        if raw is None: bad+=1;continue
        L=parse(raw)
        json.dump({'t':int(time.time()),'r':L},open(p,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
        ok+=1;print(d['name'],len(L),flush=True);time.sleep(5)
    print('zapisane',ok,'nieudane',bad,'aktualne',skip)
if __name__=='__main__':
    try: main()
    except Exception as e: print('blad',e)
    sys.exit(0)
