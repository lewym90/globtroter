#!/usr/bin/env python3
"""API Globtrotera: tylko 127.0.0.1, za Caddy. Bez kont i bez zapisu danych o uzytkownikach."""
import json,logging,os,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ai,flights,geo,hotels,net,plan,push,ryanair,search,store,trips
VERSION='1.7.0'
_hits={}
def limited(ip,kind,n,win):
    """Prosty limit zapytan na adres, zeby nikt nie zapchal bazy ani darmowego limitu AI."""
    t=time.time();k=(ip,kind);L=[x for x in _hits.get(k,[]) if t-x<win]
    if len(L)>=n: return True
    L.append(t);_hits[k]=L;return False
ALLOW={'https://lewym90.github.io','http://localhost:8000','http://127.0.0.1:8000'}
class H(BaseHTTPRequestHandler):
    server_version='Globtroter'
    def log_message(self,*a): pass
    def cors(self):
        o=self.headers.get('Origin')
        if o in ALLOW: self.send_header('Access-Control-Allow-Origin',o);self.send_header('Vary','Origin')
    def out(self,code,v):
        b=json.dumps(v,ensure_ascii=False).encode();self.send_response(code);self.cors()
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
    def do_OPTIONS(self):
        self.send_response(204);self.cors();self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Access-Control-Max-Age','86400');self.end_headers()
    def body(self):
        n=int(self.headers.get('Content-Length') or 0)
        if n>500000: raise ValueError('Za duże zapytanie')
        return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        u=urlsplit(self.path);p=u.path.replace('/globtroter','',1);q={k:v[0] for k,v in parse_qs(u.query).items()}
        try:
            if p in('/api/health','/zdrowie'): return self.out(200,{'ok':True,'version':VERSION,'google':flights.status(),'ryanair':ryanair.status(),'ai':ai.ready(),'pushErr':push._err[0],'dests':len(geo.DESTS),'airports':len(geo.AIRPORTS)})
            if p=='/api/job':
                j=search.JOBS.get(q.get('id',''))
                if not j: return self.out(404,{'error':'Wyszukiwanie wygasło. Uruchom je jeszcze raz.'})
                return self.out(200,j)
            if p=='/api/hotel/offers': return self.out(200,hotels.offers(q.get('key'),q.get('in'),q.get('out'),q.get('rooms',1)))
            if p=='/api/hotels':
                return self.out(200,hotels.search(q['dest'],q['in'],q['out'],int(q.get('adults',2)),int(q.get('children',0)),int(q['budget']) if q.get('budget') else None,q.get('pref','balanced'),q.get('minRating',0),q.get('kind','all'),q.get('breakfast')=='1'))
            if p=='/api/diag':
                import ghotels
                d=geo.BYID.get(q.get('dest','hvar'));r=ghotels.search(d,q.get('in','2027-06-10'),q.get('out','2027-06-17'))
                return self.out(200,{'found':len(r or []),'last':ghotels.last})
            if p=='/api/ai/diag': return self.out(200,ai.diag())
            if p=='/api/ryanair': return self.out(200,{'routes':len(ryanair.routes(q.get('o','KRK'))),'may':len(ryanair.month(q.get('o','KRK'),q.get('d','BCN'),q.get('ym','2027-05')))})
            if p=='/api/fx':
                if q.get('c'):
                    if not q['c'].isalpha() or len(q['c'])!=3: raise ValueError('Zły kod waluty')
                    return self.out(200,{'code':q['c'].upper(),'rate':net.fx(q['c'])})
                return self.out(200,{'USD':net.fx('USD'),'EUR':net.fx('EUR')})
            if p=='/api/explore':
                d=geo.BYID.get(q.get('dest',''))
                if not d: raise ValueError('Nie znam tego miejsca')
                return self.out(200,plan.explore(d))
            if p=='/api/watch': return self.out(200,{'list':push.watch_list(q.get('device',''))})
            if p=='/api/trip': return self.out(200,trips.get(q.get('k','')))
            if p=='/api/push/key': return self.out(200,{'key':push.public()})
            self.out(404,{'error':'Nie ma takiej ścieżki'})
        except ValueError as e: self.out(400,{'error':str(e)})
        except KeyError as e: self.out(400,{'error':f'Brak pola {e}'})
        except trips.Denied: self.out(404,{'error':'Ten link do wyjazdu jest nieaktualny.'})
        except net.SourceDown as e: self.out(503,{'error':'Źródło danych chwilowo nie odpowiada. Spróbuj za chwilę.','retry':True})
        except Exception: logging.exception('GET');self.out(500,{'error':'Błąd serwera. Spróbuj ponownie.','retry':True})
    def do_POST(self):
        p=urlsplit(self.path).path.replace('/globtroter','',1)
        try:
            b=self.body()
            if p=='/api/search': return self.out(200,{'id':search.start(b)})
            if p=='/api/plan': return self.out(200,plan.build(b))
            ip=(self.headers.get('X-Forwarded-For') or self.client_address[0]).split(',')[0].strip()
            if p=='/api/trip/new':
                if limited(ip,'new',40,86400): return self.out(429,{'error':'Za dużo nowych wyjazdów dziś. Spróbuj jutro.'})
                return self.out(200,trips.create(b.get('plan'),b.get('s')))
            if p=='/api/trip/sync': return self.out(200,trips.sync(b.get('k',''),b.get('s'),b.get('device'),b.get('note')))
            if p=='/api/trip/del': trips.delete(b.get('k',''));return self.out(200,{'ok':True})
            if p=='/api/push/sub': return self.out(200,{'trips':push.subscribe(b.get('device'),b.get('subscription'),b.get('keys'))})
            if p=='/api/push/off': push.unsubscribe(b.get('device',''));return self.out(200,{'ok':True})
            if p=='/api/push/test':
                if limited(ip,'test',10,3600): return self.out(429,{'error':'Za dużo prób. Spróbuj za godzinę.'})
                push.test(b.get('device',''));return self.out(200,{'ok':True})
            if p=='/api/ai/parse':
                if limited(ip,'ai',80,3600): return self.out(429,{'error':'Asystent ma chwilę przerwy. Spróbuj za kilkanaście minut.'})
                return self.out(200,ai.parse(b.get('text','')))
            if p=='/api/ai/chat':
                if limited(ip,'ai',80,3600): return self.out(429,{'error':'Asystent ma chwilę przerwy. Spróbuj za kilkanaście minut.'})
                if not ai.ready(): return self.out(503,{'error':'Asystent nie ma jeszcze klucza na serwerze.'})
                d=geo.BYID.get(b.get('dest',''));return self.out(200,ai.chat(b,plan.ATTR.get(d['id'],[]) if d else []))
            if p=='/api/route': return self.out(200,plan.route(b))
            if p=='/api/plan/manual': return self.out(200,plan.manual(b))
            if p=='/api/car':
                return self.out(200,plan.car_route(float(b['lat']),float(b['lon']),float(b['la']),float(b['lo']),b.get('transport')))
            if p=='/api/watch/add': return self.out(200,{'id':push.watch_add(b.get('device',''),b['from'],b['to'],b['ym'],b['nights'],b.get('name',''),b['price'])})
            if p=='/api/watch/del': push.watch_del(b.get('device',''),b.get('id',''));return self.out(200,{'ok':True})
            if p=='/api/calendar': return self.out(200,search.month_grid(b))
            if p=='/api/option': return self.out(200,search.recheck(b))
            self.out(404,{'error':'Nie ma takiej ścieżki'})
        except ValueError as e: self.out(400,{'error':str(e)})
        except KeyError as e: self.out(400,{'error':f'Brak pola {e}'})
        except trips.Denied: self.out(404,{'error':'Ten link do wyjazdu jest nieaktualny.'})
        except PermissionError as e: self.out(403,{'error':str(e)})
        except net.SourceDown: self.out(503,{'error':'Asystent chwilowo nie odpowiada. Spróbuj za chwilę.','retry':True})
        except flights.Unavailable: self.out(503,{'error':'Google Flights chwilowo nie odpowiada. Spróbuj za kilka minut.','retry':True})
        except Exception: logging.exception('POST');self.out(500,{'error':'Błąd serwera. Spróbuj ponownie.','retry':True})
def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    store.prune()
    push.start()
    port=int(os.environ.get('GLOBTROTER_PORT','8796'))
    ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
if __name__=='__main__': main()
