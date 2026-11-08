"""Wakacje z biurem: plan od hotelu i lotow podanych przez uzytkownika, bez sieci."""
import os,sys,tempfile,unittest
from unittest import mock
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
import plan
B=lambda **k:{**{'hotel':{'name':'Hotel','lat':35.32,'lon':25.38,'label':'Hersonissos'},'out':{'date':'2027-06-10','time':'06:30','arr':'09:40','from':'KTW','to':'HER'},
   'back':{'date':'2027-06-17','time':'11:40','arr':'13:55','from':'HER','to':'KTW'},'board':'ai','mix':'half','home':{'lat':50.26,'lon':19.02}},**k}
def run(b):
    with mock.patch.object(plan,'car_route',return_value={'km':30,'min':30,'fuel':40,'map':'https://x'}),mock.patch.object(plan,'weather',return_value={}),mock.patch.object(plan,'holidays',return_value=[]),mock.patch.object(plan.net,'fx',return_value=4.3),mock.patch.object(plan,'sun',return_value={}),mock.patch.object(plan,'restaurants',return_value=[]):
        return plan.tour(b)
class Tour(unittest.TestCase):
    def test_days_and_edges(self):
        p=run(B());D=p['days']
        self.assertEqual(len(D),8);self.assertEqual(D[0]['stops'],[]);self.assertEqual(D[-1]['stops'],[])
        self.assertTrue(any(d['kind']=='rest' for d in D));self.assertTrue(any(d['stops'] for d in D))
    def test_all_inclusive_no_meals(self):
        p=run(B())
        self.assertFalse(any(s.get('meal') for d in p['days'] for s in d['stops']))
    def test_room_only_has_meals(self):
        p=run(B(board='ro',mix='many'))
        self.assertTrue(any(s.get('meal') for d in p['days'] for s in d['stops']))
    def test_far_stops_by_car(self):
        p=run(B(mix='many'))
        self.assertTrue(any(s.get('by')=='car' for d in p['days'] for s in d['stops']))
    def test_timeline_order(self):
        p=run(B());at=[x['at'] for x in p['timeline']]
        self.assertEqual(at,sorted(at));self.assertIn('Wylot',[x['title'] for x in p['timeline']])
    def test_overnight_arrival(self):
        p=run(B(out={'date':'2027-06-10','time':'22:30','arr':'02:10','from':'KTW','to':'HER'}))
        self.assertTrue(p['option']['arrive'].startswith('2027-06-11'))
    def test_price_in_budget(self):
        p=run(B(price='7800',agency='Itaka'))
        self.assertEqual(p['cost'][0]['pln'],7800);self.assertEqual(p['cost'][0]['sure'],'fact')
    def test_bad_airport(self):
        with self.assertRaises(ValueError): run(B(out={'date':'2027-06-10','time':'06:30','arr':'09:40','from':'XXX','to':'HER'}))
    def test_return_before_arrival(self):
        with self.assertRaises(ValueError): run(B(back={'date':'2027-06-09','time':'11:40','arr':'13:55','from':'HER','to':'KTW'}))
    def test_no_hotel(self):
        with self.assertRaises(ValueError): run(B(hotel={}))
if __name__=='__main__': unittest.main()
