"""Regent: parse_list() i parse() na prawdziwych stronach (offline)."""
import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import http,regent
D=os.path.join(os.path.dirname(__file__),'fixtures','tours')
KEYS={'op','name','stars','place','dep','ret','nights','board','from','ppp','adults','total','rating','kind','url'}
def read(n):
    with open(os.path.join(D,n),encoding='utf-8') as f: return f.read()

class List(unittest.TestCase):
    def test_trips(self):
        t=regent.parse_list(read('regent_list.html'))
        self.assertEqual(len(t),9)
        self.assertEqual(t[0]['name'],'City Break - Magia Barcelony - 4 dni');self.assertEqual(t[0]['place'],'Barcelona')
        self.assertEqual(t[0]['board'],'HB')
        codes=[i for c,i,u in t[0]['deps']]
        self.assertEqual(codes,['WMI','WRO','KRK','KTW','WAW','GDN','POZ'])
        for x in t:
            for c,i,u in x['deps']: self.assertTrue(u.startswith('https://www.regent.pl/oferta_'),u)

class Parse(unittest.TestCase):
    def setUp(self): self.o=regent.parse(read('regent.html'),'City Break - Magia Barcelony - 4 dni','Barcelona','HB','KTW')
    def test_all(self):
        self.assertEqual(len(self.o),42)
        for o in self.o:
            self.assertEqual(set(o),KEYS);self.assertEqual(o['kind'],'city break');self.assertEqual(o['op'],'regent')
            self.assertEqual(o['nights'],3);self.assertEqual(o['total'],2*o['ppp']);self.assertGreater(o['ppp'],1000)
            self.assertEqual(o['board'],'Śniadania i obiadokolacje');self.assertEqual(o['from'],'KTW')
            self.assertRegex(o['url'],r'^https://regent\.pl/webit\.php\?onepage=20&adults=2&.*md=[0-9a-f]{32}$')
    def test_first_row_skips_strike_and_omnibus(self):
        o=self.o[0];self.assertEqual((o['dep'],o['ret'],o['ppp']),('2027-03-04','2027-03-07',2055))
    def test_month(self):
        m=regent.parse(read('regent.html'),ym='2027-05')
        self.assertTrue(m);self.assertTrue(all(o['dep'].startswith('2027-05') for o in m))
        self.assertEqual(m[0]['from'],'Katowic')   # bez podanego kodu: tekst z naglowka tabeli

class Search(unittest.TestCase):
    def test_flow(self):
        seen=[]
        def fake(url,data=None,headers=None):
            seen.append(url);return read('regent_list.html' if 'destinationto' in url else 'regent.html')
        old=http.get;http.get=fake
        try: r=regent.search('ES','2027-05','KTW')
        finally: http.get=old
        self.assertIn('destinationto=REGENT|HISZPANIA|&wylot=01.05.2027&powrot=14.06.2027',seen[0])
        self.assertTrue(all('z_katowic' in u for u in seen[1:]));n=sum(1 for t in regent.parse_list(read('regent_list.html')) for c,i,u in t['deps'] if i=='KTW');self.assertEqual(len(seen),1+n)
        self.assertTrue(r['complete']);self.assertTrue(all(o['dep'].startswith('2027-05') and o['from']=='KTW' for o in r['offers']))
        p=[o['ppp'] for o in r['offers']];self.assertEqual(p,sorted(p))
    def test_unknown(self):
        self.assertEqual(regent.search('TR','2027-05',None)['offers'],[])

if __name__=='__main__': unittest.main()
