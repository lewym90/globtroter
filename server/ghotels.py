"""Drugie zrodlo hoteli: strona Google Hotels. Dane sa wbudowane w strone jako struktura JSON.
Zwraca tylko rekordy zgodne z podanymi datami i lezace przy celu. Awaria to None, nigdy zgadywanie."""
import datetime as dt,html,json,logging,re,threading,time,base64
from urllib.parse import quote,unquote
import geo,net,store
log=logging.getLogger('ghotels')
MONTHS='January February March April May June July August September October November December'.split()
ALIAS={'Thira':'Santorini','Arrecife':'Lanzarote','Puerto del Rosario':'Fuerteventura','Faro':'Algarve','Argostoli':'Kefalonia','Sarandë':'Saranda','Valletta':'Malta','Chamonix-Mont-Blanc':'Chamonix','Funchal':'Madeira','Ponta Delgada':'Azores Sao Miguel','Sal (Cape Verde)':'Sal Cape Verde','Boa Vista (Cape Verde)':'Boa Vista Cape Verde'}
_l=threading.Lock();_last=[0.0];_blocked=[0.0]
_dec=json.JSONDecoder()
def query(name,ci,co):
    a,b=dt.date.fromisoformat(ci),dt.date.fromisoformat(co)
    f=lambda d:f'{MONTHS[d.month-1]} {d.day} {d.year}'
    return f'hotels in {name} from {f(a)} to {f(b)}'
def records(text):
    """Wyciaga rekordy hoteli z blokow danych strony."""
    out=[]
    for x in re.finditer(r"AF_initDataCallback\(\{key: 'ds:\d+'.*?data:",text,re.S):
        try: o,_=_dec.raw_decode(text[x.end():])
        except Exception: continue
        st=[o]
        while st:
            n=st.pop()
            if isinstance(n,dict):
                for k,v in n.items():
                    if k=='397419284' and isinstance(v,list) and v: out.append(v[0])
                    else: st.append(v)
            elif isinstance(n,list): st.extend(n)
    return out
def _num(s):
    d=re.sub(r'[^\d]','',s or '');return int(d) if d else None
def parse(r,ci,co):
    """Zamienia rekord na hotel albo None, gdy czegokolwiek waznego brakuje lub daty sie nie zgadzaja."""
    try:
        name=r[1];pos=r[2][0];p=r[6];head=p[1];offer=p[2]
        if not name or not offer or not offer[1]: return None
        a,b=head[4][0],head[4][1]
        if dt.date(*a).isoformat()!=ci or dt.date(*b).isoformat()!=co: return None
        cur=head[3];night=offer[1][4] if len(offer[1])>4 and offer[1][4] else None
        total=_num(offer[10][0]) if len(offer)>10 and offer[10] else None
        n=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days
        if not night and total: night=total/n
        if not night or night<=0: return None
        rate=r[7][0] if r[7] else None
        img=None
        try: img=r[5][1][0][1][0]
        except Exception: pass
        return {'name':name,'lat':pos[0],'lon':pos[1],'stars':(r[3][1] if r[3] and len(r[3])>1 else None),'kind':(r[3][0] if r[3] else None),'rating':rate[0] if rate else None,'reviews':rate[1] if rate else 0,'image':img,'night':night,'total':total or night*n,'currency':cur,'id':r[20] if len(r)>20 else None}
    except Exception: return None
AMEN={'Free breakfast':'śniadanie w cenie','Free Wi-Fi':'darmowe Wi-Fi','Free parking':'darmowy parking','Parking ($)':'parking płatny','Parking':'parking','Outdoor pool':'basen','Indoor pool':'basen','Pool':'basen','Hot tub':'jacuzzi','Spa':'spa','Beach access':'przy plaży','Fitness center':'siłownia','Air conditioning':'klimatyzacja','Restaurant':'restauracja','Bar':'bar','Kid-friendly':'dla dzieci','Pet-friendly':'ze zwierzętami','Airport shuttle':'transfer z lotniska','Accessible':'dla niepełnosprawnych'}
def amenities(text):
    """Udogodnienia z tekstu dla czytnikow ekranu: nazwa hotelu -> lista."""
    out={}
    for m in re.finditer(r'Amenities for ([^<]+?), an? [^<:]*?\.?: ([^<]+?)\s*<',text):
        out[html.unescape(m.group(1)).strip()]=[x.strip() for x in html.unescape(m.group(2)).split(',') if x.strip()]
    return out
def _breakfast(L):
    if 'Free breakfast' in L: return 'free'
    if 'Breakfast' in L or 'Breakfast ($)' in L: return 'paid'
    return None
