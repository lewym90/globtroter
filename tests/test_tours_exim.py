"""Exim Tours: parse() na prawdziwej odpowiedzi API (offline)."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import exim,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','exim.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=exim.parse(text())
    def test_count(self): self.assertEqual(len(self.o),6)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS)
            self.assertEqual(o['op'],'exim');self.assertEqual(o['kind'],'wypoczynek')
            self.assertTrue(o['name']);self.assertRegex(o['dep'],r'^2027-05-\d\d$');self.assertRegex(o['ret'],r'^\d{4}-\d\d-\d\d$')
            self.assertGreater(o['ret'],o['dep']);self.assertGreater(o['nights'],0)
            self.assertEqual(o['from'],'KTW');self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int)
            self.assertEqual(o['adults'],2);self.assertLessEqual(abs(o['ppp']*2-o['total']),1)
            self.assertTrue(o['url'].startswith('https://www.exim.pl/kierunki/'))
            self.assertIn('DD='+o['dep'],o['url'])
            self.assertTrue(o['board'])
            if o['rating'] is not None: self.assertTrue(0<o['rating']<=10)
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['total'],o['ppp'],o['stars']),('REYMAR','2027-05-05','2027-05-08',3,2098,1049,3))
        self.assertEqual(o['place'],'Costa Brava, Santa Susanna');self.assertEqual(o['board'],'Bez wyżywienia')
    def test_uneven_adult_prices(self):   # 1449 + 809: ppp to srednia z ceny calkowitej
        o=[x for x in self.o if x['total']==2258][0];self.assertEqual(o['ppp'],1129)
    def test_month_filter(self):
        self.assertEqual(exim.parse(text(),'2027-06'),[])

class Search(unittest.TestCase):
    def test_paging_and_params(self):
        seen=[]
        def fake(url,data=None,headers=None):
            seen.append(url);d=json.loads(text());d['toursCount']=6;return json.dumps(d)
        old=http.get;http.get=fake
        try: r=exim.search('es','2027-05','KTW')
        finally: http.get=old
        self.assertEqual(len(seen),1);self.assertTrue(r['complete']);self.assertEqual(r['total'],6);self.assertEqual(len(r['offers']),6)
        u=seen[0];self.assertIn('to=1862',u);self.assertIn('dd=2027-05-01',u);self.assertIn('rd=2027-05-31',u);self.assertIn('sortby=PriceTotal',u)
        self.assertTrue(r['url'].startswith('https://www.exim.pl/wyszukanie?'))
    def test_unknown(self):
        self.assertEqual(exim.search('ES','2027-05','OSZ')['offers'],[])
        self.assertEqual(exim.search('XX','2027-05',None)['offers'],[])
    def test_waw_group(self):
        self.assertEqual(exim.AIRPORTS['WAW'],'3850|4380|4381')

if __name__=='__main__': unittest.main()
