"""Matimpex (MerlinX, city breaki): parse() na prawdziwej odpowiedzi wapi (offline)."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import matimpex,merlinx,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','matimpex.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=matimpex.parse(text())
    def test_count(self): self.assertEqual(len(self.o),5)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'matimpex');self.assertEqual(o['kind'],'city break')
            self.assertRegex(o['dep'],r'^2027-03-\d\d$');self.assertGreater(o['ret'],o['dep']);self.assertEqual(o['nights'],3)
            self.assertIn(o['from'],('WAW','KRK'));self.assertEqual(o['ppp']*2,o['total'])
            self.assertTrue(o['url'].startswith('https://www.matimpex.pl/index/city_breaki/details?'))
    def test_first(self):
        o=self.o[0]
        self.assertEqual((o['name'],o['place'],o['dep'],o['ret'],o['ppp'],o['total'],o['board'],o['from']),
                         ('City Break w Wenecji 4 dni','Wenecja','2027-03-12','2027-03-15',2199,4398,'Śniadania','WAW'))
        self.assertEqual(self.o[1]['place'],'Sycylia, Katania')
    def test_modlin_is_waw(self):   # 'Warszawa - Modlin' w fixture
        self.assertEqual(self.o[4]['from'],'WAW')
    def test_origin_filter(self):
        self.assertEqual(len(matimpex.parse(text(),origin='KRK')),2)

class Search(unittest.TestCase):
    def test_params(self):
        seen=[];old=http.get;merlinx._wid[matimpex.BASE]='161387871'
        def fake(url,data=None,headers=None):
            seen.append(url);d=json.loads(text());d['d'][0]['d']['moreOffersAvailable']=False;return json.dumps(d)
        http.get=fake
        try: r=matimpex.search('IT','2027-03',None)
        finally: http.get=old;merlinx._wid.pop(matimpex.BASE,None)
        self.assertEqual(len(seen),1);self.assertIn('oft=F',seen[0]);self.assertIn('des%5B%5D=44%3A',seen[0])
        self.assertTrue(r['complete']);self.assertEqual(r['total'],5)
    def test_unknown(self): self.assertEqual(matimpex.search('TR','2027-03',None)['offers'],[])

if __name__=='__main__': unittest.main()
