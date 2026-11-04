#!/usr/bin/env python3
"""Atrakcje z Wikivoyage: miejsca polecane przez podroznych, z opisem i czesto z godzinami. Tylko wpisy ze wspolrzednymi."""
import hashlib,json,os,re,sys,time,unicodedata,urllib.error,urllib.parse,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=ROOT+'/data/attractions.json'
def raw(t):
    u='https://en.wikivoyage.org/w/index.php?action=raw&title='+urllib.parse.quote(t.replace(' ','_'))
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Globtroter/1.0 (non-commercial; github.com/lewym90/globtroter)'}),timeout=30).read().decode('utf8')
        except urllib.error.HTTPError as e:
            if e.code==404: return ''
            time.sleep(10*(i+1))
        except Exception: time.sleep(5)
    return ''
def field(b,k):
    m=re.search(r'\|\s*'+k+r'\s*=\s*(.*?)(?=\n?\s*\|\s*[a-zA-Z_]+\s*=|\Z)',b,re.S)
    return re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]',r'\1',m[1]).replace("'''",'').replace("''",'').strip() if m else ''
def kind(tag,n):
    x=n.lower()
    for k,w in (('church','church|cathedral|basilica|chapel|monastery|mosque|abbey|synagogue'),('museum','museum|gallery|pinacoteca'),('castle','castle|fortress|fort |citadel'),('palace','palace|palazzo'),('ruins','ruin|roman|archaeolog|amphitheat'),('park','park|garden'),('beach','beach|plage|playa|spiaggia'),('square','square|piazza|plaza'),('theatre','theatre|theater|opera')):
        if re.search(w,x): return k
    return 'sight' if tag=='see' else 'nature'
def norm(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode())
def main():
    ds=json.load(open(ROOT+'/data/destinations.json',encoding='utf8'));A=json.load(open(P,encoding='utf8'));t0=time.time();tot=0
    for d in ds:
        if time.time()-t0>1500: break
        t=raw(d['en'])
        L=A.setdefault(d['id'],[]);have={norm(x['n']) for x in L};n=0
        for m in re.finditer(r'\{\{(see|do)\s*\n?\|(.*?)\n?\}\}',t,re.S|re.I):
            b='|'+m[2];nm=field(b,'name');la=field(b,'lat');lo=field(b,'long')
            if not nm or norm(nm) in have or len(nm)>80: continue
            try: la,lo=float(la),float(lo)
            except ValueError: continue
            if abs(la-d['lat'])>.6 or abs(lo-d['lon'])>.8: continue
            de=re.sub(r'\s+',' ',field(b,'content'))[:300];w=field(b,'url');h=field(b,'hours')[:120]
            have.add(norm(nm));L.append({'n':nm,'lat':round(la,5),'lon':round(lo,5),'l':3,'t':kind(m[1].lower(),nm),'q':field(b,'wikidata') or 'wv'+hashlib.sha1(nm.encode()).hexdigest()[:8],'img':None,'web':w or None,'h':h or None,'de':de or None});n+=1
        tot+=n;print(d['name'],n,len(L),flush=True);time.sleep(1)
    json.dump(A,open(P,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'));print('razem',tot)
if __name__=='__main__': main()
