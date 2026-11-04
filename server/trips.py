"""Wspolne wyjazdy bez kont: dostep daje tajny link. W bazie sa tylko skroty kluczy, nie same klucze.
Zmiany lacza sie element po elemencie, wiec dwie osoby moga pracowac rownoczesnie, takze bez internetu."""
import base64,datetime as dt,glob,hashlib,json,os,secrets,sqlite3,threading,time
SECTIONS=('exp','vault','pack','ck','days','meta')
MAX_ITEM=30000;MAX_ITEMS=3000;MAX_PLAN=450000
_d=os.environ.get('GLOBTROTER_DATA',os.path.join(os.path.dirname(__file__),'..','.data'))
os.makedirs(_d,exist_ok=True)
_l=threading.RLock()
_c=sqlite3.connect(os.path.join(_d,'trips.db'),check_same_thread=False)
_c.execute('PRAGMA journal_mode=WAL');_c.execute('PRAGMA foreign_keys=ON')
_c.executescript('''CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY,hedit TEXT UNIQUE NOT NULL,hview TEXT UNIQUE NOT NULL,plan TEXT NOT NULL,s TEXT NOT NULL,rev INTEGER NOT NULL DEFAULT 1,t REAL,last REAL);
CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,sub TEXT NOT NULL,t REAL);
CREATE TABLE IF NOT EXISTS links(device TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,trip INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,PRIMARY KEY(device,trip));
CREATE TABLE IF NOT EXISTS watches(id TEXT PRIMARY KEY,device TEXT NOT NULL,o TEXT NOT NULL,d TEXT NOT NULL,ym TEXT NOT NULL,n INTEGER NOT NULL,name TEXT,first REAL,last REAL,day TEXT,t REAL);
CREATE TABLE IF NOT EXISTS sent(trip INTEGER NOT NULL,device TEXT NOT NULL,key TEXT NOT NULL,t REAL,PRIMARY KEY(trip,device,key));''')
_c.commit()
class Denied(Exception): pass
def _h(k): return hashlib.sha256(k.encode()).hexdigest()
def view_of(edit): return base64.urlsafe_b64encode(hashlib.sha256(('widok:'+edit).encode()).digest())[:26].decode()
def _clean(s):
    out={}
    for sec in SECTIONS:
        v=(s or {}).get(sec) or {}
        if not isinstance(v,dict): raise ValueError('Złe dane wyjazdu')
        out[sec]={}
        for k,i in list(v.items())[:MAX_ITEMS]:
            if not isinstance(k,str) or len(k)>64 or not isinstance(i,dict) or not isinstance(i.get('u'),(int,float)): continue
            if len(json.dumps(i,ensure_ascii=False))>MAX_ITEM: raise ValueError('Zbyt długi wpis')
            out[sec][k]=i
    return out
def merge(old,new):
    """Dla kazdego elementu zostaje nowsza wersja. Usuniecie to wpis z x=1, zeby nie wrocilo z drugiego telefonu."""
    res={sec:dict((old or {}).get(sec) or {}) for sec in SECTIONS}
    for sec in SECTIONS:
        for k,i in ((new or {}).get(sec) or {}).items():
            if k not in res[sec] or i['u']>=res[sec][k]['u']: res[sec][k]=i
    return res
def create(plan,s=None):
    p=json.dumps(plan,ensure_ascii=False)
    if len(p)>MAX_PLAN: raise ValueError('Plan jest za duży')
    if not isinstance(plan,dict) or not plan.get('option'): raise ValueError('Brak planu')
    edit=secrets.token_urlsafe(18);view=view_of(edit);t=time.time()
    with _l:
        _c.execute('INSERT INTO trips(hedit,hview,plan,s,rev,t,last) VALUES(?,?,?,?,1,?,?)',(_h(edit),_h(view),p,json.dumps(_clean(s),ensure_ascii=False),t,t));_c.commit()
    return {'edit':edit,'view':view,'rev':1}
def _find(k):
    if not isinstance(k,str) or not 10<=len(k)<=64: raise Denied()
    h=_h(k)
    with _l: r=_c.execute('SELECT id,hedit,plan,s,rev FROM trips WHERE hedit=? OR hview=?',(h,h)).fetchone()
    if not r: raise Denied()
    return r,('edit' if secrets.compare_digest(r[1],h) else 'view')
def get(k):
    r,role=_find(k)
    out={'plan':json.loads(r[2]),'s':json.loads(r[3]),'rev':r[4],'role':role}
    if role=='edit': out['view']=view_of(k)
    return out
def sync(k,changes,device=None,note=None):
    r,role=_find(k)
    if role!='edit':
        if changes and any((changes.get(x) or {}) for x in SECTIONS): raise PermissionError('Ten link służy tylko do oglądania')
        return {'s':json.loads(r[3]),'rev':r[4],'role':role}
    with _l:
        r=_c.execute('SELECT s,rev FROM trips WHERE id=?',(_find(k)[0][0],)).fetchone()
        s=merge(json.loads(r[0]),_clean(changes));rev=r[1]+1;b=json.dumps(s,ensure_ascii=False)
        if len(b)>2000000: raise ValueError('Ten wyjazd ma już za dużo wpisów')
        _c.execute('UPDATE trips SET s=?,rev=?,last=? WHERE hedit=?',(b,rev,time.time(),_h(k)));_c.commit()
    if note:
        try:
            import push;push.tell(k,device,str(note)[:120])
        except Exception: pass
    return {'s':s,'rev':rev,'role':role}
def delete(k):
    r,role=_find(k)
    if role!='edit': raise PermissionError('Usunąć może tylko osoba z linkiem do edycji')
    with _l: _c.execute('DELETE FROM trips WHERE id=?',(r[0],));_c.commit()
def trip_id(k): return _find(k)[0][0]
def backup(keep=7):
    """Kopia raz dziennie, sprawdzana po zapisie. Zostaje 7 ostatnich."""
    d=os.path.join(_d,'backup');os.makedirs(d,exist_ok=True)
    p=os.path.join(d,f'trips-{dt.date.today()}.db')
    if os.path.exists(p): return p
    t=p+'.tmp';b=sqlite3.connect(t)
    with _l: _c.backup(b)
    ok=b.execute('PRAGMA integrity_check').fetchone()[0];b.close()
    if ok!='ok':
        os.remove(t);raise RuntimeError('kopia uszkodzona')
    os.replace(t,p);os.chmod(p,0o600)
    for x in sorted(glob.glob(os.path.join(d,'trips-*.db')))[:-keep]: os.remove(x)
    return p
def prune(days=1095):
    with _l: _c.execute('DELETE FROM trips WHERE last<?',(time.time()-days*86400,));_c.execute('DELETE FROM sent WHERE t<?',(time.time()-400*86400,));_c.commit()