COOK={'SOCS':'CAISHAgCEhJnd3NfMjAyNjEwMjktMF9SQzIaAmVuIAEaBgiA_LyaBg','CONSENT':'YES+cb.20260101-00-p0.en+FX+000'}
last={}
def fetch(q):
    """Jedno zapytanie. Zwraca (rekordy, udogodnienia) albo None."""
    if _blocked[0]>time.time(): return None
    url='https://www.google.com/travel/search?q='+quote(q)+'&hl=en&gl=pl&curr=PLN'
    from curl_cffi import requests
    with _l:
        w=_last[0]+2.5-time.time()
        if w>0: time.sleep(w)
        _last[0]=time.time()
        res=requests.get(url,impersonate='chrome',timeout=25,cookies=COOK)
    last.update(status=res.status_code,url=str(res.url)[:140],size=len(res.text),q=q,t=int(time.time()))
    if res.status_code==429: _blocked[0]=time.time()+600
    if res.status_code!=200: return None
    R=records(res.text)
    last['records']=len(R)
    return R,amenities(res.text)
def collect(d,q,ci,co,seen):
    f=fetch(q)
    if not f: return False
    for r in f[0]:
        h=parse(r,ci,co)
        if not h or h['name'] in seen: continue
        if geo.km(d['lat'],d['lon'],h['lat'],h['lon'])>90: continue
        k=net.fx(h['currency']);h['nightPln']=round(h['night']*k);h['totalPln']=round(h['total']*k)
        L=f[1].get(h['name'],[]);h['amen']=[AMEN[x] for x in L if x in AMEN];h['breakfast']=_breakfast(L)
        seen[h['name']]=h
    return True
def search(d,ci,co):
    """Szybka lista (jedno zapytanie), np. do szacunku noclegu. None = zrodlo nie odpowiedzialo."""
    k=f'gh5:{d["id"]}:{ci}:{co}'
    v,_=store.get(k)
    if v: return v
    n=(AREAS.get(d['id']) or [ALIAS.get(d['en'],d['en'])])[0];seen={}
    try: collect(d,query(n,ci,co),ci,co,seen)
    except Exception as e: log.warning('gh %s',str(e)[:120]);last['error']=str(e)[:160];return None
    out=list(seen.values())
    if out: store.put(k,out,4*3600)
    return out or None
# Wyspy i regiony: turysci mieszkaja w kurortach, nie w stolicy. Kazda nazwa sprawdzona w Photon (do 85 km od celu).
AREAS={'teneryfa':['Tenerife','Costa Adeje','Los Cristianos','Playa de las Americas','Puerto de la Cruz'],
'gran-canaria':['Gran Canaria','Maspalomas','Playa del Ingles','Puerto de Mogan'],
'lanzarote':['Puerto del Carmen','Costa Teguise','Playa Blanca'],
'fuerteventura':['Corralejo','Caleta de Fuste','Costa Calma','Morro Jable'],
'palma-de-mallorca':['Mallorca','Alcudia','Cala d\'Or','Magaluf','Cala Millor'],
'ibiza':['Sant Antoni de Portmany','Santa Eulalia del Rio','Playa d\'en Bossa'],
'madera-funchal':['Madeira','Canico'],
'kreta-heraklion':['Hersonissos','Malia'],
'kreta-chania':['Platanias','Agia Marina Chania'],
'rodos':['Rhodes island','Faliraki','Ialyssos','Lindos'],
'korfu':['Corfu island','Dassia','Kavos','Sidari'],
'kos':['Kos island','Kardamena','Tigaki','Kefalos'],
'zakynthos':['Zakynthos island','Laganas','Tsilivi'],
'kefalonia':['Lassi Kefalonia','Skala Kefalonia'],
'larnaka':['Ayia Napa','Protaras'],
'pafos':['Coral Bay Cyprus'],
'antalya':['Lara Antalya','Konyaalti','Kemer'],
'sardynia-olbia':['San Teodoro','Costa Smeralda'],
'sardynia-cagliari':['Villasimius','Pula Sardinia'],
'faro-algarve':['Albufeira','Vilamoura','Portimao','Lagos Portugal'],
'makarska':['Tucepi','Baska Voda'],
'chalkidiki':['Kassandra Halkidiki','Sithonia Halkidiki'],
'sloneczny-brzeg':['Nessebar','Sveti Vlas'],
'warna':['Golden Sands Bulgaria','Albena'],
'hurghada':['El Gouna','Sahl Hasheesh'],
'szarm-el-szejk':['Naama Bay'],
'malaga':['Torremolinos','Benalmadena','Marbella'],
'ajaccio-korsyka':['Porticcio'],
'nicea':['Antibes','Cannes']}
AREA_KINDS=['hotels in %s','cheap hotels in %s','vacation rentals in %s']
KINDS=['hotels in %s','vacation rentals in %s','hotels with free breakfast in %s','4 star hotels in %s','3 star hotels in %s','5 star hotels in %s','cheap hotels in %s','best hotels in %s city center','family hotels in %s','boutique hotels in %s','resorts in %s']
def deep(d,ci,co):
    """Duza lista: wiele rodzajow zapytan, bez duplikatow."""
    k=f'gh4:{d["id"]}:{ci}:{co}'
    v,_=store.get(k)
    if v: return v
    n=ALIAS.get(d['en'],d['en']);seen={h['name']:h for h in (store.get(f'gh5:{d["id"]}:{ci}:{co}')[0] or [])}
    a,b=dt.date.fromisoformat(ci),dt.date.fromisoformat(co)
    Q=[kind%n for kind in KINDS]+[kind%x for x in AREAS.get(d['id'],[]) for kind in AREA_KINDS]
    for i,qq in enumerate(Q):
        try:
            q=query('X',ci,co).replace('hotels in X',qq)
            if not collect(d,q,ci,co,seen): break
        except Exception as e:
            log.warning('gh %s',str(e)[:120]);last['error']=str(e)[:160];break
    out=list(seen.values())
    if len(out)>=5: store.put(k,out,4*3600)
    return out or None

