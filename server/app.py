#!/usr/bin/env python3
"""API Globtrotera: tylko 127.0.0.1, za Caddy. Bez kont i bez zapisu danych o uzytkownikach."""
import json,logging,os,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import flights,geo,hotels,net,plan,search,store
VERSION='1.3.1'
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
            if p in('/api/health','/zdrowie'): return self.out(200,{'ok':True,'version':VERSION,'google':flights.status(),'dests':len(geo.DESTS),'airports':len(geo.AIRPORTS)})
            if p=='/api/job':
                j=search.JOBS.get(q.get('id',''))
                if not j: return self.out(404,{'error':'Wyszukiwanie wygasło. Uruchom je jeszcze raz.'})
                return self.out(200,j)
            if p=='/api/hotels':
                return self.out(200,hotels.search(q['dest'],q['in'],q['out'],int(q.get('adults',2)),int(q.get('children',0)),int(q['budget']) if q.get('budget') else None,q.get('pref','balanced'),q.get('minRating',0),q.get('kind','all'),q.get('breakfast')=='1'))
            if p=='/api/diag':
                import ghotels
                d=geo.BYID.get(q.get('dest','hvar'));r=ghotels.search(d,q.get('in','2027-06-10'),q.get('out','2027-06-17'))
                return self.out(200,{'found':len(r or []),'last':ghotels.last})
            if p=='/api/fx': return self.out(200,{'USD':net.fx('USD'),'EUR':net.fx('EUR')})
            self.out(404,{'error':'Nie ma takiej ścieżki'})
        except ValueError as e: self.out(400,{'error':str(e)})
        except KeyError as e: self.out(400,{'error':f'Brak pola {e}'})
        except net.SourceDown as e: self.out(503,{'error':'Źródło danych chwilowo nie odpowiada. Spróbuj za chwilę.','retry':True})
        except Exception: logging.exception('GET');self.out(500,{'error':'Błąd serwera. Spróbuj ponownie.','retry':True})
    def do_POST(self):
        p=urlsplit(self.path).path.replace('/globtroter','',1)
        try:
            b=self.body()
            if p=='/api/search': return self.out(200,{'id':search.start(b)})
            if p=='/api/plan': return self.out(200,plan.build(b))
            if p=='/api/option': return self.out(200,search.recheck(b))
            self.out(404,{'error':'Nie ma takiej ścieżki'})
        except ValueError as e: self.out(400,{'error':str(e)})
        except KeyError as e: self.out(400,{'error':f'Brak pola {e}'})
        except flights.Unavailable: self.out(503,{'error':'Google Flights chwilowo nie odpowiada. Spróbuj za kilka minut.','retry':True})
        except Exception: logging.exception('POST');self.out(500,{'error':'Błąd serwera. Spróbuj ponownie.','retry':True})
def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    store.prune()
    port=int(os.environ.get('GLOBTROTER_PORT','8796'))
    ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
if __name__=='__main__': main()
