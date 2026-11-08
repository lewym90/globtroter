"""Swiat Podrozy Oskar: parse() i search() na prawdziwych odpowiedziach /api/www/offer/ (offline)."""
import json,os,sys,unittest,urllib.parse as up
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import oskar,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','oskar.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def fx():
    with open(FIX,encoding='utf-8') as f: return json.load(f)

class Parse(unittest.TestCase):
    def setUp(self): self.F=fx();self.o=oskar.parse(self.F['list'],'2027-06','KTW')
    def test_rooms_for_two_only(self):
        # 14 produktow; 6 ma najtanszy pokoj 3-osobowy (doplata do wolnego miejsca) -> pominiete w tej odpowiedzi
        self.assertEqual(len(self.F['list']['results']),14);self.assertEqual(len(self.o),8)
        self.assertNotIn('La Mirage',[o['name'] for o in self.o])
        self.assertEqual(len(oskar.parse(self.F['list'],rooms=False)),14)
    def test_shape(self):
        for o in self.o+oskar.parse(self.F['flight']):
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'oskar');self.assertTrue(o['name'])
            self.assertRegex(o['dep'],r'^2027-06-\d\d$');self.assertGreater(o['ret'],o['dep']);self.assertGreater(o['nights'],0)
            self.assertEqual(o['adults'],2);self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int)
            self.assertLessEqual(abs(2*o['ppp']-o['total']),1);self.assertIn(o['kind'],('wypoczynek','objazd','city break'))
            q=dict(up.parse_qsl(up.urlsplit(o['url']).query))
            self.assertTrue(o['url'].startswith('https://oskar.com.pl/oferta/'))
            self.assertEqual((q['adults'],q['children'],q['multi_room'],q['own_transport']),('2','0','false','false'))
            self.assertTrue(q['term_id'].isdigit() and q['stops'].isdigit() and q['room_type'] in ('4','7','8','10'))
            self.assertTrue(o['board'])
    def test_first(self):
        o=self.o[0]
        # strona: 08.06-19.06.2027, Pokoj 2 osobowy, Katowice, 2 x 1929,48 PLN, laczna kwota 3858,96 PLN
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['from'],o['ppp'],o['total'],o['board'],o['place'],o['kind']),
            ('Aparthotel Ino','2027-06-08','2027-06-19',9,'Katowice (autokar)',1929,3859,'Bez wyżywienia','Riwiera Olimpijska, Paralia','wypoczynek'))
        self.assertEqual(o['url'],'https://oskar.com.pl/oferta/wypoczynek/grecja/aparthotel-ino/367?adults=2&children=0&boards=1'
            '&date_range=2027-06-09,2027-06-18&nights=9&term_id=31349&stops=21&own_transport=false&room_type=4&promotion=1247&multi_room=false')
    def test_tour_and_flight(self):
        a=[o for o in self.o if o['name']=='Antyczna Grecja'][0]
        self.assertEqual((a['kind'],a['dep'],a['ret'],a['ppp'],a['total']),('objazd','2027-06-05','2027-06-13',2619,5238))
        self.assertIn('/oferta/objazdowka/grecja/antyczna-grecja/230?',a['url'])
        f=oskar.parse(self.F['flight'],'2027-06','KRK')
        self.assertEqual([o['from'] for o in f],['KRK','Kraków (autokar)','Kraków (autokar)'])
        self.assertEqual(oskar.parse(self.F['flight'],'2027-06','WAW'),[])     # przystanki krakowskie odpadaja dla WAW
    def test_month(self): self.assertEqual(oskar.parse(self.F['list'],'2027-07'),[])
    def test_local_date(self):
        self.assertEqual(oskar.local_date('2027-06-08T05:00:00Z'),'2027-06-08')
        self.assertEqual(oskar.local_date('2027-06-07T22:30:00Z'),'2027-06-08')    # CEST +2
        self.assertEqual(oskar.local_date('2027-01-07T23:30:00Z'),'2027-01-08')    # CET +1
        self.assertEqual(oskar.local_date('2027-01-07T22:30:00Z'),'2027-01-07')

class Search(unittest.TestCase):
    def test_second_query_for_two_person_rooms(self):
        F=fx();seen=[]
        def fake(url,data=None,headers=None,**kw):
            q=dict(up.parse_qsl(up.urlsplit(url).query));seen.append(q)
            return json.dumps(F['rooms2'] if 'room_type' in q else F['list'])
        old=http.get;http.get=fake
        try: r=oskar.search('gr','2027-06','KTW')
        finally: http.get=old
        self.assertEqual(len(seen),2)
        q=seen[0]
        self.assertEqual((q['locations'],q['date_range'],q['stops'],q['ordering'],q['adults']),('18','2027-06-01,2027-06-30','21,1560','full_price','2'))
        self.assertEqual(seen[1]['products'],'972,971,1075,368,750,1260');self.assertEqual(seen[1]['room_type'],'4,7,8,10')
        names=[o['name'] for o in r['offers']]
        self.assertEqual(len(names),12);self.assertIn('Apartamenty Zeus',names);self.assertNotIn('La Mirage',names);self.assertNotIn('Hotel Thermaikos',names)
        self.assertEqual(r['total'],14);self.assertTrue(r['complete'])
        self.assertEqual([o['ppp'] for o in r['offers']],sorted(o['ppp'] for o in r['offers']))
        self.assertEqual(r['url'],'https://oskar.com.pl/oferty?adults=2&locations=18&date_range=2027-06-01,2027-06-30&stops=21,1560')
    def test_unknown(self):
        self.assertEqual(oskar.search('XX','2027-06','KTW')['offers'],[])
        self.assertEqual(oskar.search('GR','2027-06','IEG')['offers'],[])
    def test_maps(self):
        self.assertEqual(oskar.STOPS['WAW'],['60','1567','1568'])
        for c in 'KTW KRK GDN WRO POZ RZE LUZ BZG LCJ SZZ'.split(): self.assertEqual(len(oskar.STOPS[c]),2)
        self.assertEqual(oskar.ROOMS2,[4,7,8,10])

if __name__=='__main__': unittest.main()
