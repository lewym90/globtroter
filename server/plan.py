"""Kompendium wyjazdu: od wyjscia z domu do powrotu. Kazda godzina jest wyliczona z danych,
kazda pozycja ma poziom pewnosci: fact (rezerwacja, rozklad), est (szacunek), check (sprawdz)."""
import datetime as dt,math
from urllib.parse import quote,urlencode
import access,countries,geo,net,search
ATTR=geo.load('attractions.json',{})
DUR={'museum':120,'church':40,'palace':90,'castle':90,'monument':25,'square':25,'park':60,'sight':45,'ruins':90,'bridge':20,'beach':150,'zoo':150,'street':40,'nature':120,'theatre':30,'food':60}
LATE={'museum','ruins','palace','castle','zoo'}
LABEL={'museum':'Muzeum','church':'Świątynia','palace':'Pałac','castle':'Zamek','monument':'Pomnik','square':'Plac','park':'Park','sight':'Zabytek','ruins':'Ruiny','bridge':'Most','beach':'Plaża','zoo':'Zoo','street':'Ulica','nature':'Przyroda','theatre':'Teatr','food':'Targ'}
def t(iso): return dt.datetime.fromisoformat(iso)
def hm(d): return d.strftime('%H:%M')
def span(m):
    h,n=divmod(int(m),60)
    return (f'{h} h ' if h else '')+(f'{n} min' if n or not h else '')
def przes(n): return 'bez przesiadek' if n==0 else ('1 przesiadka' if n==1 else f'{n} przesiadki' if n<5 else f'{n} przesiadek')
def add(d,m): return d+dt.timedelta(minutes=m)
def gmaps(a,b,mode='transit'):
    return 'https://www.google.com/maps/dir/?'+urlencode({'api':1,'origin':f'{a[0]},{a[1]}','destination':f'{b[0]},{b[1]}','travelmode':mode})
def place(n,lat,lon): return 'https://www.google.com/maps/search/?'+urlencode({'api':1,'query':f'{n} {lat},{lon}'})
def transit(a,b,when):
    """Transitous. Rozklady dzialaja dla najblizszych tygodni, wiec dalszy termin liczymy na ten sam dzien tygodnia."""
    today=dt.date.today();d=when;sample=False
    if (d.date()-today).days>21:
        k=(d.date()-today).days%7;base=today+dt.timedelta(days=7+k);d=dt.datetime.combine(base,d.time());sample=True
    url='https://api.transitous.org/api/v1/plan?'+urlencode({'fromPlace':f'{a[0]},{a[1]}','toPlace':f'{b[0]},{b[1]}','time':d.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'numItineraries':3})
    try:
        r=net.fetch_json(url,ttl=86400,tries=2,timeout=25)
        its=sorted(r.get('itineraries') or [],key=lambda i:(i.get('duration',9e9)+600*i.get('transfers',0)))
        if not its: return None
        i=its[0];legs=[]
        for l in i['legs']:
            if l['mode']=='WALK' and l.get('duration',0)<120: continue
            legs.append({'mode':l['mode'],'line':l.get('routeShortName') or l.get('tripShortName') or '', 'from':l['from'].get('name'),'to':l['to'].get('name'),'min':round(l.get('duration',0)/60),'headsign':l.get('headsign')})
        return {'min':round(i['duration']/60),'transfers':i.get('transfers',0),'legs':legs,'sample':sample}
    except Exception: return None
def weather(d,ci,co):
    """Prognoza do 14 dni; dalej srednie klimatyczne z wyraznym oznaczeniem."""
    a=dt.date.fromisoformat(ci);b=dt.date.fromisoformat(co);out={}
    if (b-dt.date.today()).days<=14:
        try:
            r=net.fetch_json(f"https://api.open-meteo.com/v1/forecast?latitude={d['lat']}&longitude={d['lon']}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code&timezone=auto&forecast_days=16",ttl=3*3600)
            x=r['daily']
            for i,day in enumerate(x['time']):
                if ci<=day<=co: out[day]={'tmax':x['temperature_2m_max'][i],'tmin':x['temperature_2m_min'][i],'rain':x['precipitation_probability_max'][i],'code':x['weather_code'][i],'kind':'forecast'}
        except Exception: pass
    return out
