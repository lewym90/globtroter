"""Adapter Grecos: parse() na prawdziwym, przycietym fragmencie odpowiedzi LoadMoreOffers (bez sieci)."""
import datetime as dt,json,os,re,sys,tempfile,unittest
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import grecos
FX=os.path.join(os.path.dirname(__file__),'fixtures','tours','grecos.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
BOARDS={'All inclusive','Śniadania','Śniadania i obiadokolacje','Pełne wyżywienie','Bez wyżywienia'}
class Parse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FX,encoding='utf-8') as f: cls.text=f.read()
        cls.offers=grecos.parse(cls.text,span=7)
    def test_all_rows(self): self.assertEqual(len(self.offers),len(json.loads(self.text)))
    def test_well_formed(self):
        for o in self.offers:
            self.assertEqual(set(o),KEYS)
            self.assertEqual(o['op'],'grecos');self.assertTrue(o['name'])
            d=dt.date.fromisoformat(o['dep']);r=dt.date.fromisoformat(o['ret'])
            self.assertEqual((r-d).days,7)
            self.assertIn(o['nights'],(7,))
            self.assertIn(o['board'],BOARDS)
            self.assertIsInstance(o['ppp'],int);self.assertGreater(o['ppp'],500)
            self.assertEqual(o['adults'],2);self.assertEqual(o['total'],2*o['ppp'])
            self.assertTrue(o['stars'] is None or 1<=o['stars']<=5)
            self.assertTrue(re.match(r'https://www\.grecos\.pl/wakacje/(grecja|cypr)/[a-z0-9-]+\?offercode=[\w-]+&Adults=2&Children=0$',o['url']),o['url'])
            self.assertEqual(o['kind'],'wypoczynek')
    def test_first(self):
        o=self.offers[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['from'],o['ppp'],o['total'],o['board'],o['place'],o['stars']),
                         ('Coralli Beach','2027-05-03','2027-05-10','KTW',1967,3934,'Bez wyżywienia','Rodos, Pefki',3))
    def test_nights_from_duration(self):
        # Duration 8 ('8 dni') przy 7 dniach wylot->powrot: 7 noclegow
        o=[x for x in self.offers if x['name']=='Hotel Monika'][0]
        self.assertEqual((o['dep'],o['ret'],o['nights']),('2027-05-29','2027-06-05',7))
    def test_half_star_and_board(self):
        self.assertTrue(any(o['stars']==3.5 for o in self.offers))
        self.assertTrue(any(o['board']=='Śniadania i obiadokolacje' for o in self.offers))
    def test_cyprus(self):
        self.assertTrue(any(o['place'].startswith('Cypr') and '/wakacje/cypr/' in o['url'] for o in self.offers))
    def test_no_span_no_return(self):
        o=grecos.parse(self.text)[0];self.assertIsNone(o['ret']);self.assertIsNone(o['nights'])
    def test_bad_rows_skipped(self):
        self.assertEqual(grecos.parse('[{"Hotel_Name":"X"},{}]',span=7),[])
class Query(unittest.TestCase):
    def test_countries(self): self.assertEqual(set(grecos.COUNTRIES),{'GR','CY'})
    def test_unsold_country_no_network(self):
        r=grecos.search('ES','2027-05','KTW');self.assertEqual((r['offers'],r['complete']),([],True))
    def test_unknown_origin_no_network(self):
        self.assertEqual(grecos.search('GR','2027-05','SZZ')['offers'],[])
    def test_query_string(self):
        q=grecos._q('GR',dt.date(2027,5,1),dt.date(2027,6,7),(7,7),'WAW')
        self.assertIn('DateOfDeparture=20270501&DateOfReturn=20270607&DurationInterval=7:7',q)
        self.assertIn('From=WAW,WMI',q);self.assertIn('Dest='+grecos.COUNTRIES['GR'],q)
if __name__=='__main__': unittest.main()
