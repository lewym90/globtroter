"""Plus Wakacje: parse() na prawdziwej stronie listy (offline)."""
import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import http,pluswakacje as pw
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','pluswakacje.html')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=pw.parse(text())
    def test_count(self): self.assertEqual(len(self.o),9)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS)
            self.assertEqual(o['op'],'pluswakacje');self.assertIn(o['kind'],('wypoczynek','objazd'))
            self.assertTrue(o['name']);self.assertRegex(o['dep'],r'^2027-05-\d\d$');self.assertGreater(o['ret'],o['dep'])
            self.assertGreater(o['nights'],0);self.assertEqual(o['from'],'KTW')
            self.assertIsInstance(o['ppp'],int);self.assertEqual(o['total'],2*o['ppp']);self.assertEqual(o['adults'],2)
            self.assertTrue(o['url'].startswith('https://pluswakacje.pl/ofr-'));self.assertNotIn('&#',o['url'])
            self.assertTrue(o['board']);self.assertTrue(o['place'])
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['ppp'],o['stars'],o['board'],o['place']),
                         ('Hotel Miami Calella','2027-05-19','2027-05-21',2,978,3,'Bez wyżywienia','Costa Brava, Calella'))
    def test_sorted(self):
        p=[o['ppp'] for o in self.o];self.assertEqual(p,sorted(p))
    def test_last_page(self): self.assertEqual(pw.last_page(text()),29)

class Search(unittest.TestCase):
    def run_fake(self,origin,pages=1):
        seen=[]
        def fake(url,data=None,headers=None):
            seen.append(url);return text()
        old=http.get;http.get=fake
        try: r=pw.search('ES','2027-05',origin,limit_pages=pages)
        finally: http.get=old
        return r,seen
    def test_limit_and_filter(self):
        r,seen=self.run_fake('KTW',2)
        self.assertEqual(len(seen),2);self.assertFalse(r['complete']);self.assertIsNone(r['total'])
        self.assertEqual(len(r['offers']),9)   # druga strona to te same oferty: bez duplikatow
        self.assertIn(',Hiszpania,Katowice,2027-05-01,2027-05-31,',seen[0]);self.assertIn(',a;price,a;price',seen[0])
    def test_other_origin_filtered(self):
        r,_=self.run_fake('GDN');self.assertEqual(r['offers'],[])
    def test_no_flights(self):
        self.assertEqual(pw.search('ES','2027-05','OSZ')['offers'],[])
    def test_url_encoding(self):
        u=pw.list_url('BG','2027-06',pw.ORIGIN['WAW'])
        self.assertIn(',Bu%C5%82garia,Warszawa;Warszawa+-+Modlin;Warszawa+-+Radom,2027-06-01,2027-06-30,',u)

if __name__=='__main__': unittest.main()
