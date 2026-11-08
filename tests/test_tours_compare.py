"""Porownanie z wyjazdem na wlasna reke: bez sieci."""
import os,sys,tempfile,time,unittest
from unittest import mock
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
from tours import compare as C
L=lambda a,b,d:[{'airlineName':'Wizz Air','dep':d+'T06:00','arr':d+'T09:00','from':a,'to':b}]
FL={'total':2000,'out':{'legs':L('KTW','HER','2027-06-10')},'back':{'legs':L('HER','KTW','2027-06-17')}}
H={'name':'Aquila Atlantis Hotel','lat':35.34,'lon':25.13,'total':900,'currency':'EUR','stars':5}
X={'op':'itaka','name':'Atlantis','place':'Kreta, Heraklion','dep':'2027-06-10','ret':'2027-06-17','from':'KTW','adults':2,'total':6000,'board':'All inclusive'}
def go(x,hotel=(H,True),fl=([FL],0)):
    j={'state':'run','t':time.time()}
    with mock.patch.object(C,'find_hotel',return_value=hotel),mock.patch.object(C.flights,'roundtrip',return_value=fl),mock.patch.object(C.net,'fx',return_value=4.3):
        h=hotel[0]
        if h: h['totalPln']=round(h['total']*4.3)
        C.run(j,x)
    return j
class Cmp(unittest.TestCase):
    def test_same_hotel(self):
        self.assertTrue(C.same_hotel('Aquila Atlantis','Aquila Atlantis Hotel'))
        self.assertFalse(C.same_hotel('Atlantis Beach','Hotel Galini'))
    def test_full(self):
        j=go(dict(X));r=j['res']
        self.assertEqual(j['state'],'done');self.assertEqual(r['own'],2000+3870);self.assertEqual(r['diff'],6000-5870)
        self.assertTrue(any('All inclusive' in n for n in r['notes']))
    def test_no_flight(self):
        j=go(dict(X),fl=([],0));r=j['res']
        self.assertIsNone(r['flight']);self.assertNotIn('own',r);self.assertTrue(any('czarter' in n for n in r['notes']))
    def test_no_hotel(self):
        with mock.patch('plan.geocode',return_value={'lat':35.3,'lon':25.1}):
            j=go(dict(X),hotel=(None,None))
        self.assertIsNone(j['res']['hotel']);self.assertNotIn('own',j['res'])
    def test_no_return_date(self):
        j=go(dict(X,ret=None));self.assertEqual(j['state'],'err')
if __name__=='__main__': unittest.main()
