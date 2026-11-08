"""Rainbow (r.pl): oferty ze stron miesiecznych /<kraj>/wakacje-<miesiac>.

Strona jest renderowana na serwerze (Nuxt) i ma oferty w <script id="__NUXT_DATA__"> (stan '$sszukajBloczki').
Jeden blok = jeden hotel/wycieczka z najtansza oferta, 10 na strone (?strona=N), sortowanie domyslne
'cena-asc' (od najnizszej ceny).

Sprawdzone na zywo 2026-11:
- Strona miesiaca obejmuje zawsze NAJBLIZSZE wystapienie miesiaca: w listopadzie 2026 'wakacje-listopad' to
  08-30.11.2026, 'wakacje-pazdziernik' to 10.2027. Roku nie da sie wybrac (parametry rok/data nie dzialaja).
  Zakres dat czytamy z danych strony (Filter.Atrybuty.TerminWyjazdu); jesli to nie ten rok, zwracamy pusta
  liste z complete=False. Dodatkowo kazda oferte sprawdzamy po dacie wylotu.
- ?wybraneSkad=<IATA>[,<IATA>] filtruje lotnisko wylotu (cena i kolejnosc lotnisk w bloku dotycza wtedy
  tego lotniska). Gdy nic nie pasuje, strona podaje liczbe 0, ale i tak pokazuje bloki zastepcze - wtedy
  zwracamy zero ofert. Warszawa = WAW + WMI (tak grupuje Rainbow na stronach /wyloty-z-warszawy).
  Szczytno-Szymany to u Rainbow SZY (obecnie bez ofert). Radomia Rainbow nie zna.
- Data powrotu = wylot + liczba nocy (sprawdzone na stronach ofert: "01.05.2027 - 08.05.2027" dla 7 nocy).
- Strona miesiaca zawiera tez wycieczki objazdowe (TypWycieczki 'objazd', 'objazd + wypoczynek') -> kind 'objazd'.
- robots.txt (User-agent *) zabrania /szukaj?, /*/szukaj?, /api, /rezerwacja, /dodajopinie, /opinie/dodaj,
  /bilety-czarterowe/szukaj|rezerwacja. Pobieramy tylko strony miesieczne.

Ceny: lista jest pobierana z cena=sum, wiec 'total' to dokladna cena za 2 doroslych
(strona oferty: "Cena razem"), a 'ppp' = total/2 zaokraglone jak na stronie oferty (cena za osobe). Rainbow nie dolicza osobno TFG/TFP (sa w cenie).
Ocena klientow: Rainbow podaje w skali 0-6; przeliczamy na 0-10 (x/6*10).
"""
import calendar,datetime as dt,json,re,urllib.parse as up
from . import http

NAME='Rainbow'
SITE='https://r.pl'
OP='rainbow'
# Zweryfikowane 2026-11 (strona /<slug>/wakacje-czerwiec ma Lokalizacje_HoteloProdukt tego kraju; nieznany slug = 404).
COUNTRIES={'ES':'hiszpania','GR':'grecja','TR':'turcja','EG':'egipt','BG':'bulgaria','HR':'chorwacja','IT':'wlochy',
    'PT':'portugalia','CY':'cypr','AL':'albania','TN':'tunezja','MA':'maroko','MT':'malta','ME':'czarnogora'}
ORIGINS={'WAW':['WAW','WMI'],'KTW':['KTW'],'KRK':['KRK'],'GDN':['GDN'],'WRO':['WRO'],'POZ':['POZ'],'RZE':['RZE'],
    'LUZ':['LUZ'],'BZG':['BZG'],'LCJ':['LCJ'],'SZZ':['SZZ'],'OSZ':['SZY']}
IATA={c:k for k,v in ORIGINS.items() for c in v}       # kod Rainbow -> nasz kod
MONTHS=['styczen','luty','marzec','kwiecien','maj','czerwiec','lipiec','sierpien','wrzesien','pazdziernik','listopad','grudzien']
BOARD={'all inclusive':'All inclusive','sniadania':'Śniadania','2 posilki':'Śniadania i obiadokolacje',
    '3 posilki':'Pełne wyżywienie','bez wyzywienia':'Bez wyżywienia'}
