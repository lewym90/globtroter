"""Trwala pamiec podreczna (SQLite) ze znacznikiem czasu. Bezpieczna watkowo."""
import json,os,sqlite3,threading,time
_DB=os.environ.get('GLOBTROTER_DATA',os.path.join(os.path.dirname(__file__),'..','.data'))
os.makedirs(_DB,exist_ok=True)
_lock=threading.Lock()
_c=sqlite3.connect(os.path.join(_DB,'cache.db'),check_same_thread=False)
_c.execute('PRAGMA journal_mode=WAL')
_c.execute('CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT,t REAL,ttl REAL)')
_c.commit()
def get(k):
    """Zwraca (wartosc, wiek_s) albo (None, None) po wygasnieciu."""
    with _lock: r=_c.execute('SELECT v,t,ttl FROM kv WHERE k=?',(k,)).fetchone()
    if not r: return None,None
    age=time.time()-r[1]
    if age>r[2]: return None,None
    return json.loads(r[0]),age
def get_stale(k):
    with _lock: r=_c.execute('SELECT v,t FROM kv WHERE k=?',(k,)).fetchone()
    return (json.loads(r[0]),time.time()-r[1]) if r else (None,None)
def put(k,v,ttl):
    with _lock:
        _c.execute('INSERT OR REPLACE INTO kv VALUES(?,?,?,?)',(k,json.dumps(v,ensure_ascii=False),time.time(),ttl))
        _c.commit()
def prune(max_age=60*86400):
    with _lock:
        _c.execute('DELETE FROM kv WHERE t<?',(time.time()-max_age,));_c.commit()
