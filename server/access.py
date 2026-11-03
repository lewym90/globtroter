"""Koszt i czas dojazdu z domu na lotnisko. Kazda wartosc szacunkowa ma znacznik 'est'."""
import math
import geo,net,store
# Parking dlugoterminowy, cena za 7 dni (zl). Zrodla: Interia (2026), Bankier (2023). Zawsze do nadpisania przez uzytkownika.
PARK={'WAW':310,'WMI':95,'RDO':110,'KRK':150,'KTW':200,'POZ':200,'WRO':200,'RZE':99,'GDN':90,'LCJ':150,'LUZ':120,'SZZ':120,'BZG':100,'SZY':90,'IEG':0}
PARK_SRC={'WAW':'Interia 2026','WMI':'Interia 2026','RDO':'Interia 2026','KRK':'Interia 2026','KTW':'Interia 2026','POZ':'Interia 2026','WRO':'Interia 2026','RZE':'Interia 2026'}
PARK_FOREIGN=350
TOLL={'A1':29.90/152,'A2':138/255,'A4':36/61}
PUBLIC_ZL_KM=0.24
def parking(iata,days,override=None):
    if override is not None: return round(override/7*max(days,3))
    p=PARK.get(iata,PARK_FOREIGN)
    return round(p/7*max(days,3)) if days<=7 else round(p+p*0.55/7*(days-7))
def nearby(lat,lon,radius=450,manual=None):
    """Lotniska z Polski plus zagraniczne w zasiegu. Kolejnosc: od najblizszego."""
    out=[]
    for a in geo.AIRPORTS.values():
        if a['cc'] in('BY','RU','UA'): continue
        d=geo.km(lat,lon,a['lat'],a['lon'])
        if manual:
            if a['iata'] in manual: out.append((d,a))
        elif (a['cc']=='PL' and d<=max(radius,700)) or (d<=radius and a['large']):
            out.append((d,a))
    out.sort(key=lambda x:x[0])
    return out
def _key(lat,lon): return f'{round(lat,2)},{round(lon,2)}'
def drive_table(lat,lon,codes):
    """Czasy i dystanse jazdy; przy awarii zrodla liczy z odleglosci i oznacza jako szacunek."""
    res={}
    coords=';'.join([f'{lon},{lat}']+[f"{geo.AIRPORTS[c]['lon']},{geo.AIRPORTS[c]['lat']}" for c in codes])
    try:
        t=net.fetch_json(f'https://router.project-osrm.org/table/v1/driving/{coords}?sources=0&annotations=duration,distance',ttl=30*86400,tries=2)
        for i,c in enumerate(codes):
            s=t['durations'][0][i+1];m=t['distances'][0][i+1]
            if s is not None and m is not None: res[c]={'km':round(m/1000),'min':round(s/60*1.08),'est':False}
    except Exception: pass
    for c in codes:
        if c not in res:
            a=geo.AIRPORTS[c];k=geo.km(lat,lon,a['lat'],a['lon'])*1.3
            res[c]={'km':round(k),'min':round(k/80*60),'est':True}
    return res
def tolls(lat,lon,c):
    """Oplaty autostradowe w jedna strone wyliczone z odcinkow platnych na trasie."""
    a=geo.AIRPORTS[c]
    k=f'toll:{_key(lat,lon)}:{c}'
    v,_=store.get(k)
    if v is not None: return v
    try:
        r=net.fetch_json(f"https://router.project-osrm.org/route/v1/driving/{lon},{lat};{a['lon']},{a['lat']}?steps=true&overview=false",cache=False,tries=2)
        z=0.0
        for s in r['routes'][0]['legs'][0]['steps']:
            if any('toll' in (i.get('classes') or []) for i in s.get('intersections',[])):
                ref=(s.get('ref') or '').split(';')[0].strip();z+=s['distance']/1000*TOLL.get(ref,0.45)
        z=round(z)
        store.put(k,z,30*86400)
        return z
    except Exception: return None
def cost(mode,iata,drive,days,pax,cfg):
    """Zwraca koszt dojazdu tam i z powrotem z rozbiciem na pozycje."""
    km=drive['km'];L=cfg.get('consumption',7.5);F=cfg.get('fuelPrice',5.99)
    fuel=lambda k:round(k*L/100*F)
    if mode=='public':
        v=round(max(25,km*PUBLIC_ZL_KM)*2*pax)
        return {'mode':mode,'total':v,'items':[{'label':'Bilety tam i z powrotem (szacunek)','pln':v,'est':True}],'est':True}
    t=cfg.get('tollOneWay');t=0 if t is None else t
    if mode=='dropoff':
        f=fuel(km*4);tt=t*4
        items=[{'label':'Paliwo: dwa kursy kierowcy','pln':f,'est':True}]
        if tt: items.append({'label':'Autostrady','pln':tt,'est':True})
        return {'mode':mode,'total':f+tt,'items':items,'est':True}
    f=fuel(km*2);p=parking(iata,days,cfg.get('parkingOverride'));tt=t*2
    items=[{'label':f'Paliwo {km*2} km','pln':f,'est':True},{'label':f'Parking {days} dni','pln':p,'est':True,'source':PARK_SRC.get(iata,'szacunek')}]
    if tt: items.append({'label':'Autostrady','pln':tt,'est':True})
    return {'mode':mode,'total':f+p+tt,'items':items,'est':True}