PER_PAGE=10

def _ascii(t):
    import unicodedata
    return unicodedata.normalize('NFKD',t.replace('ł','l').replace('Ł','L')).encode('ascii','ignore').decode().lower().strip()
def board(t):
    return BOARD.get(_ascii(t),t) if t else None

def list_url(cc,ym,origin,page=1):
    m=int(ym[5:7]);q={'cena':'sum'}      # ceny za wszystkich (dokladna suma; cena za osobe na liscie jest zaokraglona)
    if origin: q['wybraneSkad']=','.join(ORIGINS[origin])
    if page>1: q['strona']=page
    return f"{SITE}/{COUNTRIES[cc]}/wakacje-{MONTHS[m-1]}"+('?'+up.urlencode(q,safe=',') if q else '')

_WRAP={'Reactive','ShallowReactive','Ref','ShallowRef','EmptyRef','EmptyShallowRef','NuxtError'}
def _state(text,keys):
    """Wybrane klucze stanu Nuxt z __NUXT_DATA__ (format devalue: tablica, odwolania przez indeksy)."""
    m=re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>',text,re.S)
    if not m: raise ValueError('rainbow: brak __NUXT_DATA__')
    d=json.loads(m.group(1));memo={}
    def r(i,depth=0):
        if not isinstance(i,int) or isinstance(i,bool): return i
        if i<0: return None
        if i in memo: return memo[i]
        if depth>400: raise ValueError('rainbow: za gleboki __NUXT_DATA__')
        v=d[i]
        if isinstance(v,list):
            if v and isinstance(v[0],str):
                if v[0] in _WRAP: out=r(v[1],depth+1) if len(v)>1 else None;memo[i]=out;return out
                if v[0] in('Date','LocalDate'): memo[i]=v[1];return v[1]
                if v[0]=='Set': out=[r(x,depth+1) for x in v[1:]];memo[i]=out;return out
                if v[0]=='null': memo[i]=None;return None
            out=[];memo[i]=out;out.extend(r(x,depth+1) for x in v);return out
        if isinstance(v,dict):
            out={};memo[i]=out
            for k,x in v.items(): out[k]=r(x,depth+1)
            return out
        memo[i]=v;return v
    root=d[0];root=d[root[1]] if isinstance(root,list) else root      # ["Reactive",n] albo slownik
    st=d[root['state']] if 'state' in root else {}
    while isinstance(st,list) and st and st[0] in _WRAP: st=d[st[1]]
    return {k:(r(st[k]) if k in st else None) for k in keys}

def _info(text):
    s=_state(text,['$sszukajBloczki','$sszukajOferty','$sresponseOfertyCount','$smiddlewareRouteInfo','$spageValue'])
    rng=(((s['$smiddlewareRouteInfo'] or {}).get('Filter') or {}).get('Atrybuty') or {}).get('TerminWyjazdu')
    return s,rng

def total_count(text):
    return _info(text)[0]['$sresponseOfertyCount']

def month_range(text):
    """(od, do) dat wylotu, ktore obejmuje strona miesiaca, np. ['2027-05-01','2027-05-31']."""
    return _info(text)[1]

def parse(text,cc=None,ym=None,origin=None):
    """Oferty z HTML strony miesiaca. Filtruje: lot samolotem, wylot w miesiacu ym, z lotniska origin, kraj cc."""
    return _parse(_info(text)[0],cc,ym,origin)

