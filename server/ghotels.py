"""Drugie zrodlo hoteli: strona Google Hotels. Dane sa wbudowane w strone jako struktura JSON.
Zwraca tylko rekordy zgodne z podanymi datami i lezace przy celu. Awaria to None, nigdy zgadywanie."""
import datetime as dt,json,logging,re,threading,time
from urllib.parse import quote
import geo,net,store
log=logging.getLogger('ghotels')
MONTHS='January February March April May June July August September October November December'.split()
ALIAS={'Thira':'Santorini','Arrecife':'Lanzarote','Puerto del Rosario':'Fuerteventura','Faro':'Algarve','Argostoli':'Kefalonia','Sarandë':'Saranda','Valletta':'Malta','Chamonix-Mont-Blanc':'Chamonix','Funchal':'Madeira','Ponta Delgada':'Azores Sao Miguel'}
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
def search(d,ci,co):
    """Lista hoteli dla celu i dat, ceny w PLN. None = zrodlo nie odpowiedzialo."""
    k=f'gh:{d["id"]}:{ci}:{co}'
    v,_=store.get(k)
    if v is not None: return v
    if _blocked[0]>time.time(): return None
    name=ALIAS.get(d['en'],d['en'])
    url='https://www.google.com/travel/search?q='+quote(query(name,ci,co))+'&hl=en&gl=pl&curr=PLN'
    try:
        from curl_cffi import requests
        with _l:
            w=_last[0]+3-time.time()
            if w>0: time.sleep(w)
            _last[0]=time.time()
            res=requests.get(url,impersonate='chrome',timeout=25)
        if res.status_code==429: _blocked[0]=time.time()+600
        if res.status_code!=200: log.warning('gh %s',res.status_code);return None
        out=[]
        for r in records(res.text):
            h=parse(r,ci,co)
            if not h: continue
            if geo.km(d['lat'],d['lon'],h['lat'],h['lon'])>90: continue
            k2=net.fx(h['currency'])
            h['nightPln']=round(h['night']*k2);h['totalPln']=round(h['total']*k2)
            out.append(h)
        seen={};[seen.setdefault(h['name'],h) for h in out];out=list(seen.values())
        if out: store.put(k,out,4*3600)
        return out or None
    except Exception as e:
        log.warning('gh blad %s',str(e)[:120]);return None
