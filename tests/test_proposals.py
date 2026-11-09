"""Propozycja wyjazdu: link do ogladania, ukryte ceny, serce i komentarz."""
import os,sys,tempfile,unittest
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
import proposals,trips
def item(i='a',name='Teneryfa'):
    return {'id':i,'option':{'dest':{'id':'x','name':name},'dep':'2026-12-21','ret':'2026-12-27','total':2150,'tickets':2011,'hotelEst':{'total':900},'flight':{'out':{'legs':[{'dep':'2026-12-21T11:55'}]}}},
            'plan':{'title':'T','home':{'lat':51.2,'lon':22.5},'timeline':[{'title':'Wyjazd z domu','map':'https://www.google.com/maps/dir/?api=1&origin=51.2,22.5&destination=1,2'}],'cost':[{'label':'Bilety','pln':2011}],'total':3000,'days':[]}}
class Props(unittest.TestCase):
    def test_flow(self):
        r=proposals.create({'title':'Święta','msg':'Wybierz','items':[item(),item('b','Malta')]},'dev-1234567890')
        v=proposals.get(r['view']);self.assertEqual(v['role'],'view');self.assertEqual(len(v['data']['items']),2)
        self.assertEqual(v['data']['items'][0]['option']['total'],2150)
        self.assertNotIn('home',v['data']['items'][0]['plan'])
        self.assertNotIn('map',v['data']['items'][0]['plan']['timeline'][0])
        proposals.vote(r['view'],'b',heart=True);proposals.vote(r['view'],'b',comment='Tak!')
        e=proposals.get(r['edit']);self.assertEqual(e['votes']['b'],{**e['votes']['b'],'heart':True,'comment':'Tak!'})
        with self.assertRaises(PermissionError): proposals.vote(r['edit'],'a',heart=True)
        with self.assertRaises(ValueError): proposals.vote(r['view'],'zz',heart=True)
    def test_hidden_prices(self):
        r=proposals.create({'hide':True,'items':[item()]})
        v=proposals.get(r['view'])['data']['items'][0]
        self.assertNotIn('total',v['option']);self.assertNotIn('tickets',v['option']);self.assertNotIn('hotelEst',v['option']);self.assertNotIn('cost',v['plan'])
        self.assertIn('flight',v['option'])
        self.assertEqual(proposals.get(r['edit'])['data']['items'][0]['option']['total'],2150)
    def test_off(self):
        r=proposals.create({'items':[item()]})
        proposals.setoff(r['edit'],True)
        with self.assertRaises(trips.Denied): proposals.get(r['view'])
        self.assertTrue(proposals.get(r['edit'])['off'])
    def test_limits(self):
        with self.assertRaises(ValueError): proposals.create({'items':[]})
        with self.assertRaises(trips.Denied): proposals.get('x'*20)
if __name__=='__main__': unittest.main()