def _parse(s,cc,ym,origin):
    if not s['$sresponseOfertyCount']: return []        # 0 = brak wynikow, bloki na stronie sa zastepcze
    oferty={o.get('Id'):o for o in s['$sszukajOferty'] or []}
    out=[]
    for b in s['$sszukajBloczki'] or []:
        bi=b.get('BazoweInformacje') or {}
        dep=(b.get('TerminWyjazdu') or '')[:10]
        if not dep or (ym and dep[:7]!=ym): continue
        stops=[p for p in b.get('Przystanki') or [] if p.get('CzySamolot')]
        if not stops: continue                          # dojazd wlasny / autokar
        codes=[IATA.get(p.get('Iata'),p.get('Iata')) for p in stops]
        if origin and codes[0]!=origin: continue        # przy wybraneSkad pierwsze lotnisko to wybrane
        if cc and COUNTRIES.get(cc) and COUNTRIES[cc] not in [_ascii(x).replace(' ','-') for x in bi.get('Panstwa') or []]: continue
        cena=b.get('Cena') or {};c=cena.get('Cena')
        if not c: continue
        n=len(bi.get('DatyUrodzenia') or [])or 2
        if cena.get('CzyCenaZaOsobe'): ppp=int(round(c));tot=ppp*n
        else: tot=int(round(c));ppp=int(tot/n+0.5)    # strona oferty pokazuje za osobe zaokraglone w gore przy ,5
        wz=b.get('Wyzywienia') or [];brd=None
        kl=((oferty.get(b.get('Klucz')) or {}).get('PodzialNaPokoje') or {}).get('Klienci') or []
        if kl:
            w=[x for x in wz if kl[0].get('TypWyzywieniaId') in (x.get('UslugiId') or [])]
            if w: brd=w[0].get('Nazwa')
        if not brd and len(wz)==1: brd=wz[0].get('Nazwa')
        nights=bi.get('LiczbaNocy')
        ret=(dt.date.fromisoformat(dep)+dt.timedelta(nights)).isoformat() if nights is not None else None
        typ=(bi.get('TypWycieczki') or '').lower()
        kind='objazd' if ('objazd' in typ or 'rejs' in typ) else 'wypoczynek'
        loc=bi.get('Lokalizacje') or '';place=loc.split(': ',1)[1] if ': ' in loc else loc
        oc=b.get('Ocena') or {}
        out.append({'op':OP,'name':bi.get('NazwaHoteluWWW') or bi.get('OfertaNazwa'),'stars':bi.get('GwiazdkiHotelu') or None,
            'place':place,'dep':dep,'ret':ret,'nights':nights,'board':board(brd),'from':codes[0],
            'ppp':ppp,'adults':n,'total':tot,
            'rating':(round(oc['Ocena']/6*10,1) if oc.get('Ocena') and oc.get('CzyPokazywac',True) else None),
            'kind':kind,'url':SITE+bi.get('OfertaUrl','').replace('czyCenaZaWszystkich=1','czyCenaZaWszystkich=0')})
    return out

def search(cc,ym,origin=None,limit_pages=40):
    if cc not in COUNTRIES: return {'offers':[],'total':0,'complete':True,'url':SITE}
    first=list_url(cc,ym,origin if origin in ORIGINS else None)
    if origin and origin not in ORIGINS: return {'offers':[],'total':0,'complete':True,'url':first}
    offers=[];seen=set();total=None;complete=False
    for p in range(1,limit_pages+1):
        s,rng=_info(http.get(list_url(cc,ym,origin,p)))
        if p==1:
            total=s['$sresponseOfertyCount']
            if not rng or rng[0][:7]!=ym:
                # strona pokazuje inny rok tego miesiaca (np. 2026-11 zamiast 2027-11) - nie umiemy pobrac
                return {'offers':[],'total':None,'complete':False,'url':first}
            if not total: return {'offers':[],'total':0,'complete':True,'url':first}
        rows=_parse(s,cc,ym,origin)
        for o in rows:
            if o['url'] not in seen: seen.add(o['url']);offers.append(o)
        n=len(s['$sszukajBloczki'] or [])
        if n<PER_PAGE or p*PER_PAGE>=total: complete=True;break
    offers.sort(key=lambda o:o['ppp'])
    return {'offers':offers,'total':total,'complete':complete,'url':first}
