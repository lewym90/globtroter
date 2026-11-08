"""OnHolidays (platforma Bluevendo): parse() na prawdziwej, przycietej odpowiedzi /api/bv (offline)."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import onholidays,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','onholidays.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=onholidays.parse(text())
    def test_count(self): self.assertEqual(len(self.o),8)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'onholidays');self.assertEqual(o['kind'],'wypoczynek')
            self.assertRegex(o['dep'],r'^2027-06-\d\d$');self.assertGreater(o['ret'],o['dep']);self.assertIn(o['nights'],(3,4))
            self.assertIn(o['from'],('WAW','GDN','KRK'));self.assertEqual(o['adults'],2)
            self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int);self.assertLessEqual(abs(2*o['ppp']-o['total']),1)
            self.assertRegex(o['url'],r'^https://onholidays\.pl/hotel/grecja/(rodos|kreta)/[a-z0-9-]+\?ids=\d+_\d+_\d+_\d+&ad=2&ch=$')
            self.assertTrue(o['board']);self.assertIsNone(o['rating']);self.assertIn(o['stars'],(3,4,5))
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['from'],o['ppp'],o['total'],o['board'],o['place']),
                         ('Romantza Mare','2027-06-07','2027-06-10',3,'WAW',1279,2558,'Śniadania','Rodos, Kalithea'))
        self.assertEqual(o['url'],'https://onholidays.pl/hotel/grecja/rodos/romantza-mare?ids=8972211_68137_68138_40723&ad=2&ch=')
    def test_total_is_what_you_pay(self):
        # strona: 'Cena za osobe 2947 PLN', 'Cena calkowita 5009 PLN' -> ppp z ceny calkowitej
        o=[x for x in self.o if x['name'].startswith('CASTELLO')][0]
        self.assertEqual((o['total'],o['ppp'],o['stars'],o['from']),(5009,2504,5,'KRK'))
        self.assertEqual(o['url'],'https://onholidays.pl/hotel/grecja/kreta/castello-boutique-resort-spa-adults-only?ids=9030832_67400_68095_41012&ad=2&ch=')
    def test_filters(self):
        self.assertEqual([o['from'] for o in onholidays.parse(text(),'2027-06','KRK')],['KRK','KRK'])
        self.assertEqual(onholidays.parse(text(),'2027-07'),[])
        self.assertEqual(onholidays.parse(text(),'2027-06','KTW'),[])

class Search(unittest.TestCase):
    def test_request(self):
        seen=[]
        def fake(url,data=None,headers=None,**kw):
            b=json.loads(data);seen.append(b)
            if b['method']=='x-regionlist':
                return json.dumps({'data':{'response':{'regions':{'region':[{'countryid':'16','regionid':'9'},{'countryid':'16','regionid':'13'}]}}}})
            return text()
        old=http.get;http.get=fake
        try: r=onholidays.search('GR','2027-06','KRK')
        finally: http.get=old
        p=seen[0]['params']
        self.assertEqual((p['countryid'],p['startnodeid'],p['numOnPage']),(['16'],['65'],100))
        self.assertTrue(r['complete']);self.assertEqual(r['total'],27);self.assertEqual(len(r['offers']),2)
        self.assertIn('regions=9%2C13&departurenodes=65',r['url'])
    def test_no_airport(self):
        def boom(*a,**k): raise AssertionError('network')
        old=http.get;http.get=boom
        try:
            for o in ('BZG','LCJ','SZZ','OSZ'): self.assertEqual(onholidays.search('GR','2027-06',o)['offers'],[])
            self.assertEqual(onholidays.search('SI','2027-06','KTW')['offers'],[])
        finally: http.get=old
    def test_maps(self):
        self.assertEqual(onholidays.NODES['WAW'],['4','62','71']);self.assertEqual(onholidays.COUNTRIES['ES'],'27')

if __name__=='__main__': unittest.main()
