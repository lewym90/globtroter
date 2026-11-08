"""Adapter TUI: parse() na prawdziwej, przycietej stronie listy (__NEXT_DATA__ w base64), bez sieci."""
import datetime as dt,os,re,sys,tempfile,unittest
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import tui
FX=os.path.join(os.path.dirname(__file__),'fixtures','tours','tui.html')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
class Parse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FX,encoding='utf-8') as f: cls.html=f.read()
        cls.offers=tui.parse(cls.html)
    def test_count(self): self.assertEqual(len(self.offers),6)
    def test_well_formed(self):
        for o in self.offers:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'tui');self.assertTrue(o['name'])
            d=dt.date.fromisoformat(o['dep']);r=dt.date.fromisoformat(o['ret'])
            self.assertTrue(1<=(r-d).days<=16);self.assertTrue(1<=o['nights']<=(r-d).days)
            self.assertEqual(o['from'],'KTW');self.assertEqual(o['adults'],2)
            self.assertIsInstance(o['ppp'],int);self.assertGreater(o['ppp'],300)
            self.assertLessEqual(abs(o['total']-2*o['ppp']),2)
            self.assertTrue(o['rating'] is None or 0<o['rating']<=10)
            self.assertTrue(o['stars'] is None or 1<=o['stars']<=5)
            self.assertTrue(o['board'])
            self.assertTrue(re.match(r'https://www\.tui\.pl/wypoczynek/hiszpania/[a-z0-9-]+/[a-z0-9-]+/OfferCodeWS/KTW[A-Z]{3}\d{8}',o['url']),o['url'])
            for bad in ('/api/','/hotel/offers/','/hotel/configurator/'): self.assertNotIn(bad,o['url'])
    def test_first(self):
        o=self.offers[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['ppp'],o['total'],o['board'],o['place'],o['stars'],o['rating']),
                         ('Don Gregorio','2027-02-08','2027-02-15',6,1107,2214,'Bez wyżywienia','Costa Blanca, Benidorm',2,5.8))
    def test_may(self):
        self.assertEqual(sum(o['dep'].startswith('2027-05') for o in self.offers),4)
    def test_page_data(self):
        rows,pg=tui.page_data(self.html);self.assertEqual(pg['pagesCount'],43);self.assertEqual(len(rows),6)
    def test_no_list(self):
        h='<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"initialOffersData":[]}}}</script>'
        self.assertEqual(tui.page_data(h),(None,None));self.assertEqual(tui.parse(h),[])
class Query(unittest.TestCase):
    def test_countries(self):
        for c in 'ES GR TR EG BG HR IT PT CY AL TN MA MT ME'.split(): self.assertIn(c,tui.COUNTRIES)
    def test_sources(self):
        m,e=tui._sources('ES','KTW')
        self.assertEqual(m,['/wypoczynek/hiszpania/wyloty-z-katowic','/wypoczynek/wyspy-kanaryjskie/wyloty-z-katowic'])
        self.assertTrue(all(p.endswith('/oferty-first-minute-lato') for p in e))
    def test_unknown_origin_no_network(self):
        self.assertEqual(tui.search('ES','2027-05','OSZ')['offers'],[])
if __name__=='__main__': unittest.main()
