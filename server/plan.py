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
def move_min(a,b,drive=False):
    """Czas przejscia albo dojazdu miedzy punktami. Przy wakacjach z biurem dalsze punkty liczymy taksowka lub autem."""
    k=geo.km(a[0],a[1],b[0],b[1])
    if drive and k>2.5: return round(k*1.3/40*60)+10 if k<=10 else round(k*1.25/55*60)+10
    return min(round(k/4.5*60),45)
def by_car(a,b,drive): return drive and geo.km(a[0],a[1],b[0],b[1])>2.5
def schedule_days(d,opt,hotel,prefs,A=None):
    """Plan dni. Pierwszy i ostatni dzien licza sie z godzin lotow."""
    A=ATTR.get(d['id'],[]) if A is None else A
    drive=bool(prefs.get('drive'));board=prefs.get('board') or ''
    mix={'many':1,'half':.5,'rest':.25}.get(prefs.get('mix'),1)
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
    full_i=0
    for i in range(nd):
        day=first+dt.timedelta(days=i)
        start=dt.datetime.combine(day,dt.time(9,30));end=dt.datetime.combine(day,dt.time(20,0));kind='full'
        if 0<i<nd-1:
            full_i+=1
            # dni odpoczynku rozlozone rowno: przy 'half' co drugi, przy 'rest' co czwarty dzien zwiedzania
            if mix<1 and int(full_i*mix)==int((full_i-1)*mix):
                days.append({'date':day.isoformat(),'kind':'rest','stops':[]});continue
        if i==0:
            start=max(start,add(arr,150));kind='arrival'
            if drive: start=end  # z biurem: dzien przylotu to hotel i odpoczynek
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
                frm=H if not stops else (stops[-1]['lat'],stops[-1]['lon'])
                need=DUR.get(x['t'],45);walk=move_min(frm,(x['lat'],x['lon']),drive);car=by_car(frm,(x['lat'],x['lon']),drive)
                if mins+need+walk>min(limit,avail): continue
                if mon and x['t']=='museum': continue
                if x['t'] in LATE and add(cur,walk).hour>=15: continue
                cur=add(cur,walk)
                if board not in('ai','fb') and not any(s.get('meal') for s in stops) and cur.hour>=13 and avail>240:
                    stops.append({'meal':'lunch','time':hm(cur),'lat':x['lat'],'lon':x['lon'],'min':60});cur=add(cur,60)
                stops.append({'time':hm(cur),'name':x['n'][0].upper()+x['n'][1:],'type':LABEL.get(x['t'],'Zabytek'),'kind':x['t'],'min':need,'lat':x['lat'],'lon':x['lon'],'info':x.get('d') or x.get('de'),'infoEn':not x.get('d') and bool(x.get('de')),'src':x.get('src'),'img':x.get('img'),'web':x.get('web'),'map':place(x['n'],x['lat'],x['lon']),'walk':walk,'q':x['q'],**({'by':'car'} if car else {})})
                used.add(x['q']);cur=add(cur,need);mins+=need+walk
            if board not in('ai','fb') and stops and avail>240 and not any(s.get('meal') for s in stops):
                ls=[s for s in stops if not s.get('meal')][-1]
                stops.append({'meal':'lunch','time':hm(max(cur,dt.datetime.combine(day,dt.time(13,30)))),'lat':ls['lat'],'lon':ls['lon'],'min':60})
            if board not in('ai','fb','hb') and stops and kind!='departure':
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
def tour_days(H,arr,dep,prefs):
    """Dni wakacji z biurem: na zmiane okolica hotelu i jednodniowe wycieczki do miejsc z bazy, do tego dni odpoczynku."""
    limit={'slow':300,'normal':420,'fast':540}[prefs.get('pace','normal')];board=prefs.get('board') or 'ro'
    mix={'many':1,'half':.5,'rest':.25}.get(prefs.get('mix'),.5)
    seen=set();local=[]
    for d in geo.DESTS:
        if geo.km(H[0],H[1],d['lat'],d['lon'])<=40:
            for x in ATTR.get(d['id'],[]):
                if x['q'] not in seen and geo.km(H[0],H[1],x['lat'],x['lon'])<=12: seen.add(x['q']);local.append(x)
    local.sort(key=lambda x:-x['l'])
    trips=[]
    for d in sorted(geo.DESTS,key=lambda d:geo.km(H[0],H[1],d['lat'],d['lon'])):
        k=geo.km(H[0],H[1],d['lat'],d['lon'])
        if k>120: break
        P=sorted([x for x in ATTR.get(d['id'],[]) if x['q'] not in seen and geo.km(d['lat'],d['lon'],x['lat'],x['lon'])<=8],key=lambda x:-x['l'])
        if k>12 and len(P)>=3: trips.append((d,P))
    first=arr.date();last=dep.date();nd=(last-first).days+1
    days=[];full_i=0;turn=0;ti=0
    def fill(day,pool,start,end,trip=None):
        cur=start;mins=0;stops=[];pos=H
        for x in order(pool[:8],H):
            if x['q'] in used: continue
            need=DUR.get(x['t'],45);mv=move_min(pos,(x['lat'],x['lon']),True);car=by_car(pos,(x['lat'],x['lon']),True)
            back=move_min((x['lat'],x['lon']),H,True)
            if mins+need+mv>limit or add(cur,mv+need+back)>end: continue
            if day.weekday()==0 and x['t']=='museum': continue
            cur=add(cur,mv)
            if board not in('ai','fb') and not any(s.get('meal') for s in stops) and cur.hour>=13:
                stops.append({'meal':'lunch','time':hm(cur),'lat':x['lat'],'lon':x['lon'],'min':60});cur=add(cur,60)
            stops.append({'time':hm(cur),'name':x['n'][0].upper()+x['n'][1:],'type':LABEL.get(x['t'],'Zabytek'),'kind':x['t'],'min':need,'lat':x['lat'],'lon':x['lon'],'info':x.get('d') or x.get('de'),'infoEn':not x.get('d') and bool(x.get('de')),'src':x.get('src'),'img':x.get('img'),'web':x.get('web'),'map':place(x['n'],x['lat'],x['lon']),'walk':mv,'q':x['q'],**({'by':'car'} if car else {})})
            used.add(x['q']);cur=add(cur,need);mins+=need+mv;pos=(x['lat'],x['lon'])
            if len([s for s in stops if not s.get('meal')])>=(4 if trip else 3): break
        if stops and board in('ro','bb'):
            ls=[s for s in stops if not s.get('meal')][-1]
            stops.append({'meal':'dinner','time':hm(max(cur,dt.datetime.combine(day,dt.time(19,0)))),'lat':ls['lat'] if not trip else H[0],'lon':ls['lon'] if not trip else H[1],'min':90})
        return stops
    used=set()
    for i in range(nd):
        day=first+dt.timedelta(days=i)
        if i==0: days.append({'date':day.isoformat(),'kind':'arrival','stops':[]});continue
        if i==nd-1: days.append({'date':day.isoformat(),'kind':'departure' if nd>1 else 'arrival','stops':[]});continue
        full_i+=1
        if mix<1 and int(full_i*mix)==int((full_i-1)*mix): days.append({'date':day.isoformat(),'kind':'rest','stops':[]});continue
        left=[x for x in local if x['q'] not in used]
        go_trip=ti<len(trips) and (turn%2==1 or len(left)<2)
        st=[];trip=None
        if go_trip:
            trip,P=trips[ti];ti+=1
            st=fill(day,P,dt.datetime.combine(day,dt.time(8,30)),dt.datetime.combine(day,dt.time(20,0)),trip)
        if not st and len(left)>=1: trip=None;st=fill(day,left,dt.datetime.combine(day,dt.time(9,30)),dt.datetime.combine(day,dt.time(19,0)))
        turn+=1
        dy={'date':day.isoformat(),'kind':'full' if st else 'rest','stops':st}
        if trip and st: dy['trip']=trip['name']
        days.append(dy)
    return days
