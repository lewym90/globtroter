"""Pobieranie z limitem czasu, ponawianiem i pamiecia. Bledy nigdy nie udaja pustych danych."""
import json,time,urllib.error,urllib.parse,urllib.request
import store
UA={'User-Agent':'Globtroter/1.0 (non-commercial travel planner)'}
class SourceDown(Exception): pass
class net_error(Exception): pass
def fetch_json(url,ttl=3600,tries=3,timeout=20,data=None,headers=None,cache=True):
    key='u:'+url+(('|'+data) if data else '')
    if cache:
        v,_=store.get(key)
        if v is not None: return v
    err=None
    for i in range(tries):
        try:
            h=dict(UA);h.update(headers or {})
            req=urllib.request.Request(url,data=data.encode() if data else None,headers=h)
            with urllib.request.urlopen(req,timeout=timeout) as r: v=json.loads(r.read())
            # Blad zapakowany w odpowiedz 200 nie moze trafic do pamieci jako prawdziwe dane
            if isinstance(v,dict) and v.get('error'): raise net_error(v['error'])
            if cache: store.put(key,v,ttl)
            return v
        except urllib.error.HTTPError as e:
            err=e
            if e.code not in(429,500,502,503,504): break
        except Exception as e: err=e
        time.sleep(1.5*(i+1))
    if cache:
        v,age=store.get_stale(key)
        if v is not None and age<7*86400 and not(isinstance(v,dict) and v.get('error')): return v
    raise SourceDown(f'{urllib.parse.urlsplit(url).hostname}: {err}')
_fx={}
def fx(code):
    """Sredni kurs NBP do PLN."""
    code=code.upper()
    if code=='PLN': return 1.0
    d=fetch_json(f'https://api.nbp.pl/api/exchangerates/rates/a/{code.lower()}/?format=json',ttl=6*3600)
    return float(d['rates'][0]['mid'])