def sun(d,ci,co):
    """Wschod i zachod. Dane z tych samych dat rok wczesniej, roznica to najwyzej minuty.
    Zrodlo podaje czas wedlug dzisiejszego przesuniecia strefy, wiec przeliczamy je na czas z danego dnia."""
    from zoneinfo import ZoneInfo
    try:
        a=dt.date.fromisoformat(ci);b=dt.date.fromisoformat(co);ago=max(1,a.year-dt.date.today().year+1)
        f=lambda x:x.replace(year=x.year-ago,day=28 if (x.month,x.day)==(2,29) else x.day)
        j=net.fetch_json(f"https://archive-api.open-meteo.com/v1/archive?latitude={d['lat']}&longitude={d['lon']}&start_date={f(a)}&end_date={f(b)}&daily=sunrise,sunset&timezone=GMT",ttl=30*86400,tries=2,timeout=10)
        r=j['daily'];z=ZoneInfo(timezone_of(d))
        loc=lambda s:dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).astimezone(z).strftime('%H:%M')
        return {x[5:]:(loc(r['sunrise'][i]),loc(r['sunset'][i])) for i,x in enumerate(r['time'])}
    except Exception: return {}
def timezone_of(d):
    return net.fetch_json(f"https://api.open-meteo.com/v1/forecast?latitude={d['lat']}&longitude={d['lon']}&timezone=auto&forecast_days=1",ttl=90*86400,tries=2,timeout=10)['timezone']
def holidays(cc,a,b):
    res=[]
    for y in sorted({a[:4],b[:4]}):
        try:
            for h in net.fetch_json(f'https://date.nager.at/api/v3/PublicHolidays/{y}/{cc}',ttl=30*86400):
                if a<=h['date']<=b and h.get('global',True): res.append({'date':h['date'],'name':h.get('localName') or h['name']})
        except Exception: pass
    return res
FOOD='https://lewym90.github.io/globtroter/data/food/%s.json'
def restaurants(did):
    """Lokale z OpenStreetMap, zbudowane przez GitHub Actions. Brak pliku to None:
    wtedy dajemy link do mapy, nigdy wymyslonych nazw."""
    try: return net.fetch_json(FOOD%did,ttl=86400,tries=2,timeout=10)['r']
    except Exception: return None
def cluster(items,center,k):
    """Grupuje atrakcje w dni: k-srednich na wspolrzednych, potem najkrotsza kolejnosc."""
    if not items: return [[] for _ in range(k)]
    seeds=sorted(items,key=lambda x:-x['l'])[:k]
    cs=[(s['lat'],s['lon']) for s in seeds]
    while len(cs)<k: cs.append(cs[0])
    for _ in range(10):
        g=[[] for _ in range(k)]
        for it in items:
            i=min(range(k),key=lambda j:geo.km(it['lat'],it['lon'],*cs[j]));g[i].append(it)
        cs=[(sum(x['lat'] for x in q)/len(q),sum(x['lon'] for x in q)/len(q)) if q else cs[i] for i,q in enumerate(g)]
    return g
def order(st,start):
    res=[];cur=start;left=list(st)
    while left:
        n=min(left,key=lambda x:geo.km(cur[0],cur[1],x['lat'],x['lon']));left.remove(n);res.append(n);cur=(n['lat'],n['lon'])
    return res
