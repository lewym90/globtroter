#!/usr/bin/env python3
"""Wczytuje opisy z dokumentu. Istniejace atrakcje dostaja opis i zrodlo, a ich wspolrzedne zostaja.
Nowe wchodza tylko z pewnym polozeniem. Kazde odrzucenie jest liczone w raporcie."""
import collections,json,math,os,re,sys,unicodedata
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND={'muzeum':'museum','świątynia':'church','pałac':'palace','zamek':'castle','ruiny':'ruins','pomnik':'monument','plac':'square','ulica':'street','park':'park','przyroda':'nature','plaża':'beach','most':'bridge','teatr':'theatre','zoo':'zoo','targ':'food','zabytek':'sight'}
LIMIT={'Teneryfa':70,'Gran Canaria':70,'Fuerteventura':70,'Lanzarote':60,'Ibiza':50,'Palma de Mallorca':80,'Madera (Funchal)':60,'Kreta (Heraklion)':80,'Kreta (Chania)':80,'Korfu':70,'Rodos':70,'Kefalonia':60,'Zakynthos':50,'Sardynia (Cagliari)':80,'Sardynia (Olbia)':80,'Ajaccio (Korsyka)':80,'Ponta Delgada (Azory)':70}
def norm(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',str(s).replace('ł','l').replace('Ł','l').lower()).encode('ascii','ignore').decode())
def km(a,b,c,d):
    p=math.radians;x=math.sin(p(c-a)/2)**2+math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2;return 6371*2*math.asin(math.sqrt(x))
def coord(s):
    m=re.fullmatch(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)',s or '')
    return (float(m[1]),float(m[2])) if m else None
def run(R,A,D):
    S=collections.Counter();bad=[]
    near={}
    for r in R:
        c,pl,orig,k,co,de,url=r;d=D[c];L=A.setdefault(d['id'],[]);p=coord(co)
        de=re.sub(r'\s+',' ',de).strip()
        if re.search(r'[Ww]edług Wikipedii|\bWikipedi',de): S['odrzucone: powolanie na Wikipedie']+=1;bad.append(r);continue
        if not url.startswith('http') or not 90<=len(de)<=260: S['odrzucone: format']+=1;bad.append(r);continue
        ns={norm(pl),norm(orig)}
        h=next((x for x in L if norm(x['n']) in ns),None)
        if h is None and p:
            h=next((x for x in L if x.get('t')==KIND.get(k) and km(p[0],p[1],x['lat'],x['lon'])<.12),None)
        if h is not None:
            S['polaczone z istniejaca']+=1
            if not h.get('d'): h['d']=de;h['src']=url;S['nowy opis istniejacej']+=1
            continue
        if not p: S['odrzucone nowe: brak wspolrzednych']+=1;bad.append(r);continue
        if km(d['lat'],d['lon'],*p)>LIMIT.get(c,45): S['odrzucone nowe: za daleko']+=1;bad.append(r);continue
        key=(d['id'],co)
        if key in near: S['odrzucone nowe: ta sama pozycja']+=1;bad.append(r);continue
        near[key]=1;L.append({'n':pl,'lat':p[0],'lon':p[1],'l':3,'t':KIND.get(k,'sight'),'q':'doc'+norm(pl)[:24],'img':None,'web':None,'h':None,'d':de,'src':url});S['nowe atrakcje']+=1
    return S,bad
if __name__=='__main__':
    R=json.load(open(sys.argv[1],encoding='utf8'));P=ROOT+'/data/attractions.json'
    A=json.load(open(P,encoding='utf8'));D={d['name']:d for d in json.load(open(ROOT+'/data/destinations.json',encoding='utf8'))}
    S,bad=run(R,A,D)
    for k,v in S.most_common():print(k,v)
    json.dump(A,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
    json.dump(bad,open(sys.argv[2],'w',encoding='utf8'),ensure_ascii=False,indent=0)