def _v(n):
    o=b''
    while True:
        b=n&127;n>>=7
        if n: o+=bytes([b|128])
        else: return o+bytes([b])
def _ld(f,b): return bytes([f<<3|2])+_v(len(b))+b
def _vi(f,n): return bytes([f<<3])+_v(n)
def stay_token(ci,co):
    """Daty pobytu w formacie strony cen Google. Bez tego Google pokazuje oferty na jutro."""
    a=dt.date.fromisoformat(ci);b=dt.date.fromisoformat(co)
    day=lambda x:_vi(1,x.year)+_vi(2,x.month)+_vi(3,x.day)
    inner=_ld(1,day(a))+_ld(2,day(b))+_vi(3,(b-a).days)
    body=_ld(1,b'\x1a\x00')+_ld(2,_ld(2,inner)+_ld(6,b'\x08\x02'))
    raw=b'\x08\x01'+_ld(2,_ld(1,b'\x08\x03')+_ld(1,b'\x08\x03'))+_vi(2,0)+_ld(3,body)
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()
_OFF=re.compile(r'\[\["([^"]{2,60})",\d+,"(/travel/lodging/clk\?[^"]+)"')
_PR=re.compile(r'\["[^"]*PLN",null,([\d.]+),null,\d+\],\["[^"]*PLN",null,([\d.]+),null,\d+\]')
def parse_offers(t,ci,co):
    """Oferty serwisow: cena z podatkami za caly pobyt i link prosto do tego hotelu z datami."""
    t=t.replace('\\u003d','=').replace('\\u0026','&');n=(dt.date.fromisoformat(co)-dt.date.fromisoformat(ci)).days;out={}
    for m in _OFF.finditer(t):
        p=_PR.search(t[m.end():m.end()+1300])
        if not p or m[1] in out: continue
        night,total=float(p[1]),float(p[2])
        if n>1 and not(.9<total/(night*n)<1.15): continue
        q=m[2].split('pcurl=',1)
        if len(q)<2: continue
        link=unquote(q[1].split('&s=')[0])
        if link.startswith('http') and not re.search(r'202\d-\d\d-\d\d',link) and ci.replace('-','') not in link: pass
        d=re.search(r'(?:checkin|datefrom|checkIn)=(\d{4}-\d\d-\d\d)',link)
        if d and d[1]!=ci: continue
        out[m[1]]={'site':m[1],'night':round(night),'total':round(total),'url':link,'taxes':True}
    return sorted(out.values(),key=lambda x:x['total'])
def offers(key,ci,co):
    """Ceny z poszczegolnych serwisow dla jednego hotelu. None = strona nie odpowiedziala, [] = brak ofert."""
    k=f'ghof:{key}:{ci}:{co}'
    v,_=store.get(k)
    if v is not None: return v
    if _blocked[0]>time.time(): return None
    from curl_cffi import requests
    url=f'https://www.google.com/travel/hotels/entity/{key}/prices?ts={stay_token(ci,co)}&hl=en&gl=pl&curr=PLN'
    with _l:
        w=_last[0]+2.5-time.time()
        if w>0: time.sleep(w)
        _last[0]=time.time()
        res=requests.get(url,impersonate='chrome',timeout=25,cookies=COOK)
    if res.status_code==429: _blocked[0]=time.time()+600
    if res.status_code!=200: return None
    r=parse_offers(res.text,ci,co)
    store.put(k,r,3*3600)
    return r
