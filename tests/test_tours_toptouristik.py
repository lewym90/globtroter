"""TOP Touristik (MerlinX): parse() na prawdziwej odpowiedzi wapi (offline), captcha -> Blocked."""
import json,os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import toptouristik,merlinx,http
FIX=os.path.join(os.path.dirname(__file__),'fixtures','tours','toptouristik.json')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def text():
    with open(FIX,encoding='utf-8') as f: return f.read()

class Parse(unittest.TestCase):
    def setUp(self): self.o=toptouristik.parse(text())
    def test_count(self): self.assertEqual(len(self.o),5)
    def test_shape(self):
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['op'],'toptouristik');self.assertEqual(o['kind'],'wypoczynek')
            self.assertRegex(o['dep'],r'^2027-06-\d\d$');self.assertGreater(o['ret'],o['dep']);self.assertGreater(o['nights'],0)
            self.assertEqual(o['from'],'KTW');self.assertEqual(o['adults'],2);self.assertLessEqual(abs(o['ppp']*2-o['total']),1)
            self.assertTrue(o['url'].startswith('https://toptouristik.pl/index/samolotem/details?'));self.assertTrue(o['board'])
    def test_first(self):   # 'trp_depDateFull': '09.06.2027' (TOP pisze date cyframi)
        o=self.o[0]
        self.assertEqual((o['name'],o['dep'],o['ret'],o['nights'],o['ppp'],o['total'],o['stars'],o['place']),
                         ('Bonita Beach','2027-06-09','2027-06-13',4,955,1909,3,'Złote Piaski'))
        self.assertEqual(self.o[2]['board'],'Śniadania i obiadokolacje');self.assertEqual(self.o[3]['stars'],2)
    def test_modlin_alias(self):   # TOP podaje wylot jako 'Modlin'
        d=json.loads(text())
        for r in d['d'][0]['d']['roffers']: r['trp_depDesc']='Modlin'
        o=toptouristik.parse(json.dumps(d));self.assertEqual({x['from'] for x in o},{'WAW'})
    def test_foreign_departure_dropped(self):
        d=json.loads(text())
        for r in d['d'][0]['d']['roffers']: r['trp_depDesc']='Berlin'
        self.assertEqual(toptouristik.parse(json.dumps(d)),[])

class Blocked(unittest.TestCase):
    def test_captcha_html(self):
        with self.assertRaises(http.Blocked): toptouristik.parse('<html><div class="cf-turnstile"></div> captcha</html>')
    def test_captcha_error(self):
        with self.assertRaises(http.Blocked): toptouristik.parse('{"d":[{"e":"captcha required"}],"status":"ok"}')
    def test_other_error(self):
        with self.assertRaises(IOError): toptouristik.parse('{"d":[{"e":"no data"}]}')
    def test_search_raises(self):
        old=http.get;merlinx._wid[toptouristik.BASE]='48634210'
        http.get=lambda url,data=None,headers=None:'<html>Przepisz kod captcha</html>'
        try:
            with self.assertRaises(http.Blocked): toptouristik.search('BG','2027-06','KTW')
        finally: http.get=old;merlinx._wid.pop(toptouristik.BASE,None)

if __name__=='__main__': unittest.main()
