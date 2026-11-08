"""Kompas Tour: parse() na prawdziwej stronie listy (offline) i parametry search()."""
import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import kompastour,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','kompastour.html')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=kompastour.parse(text())
    def test_count(self): self.assertEqual(len(self.o),18)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'kompastour');self.assertEqual(o['kind'],'wypoczynek')
            self.assertRegex(o['dep'],r'^2027-06-\d\d$');self.assertGreater(o['ret'],o['dep']);self.assertGreater(o['nights'],0)
            self.assertIn(o['from'],('WAW','KTW'));self.assertEqual(o['ppp']*2,o['total']);self.assertGreater(o['ppp'],500)
            self.assertTrue(o['url'].startswith('https://kompastour.pl/ofr-'));self.assertIn('.html?q=',o['url'])
            self.assertTrue(o['name']);self.assertTrue(o['place']);self.assertTrue(o['board'])
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['stars'],o['place'],o['dep'],o['ret'],o['nights'],o['ppp'],o['board'],o['from']),
            ('SEHER SUN PALACE RESORT & SPA',5,'Side, Colakli','2027-06-02','2027-06-09',7,4243,'All inclusive','KTW'))
    def test_sorted(self):
        p=[o['ppp'] for o in self.o];self.assertEqual(p,sorted(p))
    def test_filters(self):
        self.assertEqual(len(kompastour.parse(text(),origin='KTW')),11);self.assertEqual(len(kompastour.parse(text(),origin='WAW')),7)
        self.assertEqual(kompastour.parse(text(),'2027-07'),[])

class Search(unittest.TestCase):
    def test_params(self):
        seen=[];old=http.get
        http.get=lambda url,data=None,headers=None:(seen.append(url),text())[1]
        try: r=kompastour.search('tr','2027-06','KTW')
        finally: http.get=old
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0],'https://kompastour.pl/l?,Turcja,Katowice,2027-06-01,,,2027-06-30,2,,,,samolot,,,,,,,,,50,1,,,a;price')
        self.assertEqual(len(r['offers']),11);self.assertTrue(r['complete']);self.assertEqual(r['total'],11)
        self.assertIn('Warszawa+-+Modlin',kompastour.list_url('EG','2027-01','WAW'))
    def test_unknown(self):
        self.assertEqual(kompastour.search('GR','2027-06',None)['offers'],[])
        self.assertEqual(kompastour.search('TR','2027-06','XXX')['offers'],[])

if __name__=='__main__': unittest.main()
