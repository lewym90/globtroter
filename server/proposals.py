"""Propozycja wyjazdu: kilka opcji do wyboru wyslanych jednym linkiem, bez kont.
Autor ma klucz do edycji, odbiorca klucz do ogladania. Odbiorca moze dac serce i komentarz przy kazdej opcji.
Gdy autor ukryje ceny, serwer usuwa je z danych dla odbiorcy (nie tylko chowa na ekranie)."""
import base64,hashlib,json,secrets,threading,time
import trips
MAX=1500000;MAX_ITEMS=8;TTL_DAYS=183
_l=trips._l;_c=trips._c
_c.executescript('''CREATE TABLE IF NOT EXISTS props(id INTEGER PRIMARY KEY,hedit TEXT UNIQUE NOT NULL,hview TEXT UNIQUE NOT NULL,data TEXT NOT NULL,votes TEXT NOT NULL,device TEXT,off INTEGER NOT NULL DEFAULT 0,t REAL,last REAL);''')
_c.commit()
PRICE={'total','tickets','price','pln','bestTotal','fuel','tolls','prices','cost','ppp','transport','hotelEst','access','own','diff','agency','perNight','calendar','alts','cheapest','budget','tollItems','totalPln'}
def _h(k): return hashlib.sha256(k.encode()).hexdigest()
def view_of(edit): return base64.urlsafe_b64encode(hashlib.sha256(('propozycja:'+edit).encode()).digest())[:26].decode()
def _strip(x):
    if isinstance(x,dict): return {k:_strip(v) for k,v in x.items() if k not in PRICE}
    if isinstance(x,list): return [_strip(v) for v in x]
    return x
def _private(x):
    """Bez wspolrzednych domu autora: dom zostaje tylko na jego telefonie."""
    if isinstance(x,dict): return {k:_private(v) for k,v in x.items() if k not in('home','origin') and not (k=='map' and isinstance(v,str) and 'origin=' in v)}
    if isinstance(x,list): return [_private(v) for v in x]
    return x
def _clean(d):
    if not isinstance(d,dict): raise ValueError('Zła propozycja')
    items=d.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=MAX_ITEMS: raise ValueError(f'Propozycja musi mieć od 1 do {MAX_ITEMS} opcji')
    out={'title':str(d.get('title') or 'Propozycja wyjazdu')[:80],'msg':str(d.get('msg') or '')[:1200],'hide':bool(d.get('hide')),'items':[]}
    for i,it in enumerate(items):
        if not isinstance(it,dict) or not isinstance(it.get('option'),dict): raise ValueError('Zła opcja w propozycji')
        out['items'].append({'id':str(it.get('id') or i)[:24],'kind':'plan' if it.get('plan') else 'idea','option':_private(it['option']),'plan':_private(it['plan']) if isinstance(it.get('plan'),dict) else None,'guide':it.get('guide') if isinstance(it.get('guide'),list) else None,'at':it.get('at')})
    s=json.dumps(out,ensure_ascii=False)
    if len(s)>MAX: raise ValueError('Propozycja jest za duża. Usuń jedną opcję.')
    return out
def create(d,device=None):
    data=_clean(d);edit=secrets.token_urlsafe(18);view=view_of(edit);t=time.time()
    with _l:
        _c.execute('INSERT INTO props(hedit,hview,data,votes,device,t,last) VALUES(?,?,?,?,?,?,?)',(_h(edit),_h(view),json.dumps(data,ensure_ascii=False),'{}',device if isinstance(device,str) and 10<=len(device)<=64 else None,t,t));_c.commit()
    return {'edit':edit,'view':view}
def _find(k):
    if not isinstance(k,str) or not 10<=len(k)<=64: raise trips.Denied()
    h=_h(k)
    with _l: r=_c.execute('SELECT id,hedit,data,votes,device,off,t FROM props WHERE hedit=? OR hview=?',(h,h)).fetchone()
    if not r: raise trips.Denied()
    role='edit' if secrets.compare_digest(r[1],h) else 'view'
    if role=='view' and r[5]: raise trips.Denied()
    return r,role
def get(k):
    r,role=_find(k);data=json.loads(r[2])
    if role=='view' and data.get('hide'): data=_strip(data)
    out={'data':data,'votes':json.loads(r[3]),'role':role,'t':r[6]}
    if role=='edit': out['view']=view_of(k);out['off']=bool(r[5])
    with _l: _c.execute('UPDATE props SET last=? WHERE id=?',(time.time(),r[0]));_c.commit()
    return out
def vote(k,item,heart=None,comment=None):
    r,role=_find(k)
    if role!='view': raise PermissionError('Głosuje osoba, która dostała propozycję')
    data=json.loads(r[2])
    names={str(i['id']):i['option'].get('dest',{}).get('name','opcja') for i in data['items']}
    if str(item) not in names: raise ValueError('Nie ma takiej opcji')
    with _l:
        v=json.loads(_c.execute('SELECT votes FROM props WHERE id=?',(r[0],)).fetchone()[0])
        cur=v.get(str(item),{})
        if heart is not None: cur['heart']=bool(heart)
        if comment is not None: cur['comment']=str(comment)[:600]
        cur['t']=time.time();v[str(item)]=cur
        _c.execute('UPDATE props SET votes=?,last=? WHERE id=?',(json.dumps(v,ensure_ascii=False),time.time(),r[0]));_c.commit()
    if r[4]: _tell(r[4],names[str(item)].split(' (')[0],heart,comment)
    return {'votes':v}
def _tell(dev,name,heart,comment):
    import push
    with _l: row=_c.execute('SELECT sub FROM devices WHERE id=?',(dev,)).fetchone()
    if not row: return
    body=(f'Serce dla: {name}.' if heart else f'Zmiana przy: {name}.') if comment is None else f'Komentarz przy {name}: {comment[:80]}'
    threading.Thread(target=push._deliver,args=(dev,json.loads(row[0]),{'title':'Odpowiedź na propozycję','body':body,'url':'./','tag':'prop'}),daemon=True).start()
def setoff(k,off):
    r,role=_find(k)
    if role!='edit': raise PermissionError('Tylko autor może wyłączyć link')
    with _l: _c.execute('UPDATE props SET off=? WHERE id=?',(1 if off else 0,r[0]));_c.commit()
    return {'off':bool(off)}
def delete(k):
    r,role=_find(k)
    if role!='edit': raise PermissionError('Tylko autor może usunąć propozycję')
    with _l: _c.execute('DELETE FROM props WHERE id=?',(r[0],));_c.commit()
def prune(days=TTL_DAYS):
    with _l: _c.execute('DELETE FROM props WHERE last<?',(time.time()-days*86400,));_c.commit()
