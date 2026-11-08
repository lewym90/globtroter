"""Grzeczne pobieranie stron biur: jawny identyfikator, odstep miedzy zapytaniami do jednego hosta, ponawianie."""
import gzip,os,ssl,threading,time,urllib.error,urllib.parse,urllib.request,zlib
UA='Mozilla/5.0 (compatible; Globtroter/1.0; non-commercial travel planner; +https://lewym90.github.io/globtroter/)'
GAP=float(os.environ.get('TOURS_GAP','1.2'))
_last={};_hl={};_ml=threading.Lock()
_CERTS=os.path.join(os.path.dirname(__file__),'certs')
def _ctx():
    c=ssl.create_default_context()
    if os.path.isdir(_CERTS):
        for f in sorted(os.listdir(_CERTS)):
            if f.endswith('.pem'): c.load_verify_locations(os.path.join(_CERTS,f))
    return c
CTX=_ctx()
class Blocked(Exception):
    """Strona odmowila (403, captcha). Nie obchodzimy tego."""
def _host_lock(h):
    with _ml: return _hl.setdefault(h,threading.Lock())
def get(url,data=None,headers=None,tries=3,timeout=30):
    """Zwraca tekst odpowiedzi. Miedzy zapytaniami do tego samego hosta czeka GAP sekund."""
    h=urllib.parse.urlsplit(url).hostname
    with _host_lock(h):
        w=_last.get(h,0)+GAP-time.time()
        if w>0: time.sleep(w)
        err=None
        try:
            for i in range(tries):
                try:
                    hd={'User-Agent':UA,'Accept-Language':'pl-PL,pl;q=0.9','Accept-Encoding':'gzip, deflate'};hd.update(headers or {})
                    req=urllib.request.Request(url,data=data.encode() if isinstance(data,str) else data,headers=hd)
                    with urllib.request.urlopen(req,timeout=timeout,context=CTX) as r:
                        b=r.read();enc=r.headers.get('Content-Encoding','')
                        if enc=='gzip': b=gzip.decompress(b)
                        elif enc=='deflate':
                            try: b=zlib.decompress(b)
                            except zlib.error: b=zlib.decompress(b,-15)
                        cs=r.headers.get_content_charset() or 'utf-8'
                        return b.decode(cs,errors='replace')
                except urllib.error.HTTPError as e:
                    err=e
                    if e.code in(401,403): raise Blocked(f'{h}: {e.code}')
                    if e.code not in(429,500,502,503,504): break
                except Blocked: raise
                except Exception as e: err=e
                time.sleep(2*(i+1))
            raise IOError(f'{h}: {err}')
        finally: _last[h]=time.time()
