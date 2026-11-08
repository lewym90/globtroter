"""Nomade: parse() na prawdziwym fragmencie listy (offline); tylko polskie lotniska."""
import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import nomade,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','nomade.html')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=nomade.parse(text())
    def test_count(self): self.assertEqual(len(self.o),6)   # 8 w pliku, Berlin i Wieden odrzucone
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'nomade')
            self.assertRegex(o['dep'],r'^\d{4}-\d\d-\d\d$');self.assertGreater(o['ret'],o['dep']);self.assertGreater(o['nights'],0)
            self.assertIn(o['from'],('WAW','KRK','POZ'));self.assertEqual(o['ppp']*2,o['total'])
            self.assertTrue(o['url'].startswith('https://nomade.pl/'));self.assertIn('TermID=',o['url'])
            self.assertIn('DateFrom='+o['dep'],o['url']);self.assertNotIn('&amp;',o['url'])
            self.assertNotIn('*',o['name']);self.assertTrue(o['board'])
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['stars'],o['place'],o['dep'],o['ret'],o['nights'],o['ppp'],o['board'],o['from']),
            ('Myconian Ambassador Relais & Chateaux Hotel',5,'Mykonos','2027-05-04','2027-05-07',3,3402,'Śniadania','WAW'))
    def test_filters(self):
        self.assertEqual(len(nomade.parse(text(),'2027-05')),3)
        self.assertEqual([x['from'] for x in nomade.parse(text(),origin='KRK')],['KRK'])
        self.assertEqual(nomade.parse(text(),origin='KTW'),[])

class Search(unittest.TestCase):
    def test_params(self):
        seen=[];old=http.get
        http.get=lambda url,data=None,headers=None:(seen.append(url),text())[1]
        try: r=nomade.search('gr','2027-05','WAW');r2=nomade.search('GR','2027-05',None)
        finally: http.get=old
        self.assertIn('StartDateFrom=2027-05-01',seen[0]);self.assertIn('StartDateTo=2027-05-31',seen[0])
        self.assertIn('DestinationID=313',seen[0]);self.assertIn('DepartureStationID=83,146',seen[0])
        self.assertIn('DepartureStationID=83,146,76,162,78',seen[1])
        self.assertEqual(len(r['offers']),3);self.assertTrue(r['complete']);self.assertEqual(r['total'],3)
        self.assertTrue(r['url'].startswith('https://nomade.pl/wyszukiwane-wycieczki?'))
    def test_unknown(self):
        self.assertEqual(nomade.search('GR','2027-05','KTW')['offers'],[])
        self.assertEqual(nomade.search('TR','2027-05',None)['offers'],[])

if __name__=='__main__': unittest.main()
