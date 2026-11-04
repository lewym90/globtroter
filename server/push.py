"""Powiadomienia z serwera (Web Push): dochodza przy zamknietej aplikacji. Tresc liczona z aktualnego planu w chwili wysylki."""
import base64,datetime as dt,json,logging,os,threading,time
import trips
log=logging.getLogger('push')
SUBJECT='https://lewym90.github.io'
_key=os.path.join(trips._d,'vapid.pem')
_send=None
_err=['']
def _ensure():
    from cryptography.hazmat.primitives import serialization as z
    from cryptography.hazmat.primitives.asymmetric import ec
    if not os.path.exists(_key):
        k=ec.generate_private_key(ec.SECP256R1())
        fd=os.open(_key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f: f.write(k.private_bytes(z.Encoding.PEM,z.PrivateFormat.PKCS8,z.NoEncryption()))
    k=z.load_pem_private_key(open(_key,'rb').read(),None)
    return k
def public():
    from cryptography.hazmat.primitives import serialization as z
    b=_ensure().public_key().public_bytes(z.Encoding.X962,z.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def set_sender(f):
    global _send;_send=f
def _deliver(dev,sub,payload):
    if _send: return _send(sub,payload)
    _ensure()
    from py_vapid import Vapid02
    from pywebpush import WebPushException,webpush
    try:
        webpush(subscription_info=sub,data=json.dumps(payload,ensure_ascii=False),vapid_private_key=Vapid02.from_pem(open(_key,'rb').read()),vapid_claims={'sub':SUBJECT,'exp':int(time.time())+6*3600},ttl=3600,timeout=15)
        return True
    except WebPushException as e:
        code=getattr(e.response,'status_code',None)
        if code in(404,410):
            with trips._l: trips._c.execute('DELETE FROM devices WHERE id=?',(dev,));trips._c.commit()
        _err[0]=f'{code} {getattr(e.response,"text","")[:120]}';log.warning('push %s %s',code,str(e)[:120]);return False
    except Exception as e:
        _err[0]=str(e)[:120];log.warning('push %s',str(e)[:120]);return False
def subscribe(device,sub,keys):
    if not isinstance(device,str) or not 10<=len(device)<=64: raise ValueError('Zły identyfikator urządzenia')
    if not isinstance(sub,dict) or not str(sub.get('endpoint','')).startswith('https://') or not (sub.get('keys') or {}).get('p256dh'): raise ValueError('Zła subskrypcja')
    with trips._l:
        trips._c.execute('INSERT OR REPLACE INTO devices VALUES(?,?,?)',(device,json.dumps(sub),time.time()))
        n=0
        for k in (keys or [])[:50]:
            try:
                trips._c.execute('INSERT OR IGNORE INTO links VALUES(?,?)',(device,trips.trip_id(k)));n+=1
            except trips.Denied: pass
        trips._c.commit()
    return n
def unsubscribe(device):
    with trips._l: trips._c.execute('DELETE FROM devices WHERE id=?',(device,));trips._c.commit()
def test(device):
    with trips._l: r=trips._c.execute('SELECT sub FROM devices WHERE id=?',(device,)).fetchone()
    if not r: raise ValueError('Włącz najpierw powiadomienia')
    if not _deliver(device,json.loads(r[0]),{'title':'Globtroter','body':'Powiadomienia działają.','url':'./'}): raise ValueError('Nie udało się wysłać próbnego powiadomienia')
def tell(k,device,text):
    """Druga osoba zmienila cos we wspolnym wyjezdzie. Do autora nie wysylamy."""
    tid=trips.trip_id(k)
    with trips._l: rows=trips._c.execute('SELECT d.id,d.sub FROM devices d JOIN links l ON l.device=d.id WHERE l.trip=?',(tid,)).fetchall()
    def run():
        for i,s in rows:
            if i!=device: _deliver(i,json.loads(s),{'title':'Wspólny wyjazd','body':text,'url':'./','tag':f'zmiana{tid}'})
    threading.Thread(target=run,daemon=True).start()
def _short(n): return n.split(' (')[0]
def reminders(plan,s,now):
    """Lista {key,at,title,body}. Uwzglednia zmiany w planie i odhaczone zadania."""
    o=plan['option'];name=_short(plan['dest']['name']);R=[];dep=dt.date.fromisoformat(o['dep'])
    ck=(s or {}).get('ck') or {}
    for i,x in enumerate(plan.get('checklist') or []):
        if (ck.get(str(i)) or {}).get('v'): continue
        at=dt.datetime.combine(dep+dt.timedelta(days=x['d']),dt.time(18,0))
        R.append({'key':f'ck{i}','at':at,'title':f'{name}: do zrobienia','body':x['t']})
    lh=o.get('leaveHome')
    if lh:
        t=dt.datetime.fromisoformat(lh)
        R.append({'key':'d1','at':dt.datetime.combine(dep-dt.timedelta(days=1),dt.time(18,0)),'title':f'Jutro lot: {name}','body':f'Z domu wyjeżdżasz o {t:%H:%M}'+(f', {t.day}.{t.month:02d}.' if t.date()!=dep else '.')+' Sprawdź dokumenty i karty pokładowe.'})
        R.append({'key':'go','at':t-dt.timedelta(minutes=90),'title':'Za półtorej godziny wyjazd','body':f'{name}: z domu wyjeżdżasz o {t:%H:%M}.'})
    back=(plan.get('return') or [None])[0]
    if back: R.append({'key':'back','at':dt.datetime.fromisoformat(back['at'])-dt.timedelta(minutes=90),'title':'Powrót dziś','body':f"O {back['at'][11:16]} wyjście z hotelu na lotnisko."})
    over=(s or {}).get('days') or {}
    for d in plan.get('days') or []:
        st=(over.get(d['date']) or {}).get('stops') or d.get('stops') or []
        names=[x['name'] for x in st if not x.get('meal') and x.get('name')][:3]
        if names: R.append({'key':'day'+d['date'],'at':dt.datetime.combine(dt.date.fromisoformat(d['date']),dt.time(8,0)),'title':f'Dziś: {name}','body':', '.join(names)})
    return R
def tick(now=None):
    now=now or dt.datetime.now()
    with trips._l:
        rows=trips._c.execute('SELECT DISTINCT t.id,t.plan,t.s FROM trips t JOIN links l ON l.trip=t.id').fetchall()
    n=0
    for tid,p,s in rows:
        try: L=[r for r in reminders(json.loads(p),json.loads(s),now) if r['at']<=now<r['at']+dt.timedelta(hours=2)]
        except Exception: log.exception('przypomnienia');continue
        if not L: continue
        with trips._l: devs=trips._c.execute('SELECT d.id,d.sub FROM devices d JOIN links l ON l.device=d.id WHERE l.trip=?',(tid,)).fetchall()
        for r in L:
            for i,sub in devs:
                with trips._l:
                    c=trips._c.execute('INSERT OR IGNORE INTO sent VALUES(?,?,?,?)',(tid,i,r['key'],time.time()));trips._c.commit()
                if c.rowcount and _deliver(i,json.loads(sub),{'title':r['title'],'body':r['body'],'url':'./','tag':r['key']}): n+=1
    return n
def price_now(o,d,ym,n):
    """Najnizsza cena biletu w obie strony dla 1 osoby w miesiacu: (cena, dzien) albo None."""
    import calendar as cal,flights,ryanair,search
    y,m=int(ym[:4]),int(ym[5:7]);a=max(dt.date(y,m,1),dt.date.today()+dt.timedelta(days=1));b=dt.date(y,m,cal.monthrange(y,m)[1])
    if b<a: return None
    g=search.month_grid({'from':o,'to':d,'ym':ym,'nights':n})['grid']
    if not g: return None
    x=min(g,key=lambda v:v['price']);return x['price'],x['dep']
def watch_add(device,o,d,ym,n,name,price):
    import uuid
    with trips._l:
        if trips._c.execute('SELECT COUNT(*) FROM watches WHERE device=?',(device,)).fetchone()[0]>=15: raise ValueError('Możesz obserwować najwyżej 15 tras')
        if not trips._c.execute('SELECT 1 FROM devices WHERE id=?',(device,)).fetchone(): raise ValueError('Włącz najpierw powiadomienia w Profilu')
        i=uuid.uuid4().hex[:12];trips._c.execute('INSERT INTO watches VALUES(?,?,?,?,?,?,?,?,?,?,?)',(i,device,o,d,ym,int(n),str(name)[:60],float(price),float(price),None,time.time()));trips._c.commit()
    return i
def watch_list(device):
    with trips._l: r=trips._c.execute('SELECT id,o,d,ym,n,name,first,last,day FROM watches WHERE device=? ORDER BY t DESC',(device,)).fetchall()
    return [dict(zip(('id','from','to','ym','nights','name','first','last','day'),x)) for x in r]
def watch_del(device,i):
    with trips._l: trips._c.execute('DELETE FROM watches WHERE id=? AND device=?',(i,device));trips._c.commit()
def drop(old,new):
    """Powiadamiamy o realnym spadku: co najmniej 5% i 30 zl."""
    return new<=old*.95 and old-new>=30
def watch_tick(limit=30):
    today=dt.date.today().strftime('%Y-%m')
    with trips._l:
        trips._c.execute('DELETE FROM watches WHERE ym<?',(today,));trips._c.commit()
        rows=trips._c.execute('SELECT w.id,w.device,w.o,w.d,w.ym,w.n,w.name,w.last,d.sub FROM watches w JOIN devices d ON d.id=w.device LIMIT ?',(limit,)).fetchall()
    n=0
    for i,dev,o,d,ym,nights,name,last,sub in rows:
        try: r=price_now(o,d,ym,nights)
        except Exception: continue
        if not r: continue
        p,day=r
        with trips._l: trips._c.execute('UPDATE watches SET last=?,day=? WHERE id=?',(p,day,i));trips._c.commit()
        if drop(last,p):
            _deliver(dev,json.loads(sub),{'title':f'Taniej: {name}','body':f'{o} → {d}: {round(p)} zł za osobę, wylot {int(day[8:])}.{day[5:7]}. Wcześniej {round(last)} zł.','url':'./','tag':'cena'+i});n+=1
    return n
def nightly():
    import flights
    try: flights.warm()
    except Exception: log.exception('rozgrzewanie')
    try: watch_tick()
    except Exception: log.exception('ceny')
def loop():
    day=None;night=None
    while True:
        try:
            tick()
            d=dt.date.today()
            if d!=day: trips.backup();trips.prune();day=d
            h=dt.datetime.now()
            if h.hour==4 and night!=d: night=d;threading.Thread(target=nightly,daemon=True).start()
        except Exception: log.exception('harmonogram')
        time.sleep(60)
def start(): threading.Thread(target=loop,daemon=True).start()