def schedule_days(d,opt,hotel,prefs):
    """Plan dni. Pierwszy i ostatni dzien licza sie z godzin lotow."""
    A=ATTR.get(d['id'],[])
    style=prefs.get('pace','normal');limit={'slow':300,'normal':420,'fast':540}[style]
    arr=t(opt['arrive']) if opt.get('manual') else t(opt['flight']['out']['legs'][-1]['arr'])
    dep=t(opt['leave']) if opt.get('manual') else t(opt['flight']['back']['legs'][0]['dep'])
    H=(hotel['lat'],hotel['lon'])
    first=arr.date();last=dep.date();nd=(last-first).days+1
    pool=sorted(A,key=lambda x:-x['l'])[:max(8,nd*5)]
    interest=set(prefs.get('interests') or [])
    if interest: pool.sort(key=lambda x:(0 if x['t'] in interest else 1,-x['l']))
    days=[];groups=cluster(pool,H,max(1,nd));
    groups.sort(key=lambda g:-len(g))
    used=set();g_i=0
    for i in range(nd):
        day=first+dt.timedelta(days=i)
        start=dt.datetime.combine(day,dt.time(9,30));end=dt.datetime.combine(day,dt.time(20,0));kind='full'
        if i==0:
            start=max(start,add(arr,150));kind='arrival'
        if i==nd-1:
            end=min(end,add(dep,-300));kind='departure' if nd>1 else 'arrival'
        avail=(end-start).total_seconds()/60
        stops=[]
        if avail>=60:
            g=[x for x in groups[g_i%len(groups)] if x['q'] not in used] if groups else []
            g_i+=1
            cur=start;mins=0
            mon=day.weekday()==0
            for x in order(g,H):
                need=DUR.get(x['t'],45);walk=round(geo.km(H[0],H[1],x['lat'],x['lon'])/4.5*60) if not stops else round(geo.km(stops[-1]['lat'],stops[-1]['lon'],x['lat'],x['lon'])/4.5*60)
                walk=min(walk,45)
                if mins+need+walk>min(limit,avail): continue
                if mon and x['t']=='museum': continue
                if x['t'] in LATE and add(cur,walk).hour>=15: continue
                cur=add(cur,walk)
                if not any(s.get('meal') for s in stops) and cur.hour>=13 and avail>240:
                    stops.append({'meal':'lunch','time':hm(cur),'lat':x['lat'],'lon':x['lon'],'min':60});cur=add(cur,60)
                stops.append({'time':hm(cur),'name':x['n'][0].upper()+x['n'][1:],'type':LABEL.get(x['t'],'Zabytek'),'kind':x['t'],'min':need,'lat':x['lat'],'lon':x['lon'],'info':x.get('d') or x.get('de'),'infoEn':not x.get('d') and bool(x.get('de')),'src':x.get('src'),'img':x.get('img'),'web':x.get('web'),'map':place(x['n'],x['lat'],x['lon']),'walk':walk,'q':x['q']})
                used.add(x['q']);cur=add(cur,need);mins+=need+walk
            if stops and avail>240 and not any(s.get('meal') for s in stops):
                ls=[s for s in stops if not s.get('meal')][-1]
                stops.append({'meal':'lunch','time':hm(max(cur,dt.datetime.combine(day,dt.time(13,30)))),'lat':ls['lat'],'lon':ls['lon'],'min':60})
            if stops and kind!='departure':
                last_s=[s for s in stops if not s.get('meal')]
                if last_s: stops.append({'meal':'dinner','time':hm(max(cur,dt.datetime.combine(day,dt.time(19,0)))),'lat':last_s[-1]['lat'],'lon':last_s[-1]['lon'],'min':90})
        days.append({'date':day.isoformat(),'kind':kind,'stops':stops})
    return days
def attach_food(days,did,likes=None):
    meals=[s for dy in days for s in dy['stops'] if s.get('meal')]
    for s in meals: s['mapSearch']='https://www.google.com/maps/search/restauracje/@%s,%s,16z'%(s['lat'],s['lon'])
    if not meals: return True
    R=restaurants(did)
    if R is None: return False
    used=set()
    for s in meals:
        near=sorted([x for x in R if x['n'] not in used and geo.km(s['lat'],s['lon'],x['lat'],x['lon'])<.9],key=lambda x:(not any(k in x.get('c','') for k in likes or []),-x['s'],geo.km(s['lat'],s['lon'],x['lat'],x['lon'])))[:3]
        s['options']=[{'name':x['n'],'cuisine':x.get('c',''),'hours':x.get('h'),'web':x.get('w'),'map':place(x['n'],x['lat'],x['lon'])} for x in near]
        used.update(x['n'] for x in near)
    return True
INDOOR={'museum','church','palace','theatre'}
def explore(d):
    """Wszystko, co mamy o miejscu, do przegladania i dodawania do planu."""
    A=[{'name':x['n'][0].upper()+x['n'][1:],'kind':x['t'],'type':LABEL.get(x['t'],'Zabytek'),'min':DUR.get(x['t'],45),'lat':x['lat'],'lon':x['lon'],'img':x.get('img'),'web':x.get('web'),'info':x.get('d') or x.get('de'),'infoEn':not x.get('d') and bool(x.get('de')),'src':x.get('src'),'hours':x.get('h'),'indoor':x['t'] in INDOOR,'q':x['q'],'map':place(x['n'],x['lat'],x['lon'])} for x in sorted(ATTR.get(d['id'],[]),key=lambda x:-x['l'])]
    R=[{'name':x['n'],'cuisine':x.get('c',''),'hours':x.get('h'),'web':x.get('w'),'lat':x['lat'],'lon':x['lon'],'map':place(x['n'],x['lat'],x['lon'])} for x in (restaurants(d['id']) or [])]
    return {'attractions':A,'restaurants':R}
