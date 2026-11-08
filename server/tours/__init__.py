"""Oferty biur podrozy: kazde biuro czytane osobno, rownolegle, z pamiecia na kilka godzin.
Zbieramy tylko podstawowe dane (termin, hotel, cena) i link do oferty na stronie biura."""
import datetime,importlib,logging,threading,time,uuid
import store
from . import http
OPS=['itaka','rainbow','tui','exim','grecos','pluswakacje','dertour','toptouristik','nomade','kompastour','regent','matimpex']
NAMES={'ES':'Hiszpania','GR':'Grecja','TR':'Turcja','EG':'Egipt','BG':'Bułgaria','HR':'Chorwacja','IT':'Włochy','PT':'Portugalia','CY':'Cypr',
 'AL':'Albania','TN':'Tunezja','MA':'Maroko','MT':'Malta','ME':'Czarnogóra','FR':'Francja','DE':'Niemcy','AT':'Austria','CZ':'Czechy','HU':'Węgry',
 'GB':'Wielka Brytania','NL':'Holandia','BE':'Belgia','IE':'Irlandia','DK':'Dania','SE':'Szwecja','NO':'Norwegia','IS':'Islandia','FI':'Finlandia',
 'SI':'Słowenia','RS':'Serbia','GE':'Gruzja','AE':'Zjednoczone Emiraty Arabskie','JO':'Jordania','CV':'Wyspy Zielonego Przylądka','MK':'Macedonia Północna',
 'BA':'Bośnia i Hercegowina','RO':'Rumunia','PL':'Polska','SK':'Słowacja','LV':'Łotwa','LT':'Litwa','EE':'Estonia','CH':'Szwajcaria','OM':'Oman','DO':'Dominikana','MX':'Meksyk','TH':'Tajlandia','KE':'Kenia','TZ':'Tanzania (Zanzibar)','LK':'Sri Lanka','MU':'Mauritius','CV':'Wyspy Zielonego Przylądka','MV':'Malediwy','CU':'Kuba','ID':'Indonezja','VN':'Wietnam','US':'Stany Zjednoczone','JM':'Jamajka','SC':'Seszele','IN':'Indie','QA':'Katar','BH':'Bahrajn','SA':'Arabia Saudyjska'}
ORIGINS={'KTW':'Katowice','WAW':'Warszawa','KRK':'Kraków','GDN':'Gdańsk','WRO':'Wrocław','POZ':'Poznań','RZE':'Rzeszów','LUZ':'Lublin','BZG':'Bydgoszcz','LCJ':'Łódź','SZZ':'Szczecin','OSZ':'Olsztyn-Mazury'}
TTL=6*3600
SAME={'WAW':{'WAW','WMI','RDO'},'OSZ':{'OSZ','SZY'}}
MODS={};_done=[False]
def _load():
    if _done[0]: return MODS
    _done[0]=True
    for n in OPS:
        if n in MODS: continue
        try: MODS[n]=importlib.import_module('tours.'+n)
        except ModuleNotFoundError: pass
        except Exception: logging.exception('tours: %s',n)
    return MODS
def meta():
    M=_load();cs=set()
    for m in M.values(): cs|=set(getattr(m,'COUNTRIES',{}))
    return {'ops':[{'id':k,'name':m.NAME,'site':m.SITE,'countries':sorted(m.COUNTRIES)} for k,m in M.items()],
            'countries':sorted(([c,NAMES.get(c,c)] for c in cs),key=lambda x:x[1]),'origins':[[k,v] for k,v in ORIGINS.items()]}
JOBS={};_jl=threading.Lock()
def _check(q):
    cc=str(q.get('cc','')).upper();ym=str(q.get('ym',''));o=q.get('origin') or None
    try: d=datetime.date(int(ym[:4]),int(ym[5:7]),1)
    except Exception: raise ValueError('Wybierz miesiąc')
    t=datetime.date.today().replace(day=1)
    if d<t or (d.year-t.year)*12+d.month-t.month>18: raise ValueError('Biura sprzedają wyjazdy najwyżej półtora roku do przodu')
    if o is not None and o not in ORIGINS: raise ValueError('Nieznane lotnisko wylotu')
    if len(cc)!=2 or not cc.isalpha(): raise ValueError('Wybierz kraj')
    return cc,ym,o
def _one(job,op,m,cc,ym,o):
    st=job['ops'][op];key=f'tour:{op}:{cc}:{ym}:{o or "*"}'
    v,age=store.get(key)
    if v is None:
        st['state']='run'
        try:
            v=m.search(cc,ym,o,limit_pages=getattr(m,'PAGES',40));v['offers']=[x for x in v.get('offers',[]) if _ok(x,ym,o)];v['at']=time.time();age=0
            store.put(key,v,TTL)
        except Exception as e:
            old,oa=store.get_stale(key)
            if old is not None and oa<36*3600: v,age=old,oa;st['stale']=True
            else:
                st['state']='err';st['error']='Strona biura zablokowała odczyt' if isinstance(e,http.Blocked) else 'Strona biura nie odpowiedziała'
                logging.warning('tours %s %s %s %s: %s',op,cc,ym,o,e);return
    for x in v['offers']:
        x['op']=op
        if getattr(m,'APPROX',False): x['approx']=True
    st.update(state='ok',count=len(v['offers']),total=v.get('total'),complete=v.get('complete',True),url=v.get('url'),age=int(age or 0))
    with job['lock']: job['offers'].extend(v['offers'])
def _ok(x,ym,o):
    """Odrzuca wpisy niepelne albo spoza zapytania. Lepiej pokazac mniej niz cos falszywego."""
    try:
        if not(x.get('url','').startswith('https://') and x.get('name') and x.get('dep','').startswith(ym)): return False
        if not(isinstance(x.get('ppp'),int) and 150<=x['ppp']<=100000): return False
        if o and x.get('from') and len(x['from'])==3 and x['from'] not in SAME.get(o,{o}): return False
        return True
    except Exception: return False
def _run(job,cc,ym,o):
    T=[]
    for op,m in _load().items():
        if cc not in getattr(m,'COUNTRIES',{}): job['ops'][op]['state']='none';continue
        t=threading.Thread(target=_one,args=(job,op,m,cc,ym,o),daemon=True);t.start();T.append(t)
    for t in T: t.join(600)
    job['state']='done'
def start(q):
    cc,ym,o=_check(q);sig=(cc,ym,o)
    with _jl:
        for k in [k for k,v in JOBS.items() if time.time()-v['t']>3600]: del JOBS[k]
        for v in JOBS.values():
            if v['sig']==sig and (v['state']=='running' or time.time()-v['t']<600): return v['id']
        if sum(1 for v in JOBS.values() if v['state']=='running')>=4: raise ValueError('Serwer przegląda już kilka biur. Spróbuj za minutę.')
        jid=uuid.uuid4().hex[:12]
        job={'id':jid,'sig':sig,'state':'running','t':time.time(),'offers':[],'lock':threading.Lock(),
             'ops':{op:{'state':'wait','name':m.NAME} for op,m in _load().items()}}
        JOBS[jid]=job
    threading.Thread(target=_run,args=(job,cc,ym,o),daemon=True).start()
    return jid
def status(jid,since=0):
    j=JOBS.get(jid)
    if not j: raise KeyError('id')
    with j['lock']: off=j['offers'][since:]
    return {'id':jid,'state':j['state'],'ops':j['ops'],'offers':off,'n':since+len(off)}
