import json,math,os,re,unicodedata
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n,d=None):
    p=os.path.join(ROOT,'data',n)
    if not os.path.exists(p):
        if d is not None: return d
        raise FileNotFoundError(p)
    return json.load(open(p,encoding='utf8'))
AIRPORTS={a['iata']:a for a in load('airports.json')}
DESTS=load('destinations.json',[])
BYID={d['id']:d for d in DESTS}
def km(a,b,c,d):
    p=math.radians;x=math.sin(p(c-a)/2)**2+math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2
    return 6371*2*math.asin(math.sqrt(x))
def slug(s):
    s=unicodedata.normalize('NFKD',s.replace('ł','l').replace('Ł','L'))
    return re.sub(r'[^a-z0-9]+','-',s.encode('ascii','ignore').decode().lower()).strip('-')
