"""Dertour (MerlinX): parse() na prawdziwej odpowiedzi wapi (offline) i parametry search()."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import dertour,merlinx,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','dertour.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=dertour.parse(text())
    def test_count(self): self.assertEqual(len(self.o),5)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'dertour');self.assertEqual(o['kind'],'wypoczynek')
            self.assertTrue(o['name']);self.assertRegex(o['dep'],r'^2027-05-\d\d$');self.assertRegex(o['ret'],r'^2027-05-\d\d$')
            self.assertGreater(o['ret'],o['dep']);self.assertGreater(o['nights'],0)
            self.assertEqual(o['from'],'KTW');self.assertIsInstance(o['ppp'],int);self.assertIsInstance(o['total'],int)
            self.assertEqual(o['adults'],2);self.assertLessEqual(abs(o['ppp']*2-o['total']),1)
            self.assertTrue(o['url'].startswith('https://www.dertour.pl/index/wakacje_samolotem/details?'))
            self.assertIn('&id=',o['url']);self.assertTrue(o['board']);self.assertIsNone(o['rating'])
    def test_first(self):   # 'trp_depDateFull': '14 Maj 2027' (Dertour pisze miesiac slowem)
        o=self.o[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['ppp'],o['total'],o['stars']),
                         ('htop Royal Sun Suites','2027-05-14','2027-05-20',6,2339,4678,4))
        self.assertEqual(o['place'],'Costa Brava, Santa Susanna');self.assertEqual(o['board'],'Bez wyżywienia')
        self.assertEqual(self.o[1]['board'],'Śniadania')
    def test_month_filter(self): self.assertEqual(dertour.parse(text(),'2027-06'),[])
    def test_origin_filter(self):
        self.assertEqual(len(dertour.parse(text(),origin='KTW')),5);self.assertEqual(dertour.parse(text(),origin='WAW'),[])
    def test_dates(self):
        for s,v in [('14 Maj 2027','2027-05-14'),('03 Paź 2027','2027-10-03'),('1 Sty 2027','2027-01-01'),('15.06.2027','2027-06-15'),('xx',None)]:
            self.assertEqual(merlinx._date(s),v)

class Search(unittest.TestCase):
    def setUp(self):
        self.seen=[];self.old=http.get;merlinx._wid.pop(dertour.BASE,None)
        def fake(url,data=None,headers=None):
            self.seen.append((url,data))
            if '/wapi/' not in url: return '<div data-widgetname="Widget\\Results\\TripListWidget"\n data-id="64939221"></div>'
            d=json.loads(text());d['d'][0]['d']['moreOffersAvailable']=len(self.seen)<4;return json.dumps(d)
        http.get=fake
    def tearDown(self): http.get=self.old;merlinx._wid.pop(dertour.BASE,None)
    def test_paging_and_params(self):
        r=dertour.search('es','2027-05','KTW')
        self.assertEqual(len(self.seen),4)   # strona (id widgetu) + 3 zapytania wapi
        u,b=self.seen[1]
        self.assertIn('/index/wakacje_samolotem/wapi/?',u);self.assertIn('des%5B%5D=15%3A',u)
        self.assertIn('depd=01.05.2027',u);self.assertIn('retd=31.05.2027',u);self.assertIn('dn=0x4b61746f77696365',u)
        self.assertIn('d%5B0%5D%5Bm%5D=64939221',b);self.assertIn('getupdate',b);self.assertIn('allPages',b)
        self.assertIn('moreoffers',self.seen[2][1]);self.assertIn('page%5D=2',self.seen[2][1])
        self.assertTrue(r['complete']);self.assertEqual(len(r['offers']),5);self.assertEqual(r['total'],5)   # powtorki usuniete
        self.assertTrue(r['url'].startswith('https://www.dertour.pl/index/wakacje_samolotem/?'))
    def test_limit(self):
        r=dertour.search('ES','2027-05','KTW',limit_pages=1)
        self.assertFalse(r['complete']);self.assertIsNone(r['total'])
    def test_waw_group(self):
        dertour.search('ES','2027-05','WAW')
        u=self.seen[1][0]
        for c in ('Warszawa','Warszawa - Modlin','Warszawa - Radom'): self.assertIn(merlinx.hexname(c),u)
    def test_any_origin_only_poland(self):
        dertour.search('ES','2027-05',None)
        u=self.seen[1][0];self.assertIn(merlinx.hexname('Katowice'),u);self.assertNotIn(merlinx.hexname('Berlin'),u)
    def test_unknown(self):
        self.assertEqual(dertour.search('ES','2027-05','XXX')['offers'],[])
        self.assertEqual(dertour.search('EG','2027-05',None)['offers'],[]);self.assertEqual(self.seen,[])

if __name__=='__main__': unittest.main()
