# Kafelki na starcie z prawdziwych granic (Natural Earth 1:50m przez world-atlas). Uzycie: python3 tools/tile_maps.py <katalog z map/c50.json> <katalog wyjsciowy>
import json,math,sys
from PIL import Image,ImageDraw,ImageFilter,ImageChops
SP=sys.argv[1];OUT=sys.argv[2]
W=json.load(open(SP+'/map/c50.json'));tr=W['transform']
def arc(i):
    x=y=0;pts=[]
    for dx,dy in W['arcs'][i if i>=0 else ~i]:
        x+=dx;y+=dy;pts.append((x*tr['scale'][0]+tr['translate'][0],y*tr['scale'][1]+tr['translate'][1]))
    return pts if i>=0 else pts[::-1]
C={}
for g in W['objects']['countries']['geometries']:
    if g['type'] not in('Polygon','MultiPolygon'): continue
    polys=g['arcs'] if g['type']=='MultiPolygon' else [g['arcs']]
    C[g['properties']['name']]=[[sum((arc(i) for i in ring),[]) for ring in p] for p in polys]
EUROPE={'Albania','Andorra','Austria','Belarus','Belgium','Bosnia and Herz.','Bulgaria','Croatia','Cyprus','Czechia','Denmark','Estonia','Finland','France','Germany','Greece','Hungary','Iceland','Ireland','Italy','Kosovo','Latvia','Liechtenstein','Lithuania','Luxembourg','Malta','Moldova','Monaco','Montenegro','Netherlands','North Macedonia','Norway','Portugal','Romania','San Marino','Serbia','Slovakia','Slovenia','Spain','Sweden','Switzerland','United Kingdom','Vatican','Faeroe Is.','Åland','Guernsey','Jersey','Isle of Man','Gibraltar','Turkey','Georgia','Ukraine','Russia'}
WORLD={'Egypt','Tunisia','Morocco','Cabo Verde','United Arab Emirates','Jordan','Turkey','Georgia'}
S=2;N=720*S
def proj(lon0,lat0,scale):
    # Lambert azimuthal equal-area: wierne ksztalty dla calego kontynentu
    l0=math.radians(lon0);p0=math.radians(lat0)
    def f(lon,lat):
        l=math.radians(lon);p=math.radians(lat)
        k=1+math.sin(p0)*math.sin(p)+math.cos(p0)*math.cos(p)*math.cos(l-l0)
        if k<=1e-6: return None
        k=math.sqrt(2/k)
        x=k*math.cos(p)*math.sin(l-l0);y=k*(math.cos(p0)*math.sin(p)-math.sin(p0)*math.cos(p)*math.cos(l-l0))
        return (N/2+x*scale*N,N*0.42-y*scale*N)
    return f
def bg():
    im=Image.new('RGB',(N,N),(3,18,47));d=ImageDraw.Draw(im)
    for r in range(N,0,-6):
        t=r/N;c=(int(3+16*(1-t)**1.6),int(18+40*(1-t)**1.6),int(47+80*(1-t)**1.6))
        d.ellipse((N/2-r,N*0.40-r*0.85,N/2+r,N*0.40+r*0.85),fill=c)
    # delikatna siatka poludnikow i rownoleznikow
    return im
def grid(im,f):
    d=ImageDraw.Draw(im,'RGBA')
    for lon in range(-60,121,10):
        pts=[f(lon,la) for la in range(-60,85)];pts=[p for p in pts if p]
        if len(pts)>1: d.line(pts,fill=(120,150,220,26),width=S)
    for lat in range(-60,85,10):
        pts=[f(lo,lat) for lo in range(-60,121)];pts=[p for p in pts if p]
        if len(pts)>1: d.line(pts,fill=(120,150,220,26),width=S)
def poly(d,f,name,fill,outline=None,w=1):
    for p in C.get(name,[]):
        ring=[f(x,y) for x,y in p[0]];ring=[q for q in ring if q]
        if len(ring)>2: d.polygon(ring,fill=fill,outline=outline,width=w*S if outline else 0)
def render(lon0,lat0,scale,hl,name,pins=()):
    f=proj(lon0,lat0,scale);im=bg();grid(im,f)
    land=Image.new('RGBA',(N,N),(0,0,0,0));d=ImageDraw.Draw(land)
    for n in C:
        if n in hl: continue
        poly(d,f,n,(26,52,112,255),(58,88,160,255),1)
    im.paste(land,(0,0),land)
    # zlota poswiata pod wyroznionym obszarem
    mask=Image.new('L',(N,N),0);dm=ImageDraw.Draw(mask)
    for n in hl:
        for p in C.get(n,[]):
            ring=[f(x,y) for x,y in p[0]];ring=[q for q in ring if q]
            if len(ring)>2: dm.polygon(ring,fill=255)
    glow=mask.filter(ImageFilter.GaussianBlur(28*S))
    gl=Image.new('RGB',(N,N),(255,170,40));im=Image.composite(gl,im,glow.point(lambda v:int(v*.55)))
    # zloty gradient od gory do dolu
    gold=Image.new('RGB',(N,N));gd=ImageDraw.Draw(gold)
    for y in range(N):
        t=y/N;gd.line([(0,y),(N,y)],fill=(int(255-20*t),int(214-70*t),int(110-80*t)))
    im=Image.composite(gold,im,mask)
    d=ImageDraw.Draw(im)
    for n in hl:
        for p in C.get(n,[]):
            ring=[f(x,y) for x,y in p[0]];ring=[q for q in ring if q]
            if len(ring)>2: d.line(ring+[ring[0]],fill=(255,236,190),width=max(1,S))
    for lon,lat in pins:
        x,y=f(lon,lat);r=7*S;d.ellipse((x-r,y-r,x+r,y+r),fill=(255,255,255),outline=(3,18,47),width=2*S)
    # dol przechodzi w granat jak inne grafiki
    fade=Image.new('L',(N,N),0);fd=ImageDraw.Draw(fade)
    for y in range(int(N*.72),N): fd.line([(0,y),(N,y)],fill=int(255*min(1,(y-N*.72)/(N*.22))))
    im=Image.composite(Image.new('RGB',(N,N),(3,18,47)),im,fade)
    im=im.resize((720,720),Image.LANCZOS);im.save(OUT+'/'+name,quality=86,optimize=True,progressive=True)
render(19.3,52.0,1.55,{'Poland'},'polska.jpg')
render(14,51,0.66,(EUROPE-{'Russia','Turkey','Georgia'})|{'Poland'},'europa.jpg')
render(22,29,0.56,WORLD,'swiat.jpg')
print('ok')