ROUTES={'foot':('routed-foot','foot'),'bike':('routed-bike','bike'),'car':('routed-car','driving')}
def route(b):
    """Prawdziwa trasa miedzy punktami dnia."""
    a=ROUTES.get(b.get('mode'))
    if not a: raise ValueError('Zły rodzaj trasy')
    pts=[(round(float(x[0]),5),round(float(x[1]),5)) for x in (b.get('pts') or [])[:24]]
    if len(pts)<2: raise ValueError('Za mało punktów')
    c=';'.join(f'{lo},{la}' for la,lo in pts)
    return net.fetch_json(f'https://routing.openstreetmap.de/{a[0]}/route/v1/{a[1]}/{c}?overview=full&geometries=geojson',ttl=30*86400,tries=2,timeout=20)
def geocode(q,near=None):
    """Adres noclegu na wspolrzedne. None, gdy nie znaleziono: wtedy pytamy o inny zapis, zamiast zgadywac."""
    from urllib.parse import quote
    if not str(q).strip(): raise ValueError('Podaj adres')
    r=net.fetch_json('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=3&q='+quote(str(q)[:160]),ttl=30*86400,tries=2,timeout=10,headers={'User-Agent':'Globtroter/1.5 (non-commercial travel planner)'})
    for x in r:
        la,lo=float(x['lat']),float(x['lon'])
        if not near or geo.km(near[0],near[1],la,lo)<200: return {'lat':la,'lon':lo,'label':x.get('display_name','')[:140]}
    return None
def custom_dest(x):
    """Miejsce spoza bazy, z wyszukiwarki nazw. Tylko to, co potrzebne do planu."""
    try: la,lo=float(x['lat']),float(x['lon'])
    except Exception: raise ValueError('Podaj miejsce')
    if not(-90<=la<=90 and -180<=lo<=180): raise ValueError('Złe współrzędne')
    return {'id':'x-'+geo.slug(str(x.get('name'))[:60]),'name':str(x.get('name'))[:60],'cc':str(x.get('cc') or '')[:2].upper(),'lat':la,'lon':lo,'tags':[],'air':[]}
