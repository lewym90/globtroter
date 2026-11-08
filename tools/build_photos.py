#!/usr/bin/env python3
"""Zdjecia kierunkow z Wikimedia Commons (na podstawie Wikidata) i zestaw zdjec startowych."""
import io,json,os,subprocess,sys,urllib.parse
from PIL import Image,ImageOps
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A=json.load(open(R+'/data/attractions.json',encoding='utf8'));D=json.load(open(R+'/data/destinations.json',encoding='utf8'))
ONLY=set(filter(None,os.environ.get('ONLY','').split(',')))  # tylko te kierunki, reszta pliku bez zmian
out=json.load(open(R+'/data/photos.json',encoding='utf8')) if ONLY else {}
for d in D:
    if ONLY and d['id'] not in ONLY: continue
    L=[x for x in A.get(d['id'],[]) if x.get('img') and not x['img'].lower().endswith(('.svg','.tif','.tiff'))][:8]
    out[d['id']]=[{'f':urllib.parse.unquote(x['img']),'n':x['n'][0].upper()+x['n'][1:]} for x in L]
json.dump(out,open(R+'/data/photos.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
print(sum(1 for v in out.values() if v),'kierunkow ze zdjeciami',[d['name'] for d in D if not out[d['id']]][:20])
HERO=sys.argv[1:] 
