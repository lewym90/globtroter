"""Sun & Fun: parse(), terms() i search() na prawdziwych odpowiedziach GraphQL (offline)."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import sunfun,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','sunfun.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def fx():
    with open(FIX,encoding='utf-8') as f: return json.load(f)

class Parse(unittest.TestCase):
    def setUp(self): self.F=fx();self.o=sunfun.parse(self.F['results'],self.F['term'])
    def test_count(self): self.assertEqual(len(self.o),10);self.assertEqual(len(sunfun.parse(self.F['results_p2'],self.F['term'])),5)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'sunfun');self.assertEqual(o['kind'],'wypoczynek')
            self.assertEqual((o['dep'],o['ret'],o['nights'],o['from'],o['adults']),('2027-06-05','2027-06-12',7,'WAW',2))
            self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int);self.assertEqual(o['total'],2*o['ppp'])
            self.assertRegex(o['url'],r'^https://www\.sunfun\.pl/grecja/samos/[a-z0-9-]+/\?date=2027-06-05&duration=7&depCity=2&arrCity=949&airline=LOT%20Polish%20Airlines&flightNo=WAWSMI6S27&room1=2$')
            self.assertNotRegex(o['url'],r'/(obj-|objednavka|rezervace|admin)')
            self.assertIn(o['board'],('All inclusive','Śniadania','Śniadania i obiadokolacje','Bez wyżywienia','Pełne wyżywienie'))
            self.assertTrue(o['rating'] is None or 0<o['rating']<=10);self.assertTrue(o['stars'] is None or 1<=o['stars']<=5)
    def test_first(self):
        o=self.o[0]
        # strona hotelu 08.11.2026: STUDIO SV 2-2, BED & BREAKFAST, 'Calkowita cena 4 922 zl', wylot Warszawa
        self.assertEqual((o['name'],o['stars'],o['place'],o['ppp'],o['total'],o['board'],o['rating']),
                         ('Posidonio Bay Holiday Resort',3,'Samos',2461,4922,'Śniadania',9.0))
    def test_bed_only(self):
        o=[x for x in self.o if x['name']=='Green Hill'][0];self.assertEqual((o['board'],o['total'],o['place']),('Bez wyżywienia',5382,'Samos, Kokkari'))
    def test_terms(self):
        ts=sunfun.terms(self.F['flights']['data']['search_flights']['flights'],'2027-06')
        self.assertEqual([(t['date'],t['duration']) for t in ts],[(d,n) for d in ('2027-06-05','2027-06-12','2027-06-19','2027-06-26') for n in (7,14)])
        self.assertEqual(ts[1]['ret'],'2027-06-19');self.assertEqual(ts[0]['from'],'WAW')
        self.assertEqual(sunfun.terms(self.F['flights']['data']['search_flights']['flights'],'2027-09'),[])
    def test_pick(self):
        ts=[{'date':f'2027-06-{d:02d}','duration':n} for d in range(1,31) for n in (7,10)]
        p=sunfun.pick(ts,10);self.assertEqual(len(p),10);self.assertTrue(all(t['duration']==7 for t in p))
        self.assertEqual(p[0]['date'],'2027-06-01');self.assertGreaterEqual(p[-1]['date'],'2027-06-25')
        p=sunfun.pick(ts[:6],10);self.assertEqual(len(p),6)
    def test_helpers(self):
        self.assertEqual(sunfun._stars('STAR_4'),4);self.assertEqual(sunfun._stars('STAR_4_5'),4.5);self.assertIsNone(sunfun._stars(None))
        self.assertEqual(sunfun._rating({'rating':'97 %','ratingCount':15}),9.7);self.assertIsNone(sunfun._rating({'rating':'97 %','ratingCount':0}))
        self.assertEqual(sunfun.board('PREAI',''),'All inclusive');self.assertEqual(sunfun.board('XX','LIGHT ALL INCLUSIVE'),'All inclusive')
        self.assertTrue(sunfun.APPROX)

class Search(unittest.TestCase):
    def test_flow_and_bound(self):
        F=fx();ops=[]
        def fake(url,data=None,headers=None,**kw):
            b=json.loads(data)[0];ops.append(b)
            if b['operationName']=='SearchFlights':
                fl=json.loads(json.dumps(F['flights']));fl['data']['search_flights']['flights']=fl['data']['search_flights']['flights'][:8]
                return json.dumps(fl)
            p=b['variables']['request'].get('page',1)
            return json.dumps(F['results_p2'] if p==2 else F['results'])
        old=http.get;http.get=fake
        try: r=sunfun.search('GR','2027-06','WAW')
        finally: http.get=old
        self.assertEqual(ops[0]['operationName'],'SearchFlights')
        rq=ops[0]['variables']['request'];self.assertEqual((rq['depCity'],rq['arrCities'],rq['dateFrom']),(2,['949'],'2027-06-01'))
        res=[o for o in ops if o['operationName']=='SearchResults']
        self.assertEqual(len(res),16)          # 8 terminow x 2 strony
        self.assertEqual(res[0]['variables']['request']['flightNo'],'WAWSMI6S27')
        self.assertEqual(len(r['offers']),15);self.assertTrue(r['complete'])
        self.assertEqual(r['offers'][0]['ppp'],2461)
        old=http.get;http.get=fake;ops.clear()
        try: r=sunfun.search('GR','2027-06','WAW',limit_pages=5)
        finally: http.get=old
        self.assertEqual(len(ops),5);self.assertFalse(r['complete']);self.assertIsNone(r['total'])
    def test_no_flights_from(self):
        def boom(*a,**k): raise AssertionError('network')
        old=http.get;http.get=boom
        try:
            for o in ('KRK','BZG','SZZ','OSZ'): self.assertEqual(sunfun.search('EG','2027-06',o)['offers'],[])
            self.assertEqual(sunfun.search('ES','2027-06','KTW')['offers'],[])
        finally: http.get=old

if __name__=='__main__': unittest.main()