def car_route(lat,lon,la,lo,cfg=None):
    """Trasa autem: odleglosc, czas i paliwo. Oplat drogowych za granica nie znamy, wiec ich nie podajemy."""
    r=net.fetch_json(f'https://router.project-osrm.org/route/v1/driving/{lon},{lat};{lo},{la}?overview=false',ttl=30*86400,tries=2,timeout=20)['routes'][0]
    km=round(r['distance']/1000);mins=round(r['duration']/60*1.1);cfg=cfg or {}
    stops=max(0,(mins-1)//150)*20
    return {'km':km,'min':mins+stops,'fuel':round(km*2*float(cfg.get('consumption') or 7.5)/100*float(cfg.get('fuelPrice') or 5.99)),'map':f'https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={la},{lo}&travelmode=driving'}
def manual(b):
    """Wyjazd bez lotu z wyszukiwarki: auto, pociag, wlasne bilety."""
    q=b.get('dest') or {};d=geo.BYID.get(q.get('id')) or custom_dest(q)
    a=dt.date.fromisoformat(b['from']);z=dt.date.fromisoformat(b['to'])
    if z<=a: raise ValueError('Powrót musi być po wyjeździe')
    if (z-a).days>60: raise ValueError('Wyjazd może mieć najwyżej 60 dni')
    home=b.get('home') or {};mode=b.get('mode') if b.get('mode') in('car','train','plane','other') else 'other'
    pax=b.get('pax') or {};A=max(1,int(pax.get('adults',1)));C=max(0,int(pax.get('children',0)))
    arr=dt.datetime.combine(a,dt.time.fromisoformat(b.get('arrive') or '15:00'));lv=dt.datetime.combine(z,dt.time.fromisoformat(b.get('leave') or '10:00'))
    H=(d['lat'],d['lon']);tl=[];rt=[];items=[];leave=None;warn=[];links_=[]
    mname={'car':'Autem','train':'Pociągiem','plane':'Samolotem','other':'Własnym transportem'}[mode]
    ha=home.get('lat') is not None
    if mode=='car' and ha:
        c=car_route(float(home['lat']),float(home['lon']),d['lat'],d['lon'],b.get('transport'))
        leave=add(arr,-c['min']);tl.append(dict(at=leave.isoformat(timespec='minutes'),title='Wyjazd z domu',text=f"{c['km']} km, około {span(c['min'])} z postojami.",sure='est',icon='car',map=c['map']))
        items.append({'label':f"Paliwo {c['km']*2} km",'pln':c['fuel'],'est':True})
        if c['min']>540: warn.append(f"Trasa to około {span(c['min'])}. Rozważ nocleg po drodze.")
        warn.append('Opłat za autostrady i winiet za granicą nie liczymy. Sprawdź je dla swojej trasy.')
        rt.append(dict(at=lv.isoformat(timespec='minutes'),title='Wyjazd do domu',text=f"Około {span(c['min'])} z postojami.",sure='est',icon='car'))
        rt.append(dict(at=add(lv,c['min']).isoformat(timespec='minutes'),title='W domu',text='',sure='est',icon='home'))
        o_drive={'km':c['km'],'min':c['min']}
    else:
        o_drive={'km':0,'min':0}
        if mode=='train' and ha:
            tr=transit((float(home['lat']),float(home['lon'])),H,dt.datetime.combine(a,dt.time(7,0)))
            links_=[{'site':'Połączenie w Google Maps','url':f"https://www.google.com/maps/dir/?api=1&origin={home['lat']},{home['lon']}&destination={d['lat']},{d['lon']}&travelmode=transit"},{'site':'PKP Intercity','url':'https://www.intercity.pl/'},{'site':'Deutsche Bahn','url':'https://www.bahn.com/pl'}]
            if tr:
                leave=add(arr,-tr['min']);tl.append(dict(at=leave.isoformat(timespec='minutes'),title='Wyjazd z domu',text=f"Około {span(tr['min'])}, {przes(tr['transfers'])}.",legs=tr['legs'],sample=tr['sample'],sure='est',icon='bus'))
            else: warn.append('Nie mamy rozkładu dla tej trasy. Sprawdź połączenie w linkach.')
        tl.append(dict(at=arr.isoformat(timespec='minutes'),title='Na miejscu',text=f"{mname}. Godzina, którą podałeś.",sure='check',icon='door'))
        rt.append(dict(at=lv.isoformat(timespec='minutes'),title='Wyjazd do domu',text=f"{mname}. Godzina, którą podałeś.",sure='check',icon='door'))
    c_t=float(b.get('transportCost') or 0)
    if c_t>0: items.append({'label':'Transport','pln':round(c_t),'est':False})
    if mode=='car': tl.append(dict(at=arr.isoformat(timespec='minutes'),title='Na miejscu',text='',sure='est',icon='door'))
    hc=float(b.get('hotelCost') or 0);name=str(b.get('hotel') or '').strip()[:80]
    h={'name':name or 'Nocleg do wyboru','lat':d['lat'],'lon':d['lon'],'bestTotal':round(hc) if hc>0 else None,'breakfast':False}
    o={'id':__import__('uuid').uuid4().hex[:10],'manual':True,'mode':mode,'modeName':mname,'dest':{k:d.get(k) for k in('id','name','cc','lat','lon','tags','desc','ta')},'from':'','to':'','fromName':home.get('label','Dom'),'toName':d['name'],'dep':a.isoformat(),'ret':z.isoformat(),'nights':(z-a).days,'pax':{'adults':A,'children':C},'arrive':arr.isoformat(timespec='minutes'),'leave':lv.isoformat(timespec='minutes'),'flight':None,'links':links_,'tickets':0,'verified':True,'total':0,'access':{'mode':mode,'items':items,'total':sum(i['pln'] for i in items)},'drive':o_drive,'warnings':warn,'calendar':[]}
    o['total']=o['access']['total']
    if leave: o['leaveHome']=leave.isoformat(timespec='minutes')
    p=finish(d,o,h,home,b.get('prefs') or {},mode,tl,rt,False,None)
    return p
def build(body):
    o=body['option'];h=body['hotel'];home=body['home'];prefs=body.get('prefs') or {}
    if not o.get('flight'): raise ValueError('Ten wariant nie ma potwierdzonych lotów. Wybierz potwierdzony.')
    d=geo.BYID[o['dest']['id']];F=o['flight'];mode=o['access']['mode']
    outL=F['out']['legs'];backL=F['back']['legs']
    dep=t(outL[0]['dep']);arr=t(outL[-1]['arr']);bdep=t(backL[0]['dep']);barr=t(backL[-1]['arr'])
    AP=geo.AIRPORTS;oa=AP[o['from']];da=AP[o['to']]
    sch=d['cc'] not in search.NONSCH
    buf=120 if sch else 150
    road=round(o['drive']['min']*1.15)+20
    extra=25 if mode=='car' else 10
    leave=add(dep,-(buf+extra+road))
    H=(h['lat'],h['lon']);hmap=gmaps((da['lat'],da['lon']),H)
    tl=[];e=lambda **k:tl.append(k)
    e(at=leave.isoformat(timespec='minutes'),title='Wyjazd z domu',text=f"{home.get('label','Dom')} → {search.aname(o['from'])}. {o['drive']['km']} km, około {span(road)} z zapasem na korki.",sure='est',icon='car',map=gmaps((home['lat'],home['lon']),(oa['lat'],oa['lon']),'driving' if mode!='public' else 'transit'))
    if mode=='car': e(at=add(dep,-(buf+extra)).isoformat(timespec='minutes'),title='Parking',text=f"Zostawiasz auto. Rezerwacja online zwykle jest tańsza.",sure='est',icon='park')
    e(at=add(dep,-buf).isoformat(timespec='minutes'),title='Lotnisko',text=f"{oa['name']}. Nadanie bagażu, kontrola bezpieczeństwa"+('' if sch else ', kontrola paszportowa')+'.',sure='est',icon='door')
    e(at=add(dep,-30).isoformat(timespec='minutes'),title='Bramka',text='Bramki zwykle zamykają się 20–30 minut przed odlotem. Numer bramki sprawdź na tablicy.',sure='est',icon='gate')
    for l in outL:
        e(at=l['dep'],title=f"Wylot {l['airline']} {l['no']}",text=f"{l['airlineName']}, {AP.get(l['from'],{}).get('city',l['from'])} → {AP.get(l['to'],{}).get('city',l['to'])}, ląduje o {l['arr'][11:]} czasu lokalnego.",sure='fact',icon='plane')
    tr=transit((da['lat'],da['lon']),H,add(arr,45))
    ta=add(arr,35 if sch else 55)
    trm=tr['min'] if tr else round(geo.km(da['lat'],da['lon'],H[0],H[1])*1.4/30*60)+25
    e(at=ta.isoformat(timespec='minutes'),title='Z lotniska do hotelu',text=(f"Około {span(tr['min'])} komunikacją, {przes(tr['transfers'])}." if tr else 'Nie mamy rozkładu dla tej trasy, sprawdź połączenie na mapie.'),legs=(tr or {}).get('legs'),sample=(tr or {}).get('sample'),sure='fact' if tr and not tr['sample'] else 'est',icon='bus',map=hmap)
    e(at=add(ta,trm).isoformat(timespec='minutes'),title=(f"Hotel: {h['name']}" if h.get('bestTotal') else 'Twój nocleg'),text='Zameldowanie zwykle od 14:00–15:00. Sprawdź godzinę w potwierdzeniu.',sure='check',icon='bed',map=place(h['name'],H[0],H[1]))
    rt=[]
    r2=transit(H,(da['lat'],da['lon']),add(bdep,-(buf+180)))
    rm=r2['min'] if r2 else trm
    lh=add(bdep,-(buf+rm+30))
    rt.append(dict(at=lh.isoformat(timespec='minutes'),title='Wyjście z hotelu',text=f"Około {span(rm)} na lotnisko, w tym 30 min zapasu.",legs=(r2 or {}).get('legs'),sure='est',icon='bus',map=gmaps(H,(da['lat'],da['lon']))))
    rt.append(dict(at=add(bdep,-buf).isoformat(timespec='minutes'),title='Lotnisko',text=da['name'],sure='est',icon='door'))
    for l in backL:
        rt.append(dict(at=l['dep'],title=f"Powrót {l['airline']} {l['no']}",text=f"{l['airlineName']}, ląduje o {l['arr'][11:]}.",sure='fact',icon='plane'))
    rt.append(dict(at=add(barr,road+40).isoformat(timespec='minutes'),title='W domu',text=(f"Około {span(road)} jazdy po odebraniu auta." if mode=='car' else f"Około {span(road)} drogi z lotniska."),sure='est',icon='home'))
    return finish(d,o,h,home,prefs,mode,tl,rt,F['out']['legs'][0]['airline'] in search.LCC,(c0:=None))
def finish(d,o,h,home,prefs,mode,tl,rt,bags,c0):
    days=schedule_days(d,o,h,prefs)
    wx=weather(d,o['dep'],o['ret']);sn=sun(d,o['dep'],o['ret'])
    m=int(o['dep'][5:7]);cl=(d.get('climate') or {})
    for dy in days:
        if dy['date'] in wx: dy['weather']=wx[dy['date']]
        if dy['date'][5:] in sn: dy['sun']=sn[dy['date'][5:]]
    food=attach_food(days,d['id'],prefs.get('food'))
    from climate import month as cm
    c=countries.info(d['cc']);hol=holidays(d['cc'],o['dep'],o['ret'])
    rate=None
    if c and c['currency']!='PLN':
        try: rate=net.fx(c['currency'])
        except Exception: pass
    if c: c['rate']=rate
    check=[{'t':f"{c['docs'] if c else 'Dokument tożsamości'} ważny przez cały wyjazd",'d':-30},{'t':'Sprawdź wymogi wjazdu w MSZ','d':-14,'url':(c or {}).get('msz')}]
    if c and c['ekuz']: check.append({'t':'Karta EKUZ','d':-14,'url':'https://www.nfz.gov.pl/dla-pacjenta/nasze-zdrowie-w-europie/'})
    check+=[{'t':'Ubezpieczenie turystyczne','d':-14},{'t':'Rezerwacja parkingu','d':-7} if mode=='car' and not o.get('manual') else {'t':'Przegląd auta: opony, płyny, winiety','d':-7} if o.get('manual') and o.get('mode')=='car' else {'t':'Bilety na dojazd','d':-7},{'t':'Odprawa online: zwykle 24–48 h przed lotem','d':-2} if not o.get('manual') or o.get('mode')=='plane' else {'t':'Sprawdź trasę i bilety na dojazd','d':-2},{'t':'Pobierz bilety i karty pokładowe','d':-1},{'t':'Ładowarka i powerbank w bagażu podręcznym','d':-1}]
    if bags: check.insert(2,{'t':'Dokup bagaż u linii. Na lotnisku jest dużo drożej','d':-7})
    if c and 'C' not in c['plugs']: check.append({'t':f"Adapter do gniazdek {c['plugs']}",'d':-3})
    cost=([] if o.get('manual') else [{'label':'Bilety','pln':o['tickets'],'sure':'fact' if o['verified'] else 'est'}])+[{'label':i['label'],'pln':i['pln'],'sure':'est'} for i in o['access']['items']]
    if o.get('bags'): cost.append({'label':'Bagaż (szacunek)','pln':o['bags'],'sure':'est'})
    if h.get('bestTotal'): cost.append({'label':f"Nocleg: {h['name']}",'pln':h['bestTotal'],'sure':'est'})
    elif o.get('hotelEst'): cost.append({'label':'Nocleg','pln':o['hotelEst']['total'],'sure':'est'})
    return {'title':f"{d['name']}: {o['nights']} nocy",'dest':{k:d.get(k) for k in('id','name','cc','lat','lon')},'option':o,'hotel':h,'home':home,'timeline':tl,'return':rt,'days':days,'climate':cm(d,m),'climateSource':cl.get('station'),'country':c,'holidays':hol,'checklist':sorted(check,key=lambda x:x['d']),'cost':cost,'total':sum(x['pln'] for x in cost),'foodOk':food is not False,'at':dt.datetime.now().isoformat(timespec='minutes')}