BOARD={'ai':'All inclusive','fb':'Pełne wyżywienie','hb':'Śniadania i obiadokolacje','bb':'Śniadania','ro':'Bez wyżywienia'}
def tour(b):
    """Wakacje z biurem: loty, hotel i wyzywienie podaje uzytkownik. My ukladamy dojazd na lotnisko, przylot, dni i powrot."""
    H0=b.get('hotel') or {}
    try: H=(float(H0['lat']),float(H0['lon']))
    except Exception: raise ValueError('Wskaż hotel na mapie albo wpisz jego adres')
    if not(-90<=H[0]<=90 and -180<=H[1]<=180): raise ValueError('Złe położenie hotelu')
    hname=str(H0.get('name') or 'Hotel').strip()[:80]
    AP=geo.AIRPORTS;fo=b.get('out') or {};fb=b.get('back') or {}
    for k,f in (('wylotu',fo),('powrotu',fb)):
        if f.get('from') not in AP or f.get('to') not in AP: raise ValueError(f'Wybierz lotniska {k}')
    try:
        dep=dt.datetime.fromisoformat(f"{fo['date']}T{fo['time']}");arr=dt.datetime.fromisoformat(f"{fo.get('arrDate') or fo['date']}T{fo['arr']}")
        bdep=dt.datetime.fromisoformat(f"{fb['date']}T{fb['time']}");barr=dt.datetime.fromisoformat(f"{fb.get('arrDate') or fb['date']}T{fb['arr']}")
    except Exception: raise ValueError('Uzupełnij daty i godziny lotów')
    if arr<dep-dt.timedelta(hours=4): arr+=dt.timedelta(days=1)   # przylot po polnocy
    if barr<bdep-dt.timedelta(hours=4): barr+=dt.timedelta(days=1)
    if bdep<=arr: raise ValueError('Powrót musi być po przylocie')
    if (bdep.date()-arr.date()).days>45: raise ValueError('Wyjazd może mieć najwyżej 45 dni')
    # najblizsze miejsce z naszej bazy daje atrakcje i restauracje; dalej niz 80 km = miejsce spoza bazy
    near=sorted(((geo.km(H[0],H[1],d['lat'],d['lon']),d) for d in geo.DESTS),key=lambda x:x[0])
    pool={};base=None
    for k,d in near:
        if k>80: break
        base=base or d
        for x in ATTR.get(d['id'],[]):
            if geo.km(H[0],H[1],x['lat'],x['lon'])<=70: pool[x['q']]=x
    d=dict(base) if base else custom_dest({'name':hname,'lat':H[0],'lon':H[1],'cc':b.get('cc') or AP[fo['to']]['cc']})
    if base and geo.km(H[0],H[1],base['lat'],base['lon'])>15:
        d=dict(base,name=f"{base['name']} (okolice)")
    # bliskie i wazne najpierw: waga spada z odlegloscia od hotelu
    A=sorted(pool.values(),key=lambda x:-(x['l']/(1+geo.km(H[0],H[1],x['lat'],x['lon'])/15)))
    home=b.get('home') or {};pax=b.get('pax') or {};Ad=max(1,int(pax.get('adults',2)));C=max(0,int(pax.get('children',0)))
    board=b.get('board') if b.get('board') in BOARD else 'ro'
    oa=AP[fo['from']];da=AP[fo['to']];ra=AP[fb['from']];ha=AP[fb['to']]
    sch=d['cc'] not in search.NONSCH;buf=120 if sch else 150
    tl=[];rt=[];items=[];warn=[]
    e=lambda **k:tl.append(k)
    road=None
    if home.get('lat') is not None:
        try:
            c=car_route(float(home['lat']),float(home['lon']),oa['lat'],oa['lon'],b.get('transport'))
            road=round(c['min']*1.15)+20;leave=add(dep,-(buf+25+road))
            e(at=leave.isoformat(timespec='minutes'),title='Wyjazd z domu',text=f"{home.get('label','Dom')} → {search.aname(fo['from'])}. {c['km']} km, około {span(road)} z zapasem na korki.",sure='est',icon='car',map=c['map'])
            e(at=add(dep,-(buf+25)).isoformat(timespec='minutes'),title='Parking',text='Zostawiasz auto. Rezerwacja online zwykle jest tańsza.',sure='est',icon='park')
            items.append({'label':f"Paliwo na lotnisko i z powrotem ({c['km']*2} km)",'pln':c['fuel'],'est':True})
            days_p=(barr.date()-dep.date()).days+1
            try:
                import access;items.append({'label':f'Parking przy lotnisku, {days_p} dni','pln':access.parking(fo['from'],days_p),'est':True})
            except Exception: pass
        except Exception: warn.append('Nie udało się policzyć dojazdu na lotnisko. Sprawdź trasę w mapach.')
    e(at=add(dep,-buf).isoformat(timespec='minutes'),title='Lotnisko',text=f"{oa['name']}. Stanowisko biura i odprawa"+('' if sch else ', kontrola paszportowa')+'. Dokładną godzinę zbiórki podaje biuro.',sure='check',icon='door')
    e(at=dep.isoformat(timespec='minutes'),title='Wylot',text=f"{oa.get('city') or fo['from']} → {da.get('city') or fo['to']}"+(f", lot {str(fo.get('no'))[:10]}" if fo.get('no') else '')+f". Przylot o {arr.strftime('%H:%M')} czasu lokalnego.",sure='fact',icon='plane')
    km_h=geo.km(da['lat'],da['lon'],H[0],H[1]);trm=round(km_h*1.3/50*60)+20
    ta=add(arr,40 if sch else 75)
    if b.get('transfer',True): e(at=ta.isoformat(timespec='minutes'),title='Transfer biura do hotelu',text=f"Autokar biura czeka przy wyjściu. Hotel jest {round(km_h)} km od lotniska, przejazd około {span(trm)}, z rozwożeniem do innych hoteli może trwać dłużej."+('' if sch else ' Wcześniej kontrola paszportowa'+(' i wiza na lotnisku' if d['cc'] in('EG','JO') else '')+'.'),sure='est',icon='bus',map=gmaps((da['lat'],da['lon']),H,'driving'))
    else: e(at=ta.isoformat(timespec='minutes'),title='Z lotniska do hotelu',text=f"{round(km_h)} km, taksówką około {span(trm)}. Cenę taksówki ustal przed jazdą.",sure='est',icon='bus',map=gmaps((da['lat'],da['lon']),H,'driving'))
    e(at=add(ta,trm).isoformat(timespec='minutes'),title=f"Hotel: {hname}",text='Zameldowanie zwykle od 14:00. Przy wcześniejszym przylocie bagaż zostawisz w recepcji.',sure='check',icon='bed',map=place(hname,H[0],H[1]))
    rm=trm+(60 if b.get('transfer',True) else 20)
    rt.append(dict(at=add(bdep,-(buf+rm)).isoformat(timespec='minutes'),title='Wyjazd z hotelu',text='Godzinę odbioru transferu biuro podaje dzień lub dwa wcześniej, zwykle na tablicy w hotelu lub przez rezydenta.' if b.get('transfer',True) else f"Taksówką około {span(trm)} na lotnisko.",sure='check',icon='bus',map=gmaps(H,(ra['lat'],ra['lon']),'driving')))
    rt.append(dict(at=add(bdep,-buf).isoformat(timespec='minutes'),title='Lotnisko',text=ra['name'],sure='est',icon='door'))
    rt.append(dict(at=bdep.isoformat(timespec='minutes'),title='Powrót',text=f"{ra.get('city') or fb['from']} → {ha.get('city') or fb['to']}"+(f", lot {str(fb.get('no'))[:10]}" if fb.get('no') else '')+f". Ląduje o {barr.strftime('%H:%M')}.",sure='fact',icon='plane'))
    if road: rt.append(dict(at=add(barr,road+40).isoformat(timespec='minutes'),title='W domu',text=f"Około {span(road)} jazdy po odebraniu auta.",sure='est',icon='home'))
    price=float(b.get('price') or 0)
    if price>0: items.insert(0,{'label':f"Wyjazd z biurem{(' '+str(b.get('agency'))[:40]) if b.get('agency') else ''}",'pln':round(price),'est':False})
    if not pool: warn.append('W okolicy hotelu nie mamy jeszcze atrakcji w bazie. Dni są wolne, a miejsca do zwiedzania dodasz z wyszukiwarki atrakcji.')
    h={'name':hname,'lat':H[0],'lon':H[1],'bestTotal':None,'breakfast':board!='ro','board':BOARD[board],'own':True,'address':str(H0.get('label') or '')[:140],'ci':arr.date().isoformat(),'co':bdep.date().isoformat(),'code':str(b.get('ref') or '')[:40]}
    o={'id':__import__('uuid').uuid4().hex[:10],'manual':True,'tour':{'agency':str(b.get('agency') or '')[:60],'ref':str(b.get('ref') or '')[:60],'url':str(b.get('url') or '')[:500] if str(b.get('url') or '').startswith('https://') else '','board':BOARD[board],'transfer':bool(b.get('transfer',True)),'price':round(price) if price>0 else None},
       'mode':'plane','modeName':'Z biurem podróży','dest':{k:d.get(k) for k in('id','name','cc','lat','lon','tags','desc','ta')},'from':fo['from'],'to':fo['to'],'fromName':home.get('label','Dom'),'toName':d['name'],
       'dep':dep.date().isoformat(),'ret':barr.date().isoformat(),'nights':(bdep.date()-arr.date()).days,'pax':{'adults':Ad,'children':C},'arrive':add(ta,trm).isoformat(timespec='minutes'),'leave':add(bdep,-(buf+rm)).isoformat(timespec='minutes'),
       'flight':None,'links':[],'tickets':0,'verified':True,'total':0,'access':{'mode':'car','items':items,'total':sum(i['pln'] for i in items)},'drive':{'km':0,'min':0},'warnings':warn,'calendar':[]}
    o['total']=o['access']['total']
    prefs=dict(b.get('prefs') or {},drive=True,board=board,mix=b.get('mix') or 'half')
    days=tour_days(H,arr,bdep,prefs)
    return finish(d,o,h,home,prefs,'car',tl,rt,False,None,days=days)
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
def finish(d,o,h,home,prefs,mode,tl,rt,bags,c0,days=None):
    days=days if days is not None else schedule_days(d,o,h,prefs)
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
    if o.get('tour'):
        tr=o['tour'];check=[x for x in check if x['d']<=-14 and x['t']!='Ubezpieczenie turystyczne']
        check+=[{'t':'Sprawdź, co obejmuje ubezpieczenie z biura. Rozważ rozszerzenie o koszty leczenia i choroby przewlekłe','d':-14},
                {'t':'Rezerwacja parkingu przy lotnisku','d':-7},{'t':'Godzina zbiórki na lotnisku i voucher od biura'+(f" ({tr['agency']})" if tr.get('agency') else ''),'d':-3,'url':tr.get('url') or None},
                {'t':'Gotówka w euro lub dolarach na wizę i napiwki' if d['cc'] in('EG','JO') else 'Trochę gotówki na napiwki i drobne wydatki','d':-2},
                {'t':'Ładowarka i powerbank w bagażu podręcznym','d':-1}]
        if tr.get('ref'): check.append({'t':f"Numer rezerwacji: {tr['ref']}",'d':-1})
    if bags: check.insert(2,{'t':'Dokup bagaż u linii. Na lotnisku jest dużo drożej','d':-7})
    if c and 'C' not in c['plugs']: check.append({'t':f"Adapter do gniazdek {c['plugs']}",'d':-3})
    cost=([] if o.get('manual') else [{'label':'Bilety','pln':o['tickets'],'sure':'fact' if o['verified'] else 'est'}])+[{'label':i['label'],'pln':i['pln'],'sure':'est' if i.get('est',True) else 'fact'} for i in o['access']['items']]
    if o.get('bags'): cost.append({'label':'Bagaż (szacunek)','pln':o['bags'],'sure':'est'})
    if h.get('bestTotal'): cost.append({'label':f"Nocleg: {h['name']}",'pln':h['bestTotal'],'sure':'est'})
    elif o.get('hotelEst'): cost.append({'label':'Nocleg','pln':o['hotelEst']['total'],'sure':'est'})
    return {'title':f"{d['name']}: {o['nights']} nocy",'dest':{k:d.get(k) for k in('id','name','cc','lat','lon')},'option':o,'hotel':h,'home':home,'timeline':tl,'return':rt,'days':days,'climate':cm(d,m),'climateSource':cl.get('station'),'country':c,'holidays':hol,'checklist':sorted(check,key=lambda x:x['d']),'cost':cost,'total':sum(x['pln'] for x in cost),'foodOk':food is not False,'at':dt.datetime.now().isoformat(timespec='minutes')}
