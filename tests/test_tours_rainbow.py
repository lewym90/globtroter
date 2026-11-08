"""Adapter Rainbow: parse() na prawdziwej, przycietej stronie miesiaca (__NUXT_DATA__), bez sieci."""
import datetime as dt,json,os,re,sys,tempfile,unittest
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import rainbow
FX=os.path.join(os.path.dirname(__file__),'fixtures','tours','rainbow.html')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
class Parse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FX,encoding='utf-8') as f: cls.html=f.read()
        cls.offers=rainbow.parse(cls.html,'ES','2027-05','KTW')
    def test_count(self): self.assertEqual(len(self.offers),6)
    def test_well_formed(self):
        for o in self.offers:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'rainbow');self.assertTrue(o['name'])
            d=dt.date.fromisoformat(o['dep']);r=dt.date.fromisoformat(o['ret'])
            self.assertEqual(o['dep'][:7],'2027-05');self.assertEqual((r-d).days,o['nights'])
            self.assertEqual(o['from'],'KTW');self.assertEqual(o['adults'],2)
            self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int);self.assertGreater(o['ppp'],300)
            self.assertLessEqual(abs(o['total']-2*o['ppp']),1)
            self.assertTrue(o['rating'] is None or 0<o['rating']<=10)
            self.assertTrue(o['stars'] is None or 1<=o['stars']<=5)
            self.assertTrue(o['board']);self.assertIn(o['kind'],('wypoczynek','objazd','city break'))
            self.assertTrue(re.match(r'https://r\.pl/[a-z0-9-]+/[a-z0-9-]+\?unikalnyKluczOferty=[A-Za-z0-9%]+&',o['url']),o['url'])
            for bad in ('/szukaj','/api','/rezerwacja'): self.assertNotIn(bad,o['url'])
    def test_first(self):
        o=self.offers[0]
        # strona oferty: 01.05.2027 - 08.05.2027, Katowice, sniadania, 2 318 zl/os., razem 4 636 zl
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['ppp'],o['total'],o['board'],o['place'],o['stars'],o['rating'],o['kind']),
                         ('ALEGRIA Fenals Mar','2027-05-01','2027-05-08',7,2318,4636,'Śniadania','Costa Brava',3,9.8,'wypoczynek'))
    def test_board_from_offer(self):
        # blok ma kilka wyzywien; cena dotyczy tego z PodzialNaPokoje (2 posilki)
        o=[x for x in self.offers if x['name']=='Alegria Cartago Nova'][0];self.assertEqual(o['board'],'Śniadania i obiadokolacje')
    def test_round_trip(self):
        o=[x for x in self.offers if x['kind']=='objazd'];self.assertEqual(len(o),1)
        self.assertEqual((o[0]['name'],o[0]['ppp'],o[0]['total']),('Gran Canaria - Kontynent w miniaturze',4751,9501))
    def test_filters(self):
        self.assertEqual(rainbow.parse(self.html,'ES','2027-05','WAW'),[])   # pierwsze lotnisko w blokach to KTW
        self.assertEqual(rainbow.parse(self.html,'ES','2026-05','KTW'),[])
        self.assertEqual(rainbow.parse(self.html,'GR','2027-05','KTW'),[])
        self.assertEqual(len(rainbow.parse(self.html)),6)
    def test_page_info(self):
        self.assertEqual(rainbow.total_count(self.html),239);self.assertEqual(rainbow.month_range(self.html),['2027-05-01','2027-05-31'])
    def test_zero_count_means_none(self):
        # strona z liczba 0 pokazuje bloki zastepcze - nie wolno ich zwracac
        m=re.search(r'id="__NUXT_DATA__">(.*?)</script>',self.html,re.S);d=json.loads(m.group(1))
        st=d[d[1]['state']];d[st['$sresponseOfertyCount']]=0
        h=self.html[:m.start(1)]+json.dumps(d,ensure_ascii=False)+self.html[m.end(1):]
        self.assertEqual(rainbow.parse(h,'ES','2027-05','KTW'),[])
    def test_no_data(self):
        with self.assertRaises(ValueError): rainbow.parse('<html></html>')
class Query(unittest.TestCase):
    def test_countries(self):
        for c in 'ES GR TR EG BG HR IT PT CY AL TN MA MT ME'.split(): self.assertIn(c,rainbow.COUNTRIES)
    def test_url(self):
        self.assertEqual(rainbow.list_url('ES','2027-05','WAW',3),'https://r.pl/hiszpania/wakacje-maj?cena=sum&wybraneSkad=WAW,WMI&strona=3')
        self.assertEqual(rainbow.list_url('TR','2027-10',None),'https://r.pl/turcja/wakacje-pazdziernik?cena=sum')
        self.assertEqual(rainbow.list_url('GR','2027-06','OSZ'),'https://r.pl/grecja/wakacje-czerwiec?cena=sum&wybraneSkad=SZY')
    def test_board(self):
        self.assertEqual(rainbow.board('3 posiłki'),'Pełne wyżywienie');self.assertEqual(rainbow.board('Wg programu imprezy'),'Wg programu imprezy')
    def test_unknown_no_network(self):
        self.assertEqual(rainbow.search('XX','2027-05','KTW')['offers'],[])
        self.assertEqual(rainbow.search('ES','2027-05','IEG')['offers'],[])
if __name__=='__main__': unittest.main()
