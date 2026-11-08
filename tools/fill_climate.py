#!/usr/bin/env python3
"""Uzupelnia klimat tam, gdzie nie ma stacji z normami (np. Wyspy Zielonego Przyladka), i temperature morza.
Klimat: NASA POWER, srednie wieloletnie z reanalizy MERRA-2 (dzienne maksima i minima, opad). Morze: Open-Meteo Marine.
Nic nie nadpisuje: wypelnia tylko braki. Zrodlo zapisuje w polu station."""
import calendar,json,os,sys,time,urllib.request
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));P=R+'/data/destinations.json'
UA={'User-Agent':'Globtroter/1.0 (non-commercial travel planner)'}
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60) as r: return json.loads(r.read())
        except Exception as e:
            if i==3: raise
            time.sleep(5*(i+1))
D=json.load(open(P,encoding='utf8'));ch=0
for d in D:
    c=d.get('climate')
    if not c:
        j=get(f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=T2M_MAX,T2M_MIN,PRECTOTCORR&community=RE&longitude={d['lon']}&latitude={d['lat']}&format=JSON")['properties']['parameter']
        M=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
        tx=[round(j['T2M_MAX'][m],1) for m in M];tn=[round(j['T2M_MIN'][m],1) for m in M]
        rain=[round(j['PRECTOTCORR'][m]*calendar.monthrange(2023,i+1)[1],1) for i,m in enumerate(M)]
        if all(-60<x<60 for x in tx+tn):
            d['climate']=c={'tmin':tn,'tmax':tx,'rain':rain,'station':'NASA POWER (średnie wieloletnie)','period':2020,'km':0};ch+=1
            print('klimat',d['name'],tx)
    if c and 'beach' in d.get('tags',[]) and not c.get('sea'):
        try:
            r=get(f"https://marine-api.open-meteo.com/v1/marine?latitude={d['lat']}&longitude={d['lon']}&hourly=sea_surface_temperature&start_date=2025-01-01&end_date=2025-12-31&timezone=UTC")
            m=[[] for _ in range(12)]
            for t,v in zip(r['hourly']['time'],r['hourly']['sea_surface_temperature']):
                if v is not None: m[int(t[5:7])-1].append(v)
            if all(m): c['sea']=[round(sum(x)/len(x),1) for x in m];ch+=1;print('morze',d['name'],c['sea'])
            else: print('brak morza',d['name'],file=sys.stderr)
        except Exception as e: print('morze blad',d['name'],e,file=sys.stderr)
        time.sleep(1)
if ch: json.dump(D,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
print('zmian',ch)
