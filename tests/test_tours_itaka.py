"""Adapter Itaka: parse() na prawdziwej, przycietej stronie wynikow (__NEXT_DATA__), bez sieci."""
import datetime as dt,os,re,sys,tempfile,unittest,urllib.parse as up
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import itaka
FX=os.path.join(os.path.dirname(__file__),'fixtures','tours','itaka.html')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
class Parse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FX,encoding='utf-8') as f: cls.html=f.read()
        cls.all=itaka.parse(cls.html)                       # bez filtrow
        cls.offers=itaka.parse(cls.html,'ES','2027-05','KTW')
    def test_counts(self):
        # 8 wierszy w fixture: 1 z dojazdem wlasnym (odrzucony zawsze), 1 z wylotem w czerwcu (odrzucony dla 2027-05)
        self.assertEqual(len(self.all),7);self.assertEqual(len(self.offers),6)
    def test_well_formed(self):
        for o in self.offers:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'itaka');self.assertTrue(o['name'])
            d=dt.date.fromisoformat(o['dep']);r=dt.date.fromisoformat(o['ret'])
            self.assertEqual(o['dep'][:7],'2027-05');self.assertTrue(1<=(r-d).days<=21);self.assertTrue(1<=o['nights']<=(r-d).days)
            self.assertEqual(o['from'],'KTW');self.assertEqual(o['adults'],2)
            self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int);self.assertGreater(o['ppp'],300)
            self.assertEqual(o['total'],2*o['ppp'])
            self.assertTrue(o['rating'] is None or 0<o['rating']<=10)
            self.assertTrue(o['stars'] is None or 1<=o['stars']<=5)
            self.assertTrue(o['board']);self.assertIn(o['kind'],('wypoczynek','objazd','city break'))
            self.assertTrue(re.match(r'https://www\.itaka\.pl/(wczasy|wycieczki|city-break)/hiszpania/([a-z0-9-]+/)?[a-z0-9-]+,[A-Z0-9]+/\?id=[A-Za-z0-9%]+$',o['url']),o['url'])
            for bad in ('/api','/reservation','/booking'): self.assertNotIn(bad,o['url'])
    def test_first(self):
        o=self.offers[0]
        # lista: 1179 zl + 20 zl TFG/TFP na osobe (strona oferty: "1 179 zl +20 zl (TFG i TFP)")
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['ppp'],o['total'],o['board'],o['place'],o['stars'],o['kind']),
                         ('Rentalmar Blue Beach Apartments','2027-05-05','2027-05-08',3,1199,2398,'Bez wyżywienia','Costa Dorada',3.0,'wypoczynek'))
    def test_kinds(self):
        self.assertEqual(sorted(o['kind'] for o in self.offers),['city break','objazd']+['wypoczynek']*4)
        rt=[o for o in self.offers if o['kind']=='objazd'][0];self.assertIn('/wycieczki/',rt['url'])
    def test_rate_id_roundtrip(self):
        rid=up.unquote(up.unquote(self.offers[0]['url'].split('?id=')[1]))
        self.assertTrue(rid.startswith('CgVJdGFrYR'))
    def test_filters(self):
        self.assertEqual(itaka.parse(self.html,'ES','2027-05','WAW'),[])
        self.assertEqual(itaka.parse(self.html,'GR','2027-05','KTW'),[])
        self.assertEqual([o['dep'] for o in itaka.parse(self.html,'ES','2027-06',None)],['2027-06-01'])
    def test_total(self): self.assertEqual(itaka.total_count(self.html),383)
    def test_no_data(self):
        with self.assertRaises(ValueError): itaka.parse('<html></html>')
class Query(unittest.TestCase):
    def test_countries(self):
        for c in 'ES GR TR EG BG HR IT PT CY AL TN MA MT ME'.split(): self.assertIn(c,itaka.COUNTRIES)
    def test_url(self):
        u=itaka.list_url('ES','2027-05','WAW',2)
        self.assertEqual(u,'https://www.itaka.pl/wyniki-wyszukiwania/wakacje/hiszpania/?dateFrom=01.05.2027&dateTo=14.06.2027'
                           '&departuresByPlane=WAW%2CWMI%2CRDO&order=priceAsc&page=2')
        self.assertIn('departuresByPlane=',itaka.list_url('ES','2027-02',None))   # bez lotniska = wszystkie, nie dojazd wlasny
        self.assertIn('dateTo=14.03.2027',itaka.list_url('ES','2027-02','KTW'))
    def test_city_codes(self):
        for t,c in [('Katowice','KTW'),('Warszawa-Okęcie','WAW'),('Warszawa-Modlin','WAW'),('Warszawa-Radom','WAW'),('Kraków','KRK'),
                    ('Gdańsk','GDN'),('Wrocław','WRO'),('Poznań','POZ'),('Łódź','LCJ'),('Olsztyn-Mazury','OSZ')]: self.assertEqual(itaka.city_code(t),c)
    def test_board(self):
        self.assertEqual(itaka.board('2 posiłki'),'Śniadania i obiadokolacje');self.assertEqual(itaka.board('All inclusive'),'All inclusive')
        self.assertEqual(itaka.board('Wyżywienie zgodnie z programem'),'Wyżywienie zgodnie z programem')
    def test_unknown_no_network(self):
        self.assertEqual(itaka.search('XX','2027-05','KTW')['offers'],[])
        self.assertEqual(itaka.search('ES','2027-05','IEG')['offers'],[])
if __name__=='__main__': unittest.main()
