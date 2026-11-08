"""Zbieranie ofert z wielu biur: bez sieci, z udawanymi biurami."""
import datetime as dt,os,sys,tempfile,time,types,unittest
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
import tours
from tours import http
YM=(dt.date.today().replace(day=1)+dt.timedelta(days=40)).strftime('%Y-%m')
def offer(**k):
    o={'name':'Hotel A','stars':4,'place':'Teneryfa','dep':YM+'-10','ret':YM+'-17','nights':7,'board':'All inclusive','from':'KTW','ppp':2199,'adults':2,'total':4398,'url':'https://biuro.example/oferta/1'}
    o.update(k);return o
def fake(name,offers,cc=('ES',),err=None):
    m=types.SimpleNamespace(NAME=name,SITE='https://x',COUNTRIES={c:c for c in cc})
    def search(c,ym,o,limit_pages=40):
        if err: raise err
        return {'offers':[dict(x) for x in offers],'total':len(offers),'complete':True,'url':'https://biuro.example/lista'}
    m.search=search;return m
def run(q,mods):
    tours._done[0]=True;tours.MODS.clear();tours.MODS.update(mods);tours.JOBS.clear()
    import store;store._c.execute('DELETE FROM kv');store._c.commit()
    jid=tours.start(q)
    for _ in range(200):
        if tours.JOBS[jid]['state']=='done': break
        time.sleep(.02)
    return tours.status(jid)
class Tours(unittest.TestCase):
    def tearDown(self): tours.MODS.clear();tours._done[0]=False
    def test_merge(self):
        r=run({'cc':'ES','ym':YM,'origin':'KTW'},{'a':fake('A',[offer()]),'b':fake('B',[offer(name='Hotel B',url='https://b.example/2')])})
        self.assertEqual(r['state'],'done');self.assertEqual(len(r['offers']),2)
        self.assertEqual({x['op'] for x in r['offers']},{'a','b'})
    def test_other_month_dropped(self):
        r=run({'cc':'ES','ym':YM,'origin':None},{'a':fake('A',[offer(dep='2020-01-01')])})
        self.assertEqual(r['offers'],[])
    def test_bad_price_dropped(self):
        r=run({'cc':'ES','ym':YM,'origin':None},{'a':fake('A',[offer(ppp=0),offer(ppp='2199'),offer(ppp=None)])})
        self.assertEqual(r['offers'],[])
    def test_wrong_origin_dropped(self):
        r=run({'cc':'ES','ym':YM,'origin':'KTW'},{'a':fake('A',[offer(**{'from':'BER'}),offer(**{'from':'KTW'})])})
        self.assertEqual(len(r['offers']),1)
    def test_warsaw_modlin(self):
        r=run({'cc':'ES','ym':YM,'origin':'WAW'},{'a':fake('A',[offer(**{'from':'WMI'})])})
        self.assertEqual(len(r['offers']),1)
    def test_country_not_sold(self):
        r=run({'cc':'GR','ym':YM,'origin':None},{'a':fake('A',[offer()])})
        self.assertEqual(r['ops']['a']['state'],'none')
    def test_error_isolated(self):
        r=run({'cc':'ES','ym':YM,'origin':None},{'a':fake('A',[],err=IOError('x')),'b':fake('B',[offer()])})
        self.assertEqual(r['ops']['a']['state'],'err');self.assertEqual(len(r['offers']),1)
    def test_blocked_message(self):
        r=run({'cc':'ES','ym':YM,'origin':None},{'a':fake('A',[],err=http.Blocked('403'))})
        self.assertIn('zablokowała',r['ops']['a']['error'])
    def test_no_link_dropped(self):
        r=run({'cc':'ES','ym':YM,'origin':None},{'a':fake('A',[offer(url='/rel'),offer(url='javascript:x')])})
        self.assertEqual(r['offers'],[])
    def test_past_month_rejected(self):
        with self.assertRaises(ValueError): tours.start({'cc':'ES','ym':'2020-01','origin':None})
    def test_bad_origin_rejected(self):
        with self.assertRaises(ValueError): tours.start({'cc':'ES','ym':YM,'origin':'XXX'})
    def test_meta(self):
        tours._done[0]=True;tours.MODS.clear();tours.MODS.update({'a':fake('A',[],cc=('ES','GR'))})
        m=tours.meta();self.assertEqual([c for c,_ in m['countries']],['GR','ES'])
if __name__=='__main__': unittest.main()
