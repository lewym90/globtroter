"""Best Reisen (platforma Bluevendo): parse() na prawdziwej, przycietej odpowiedzi /api/bv (offline)."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import bestreisen,bvplatform,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','bestreisen.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=bestreisen.parse(text())
    def test_count(self): self.assertEqual(len(self.o),7)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'bestreisen');self.assertEqual(o['kind'],'wypoczynek')
            self.assertTrue(o['name']);self.assertRegex(o['dep'],r'^2027-07-\d\d$');self.assertGreater(o['ret'],o['dep'])
            self.assertGreater(o['nights'],0);self.assertIn(o['from'],('WAW','WMI'))
            self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int);self.assertEqual(o['adults'],2)
            self.assertLessEqual(abs(2*o['ppp']-o['total']),1)
            self.assertRegex(o['url'],r'^https://bestreisengroup\.pl/hotel/grecja/[a-z0-9-]+/[a-z0-9-]+\?ids=\d+_\d+_\d+_\d+&ad=2&ch=&hid=\d+$')
            self.assertNotIn('/admin',o['url'])
            self.assertIn(o['stars'],(3,4));self.assertIsNone(o['rating']);self.assertTrue(o['board'])
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['from'],o['ppp'],o['total'],o['stars'],o['board'],o['place']),
                         ('Apollo Hotel Athens','2027-07-25','2027-07-28',3,'WMI',1424,2848,3,'Śniadania','Attika, Athens'))
        self.assertEqual(o['url'],'https://bestreisengroup.pl/hotel/grecja/attika/apollo-hotel-athens?ids=1472746032_2269232_2269193_1727943&ad=2&ch=&hid=29540')
    def test_self_catering_is_no_board(self):
        o=[x for x in self.o if x['name']=='Maritime Apartments'][0];self.assertEqual(o['board'],'Bez wyżywienia');self.assertEqual(o['stars'],3)
    def test_filters(self):
        self.assertEqual(bestreisen.parse(text(),'2027-06'),[])
        self.assertEqual(len(bestreisen.parse(text(),'2027-07','WAW')),7)    # WAW = Chopin + Modlin + Radom
        self.assertEqual(bestreisen.parse(text(),'2027-07','KTW'),[])

class Helpers(unittest.TestCase):
    def test_slug_board_stars(self):
        self.assertEqual(bvplatform.slug('Hotel Copacabana - Lloret'),'hotel-copacabana-lloret')
        self.assertEqual(bvplatform.slug('Hiszpania / Łódź & Ś'),'hiszpania-lodz-s')
        self.assertEqual(bvplatform.board('tylko śniadania'),'Śniadania');self.assertEqual(bvplatform.board('2 posiłki'),'Śniadania i obiadokolacje')
        self.assertEqual(bvplatform.board('Ultra All Inclusive'),'All inclusive');self.assertEqual(bvplatform.board('Coś innego','HB'),'Śniadania i obiadokolacje')
        self.assertEqual(bvplatform.stars('****'),4);self.assertEqual(bvplatform.stars('3'),3);self.assertEqual(bvplatform.stars('4.5'),4.5);self.assertIsNone(bvplatform.stars(''))

class Search(unittest.TestCase):
    def test_request_and_paging(self):
        seen=[]
        def fake(url,data=None,headers=None,**kw):
            seen.append((url,json.loads(data) if data else None))
            if data and json.loads(data)['method']=='x-regionlist':
                return json.dumps({'data':{'response':{'regions':{'region':[{'countryid':'73','regionid':'191'}]}}}})
            d=json.loads(text());d['data']['response']['total']=7;return json.dumps(d)
        old=http.get;http.get=fake
        try: r=bestreisen.search('gr','2027-07','WAW')
        finally: http.get=old
        self.assertTrue(r['complete']);self.assertEqual(r['total'],7);self.assertEqual(len(r['offers']),7)
        url,b=seen[0];p=b['params']
        self.assertEqual(url,'https://bestreisengroup.pl/api/bv');self.assertEqual(b['method'],'search-search')
        self.assertEqual(p['countryid'],['73']);self.assertEqual(p['startnodeid'],['13','120','243'])
        self.assertEqual((p['startdatefrom'],p['enddateto']),('2027-07-01','2027-07-31'))
        self.assertEqual((p['ordername'],p['orderdirection'],p['transporttypeid']),('customerprice','ASC','1'))
        self.assertEqual(p['searchrooms'],[{'adults':2,'infants':0,'childage':[]}])
        self.assertTrue(r['url'].startswith('https://bestreisengroup.pl/wyniki-wyszukiwania?regions=191&departurenodes=13%2C120%2C243'))
        self.assertEqual([o['ppp'] for o in r['offers']],sorted(o['ppp'] for o in r['offers']))
    def test_page_limit(self):
        n=[0]
        def fake(url,data=None,headers=None,**kw):
            if json.loads(data)['method']=='x-regionlist': raise IOError('x')
            n[0]+=1;d=json.loads(text());d['data']['response']['total']=5000;return json.dumps(d)
        old=http.get;http.get=fake
        try: r=bestreisen.search('GR','2027-07',None,limit_pages=40)
        finally: http.get=old
        self.assertEqual(n[0],bestreisen.PAGES);self.assertFalse(r['complete']);self.assertEqual(r['total'],5000)
    def test_unknown_no_network(self):
        self.assertEqual(bestreisen.search('XX','2027-07','KTW')['offers'],[])
        def boom(*a,**k): raise AssertionError('network')
        old=http.get;http.get=boom
        try: self.assertEqual(bestreisen.search('GR','2027-07','OSZ')['offers'],[])
        finally: http.get=old
    def test_maps(self):
        self.assertEqual(bestreisen.NODES['WAW'],['13','120','243'])
        for c in 'KTW KRK GDN WRO POZ RZE LUZ BZG LCJ SZZ'.split(): self.assertIn(c,bestreisen.NODES)
        for c in 'ES GR TR EG BG HR IT PT CY AL TN MA MT ME'.split(): self.assertIn(c,bestreisen.COUNTRIES)

if __name__=='__main__': unittest.main()
