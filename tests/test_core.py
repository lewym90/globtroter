"""Testy logiki, bez sieci. Uruchom: python3 -m unittest discover tests"""
import datetime as dt,json,os,sys,tempfile,unittest
os.environ['GLOBTROTER_DATA']=tempfile.mkdtemp()
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
import access,climate,flights,geo,hotels,links,plan,search
F=lambda **k:{'price':k.get('price',100),'stops':0,'min':120,'legs':k.get('legs',[{'airline':'FR','no':'1','from':'KRK','to':'BCN','dep':'2027-02-10T06:10','arr':'2027-02-10T09:00','min':170}])}
class Valid(unittest.TestCase):
    def test_ok(self): self.assertTrue(flights.valid_flight(F(),['KRK'],['BCN'],'2027-02-10'))
    def test_zero_price(self): self.assertFalse(flights.valid_flight(F(price=0)))
    def test_none_price(self): self.assertFalse(flights.valid_flight(F(price=None)))
    def test_wrong_day(self): self.assertFalse(flights.valid_flight(F(),day='2027-02-11'))
    def test_wrong_airport(self): self.assertFalse(flights.valid_flight(F(),o=['WAW']))
    def test_broken_chain(self):
        L=[{'airline':'X','no':'1','from':'KRK','to':'MUC','dep':'2027-02-10T06:10','arr':'x','min':60},{'airline':'X','no':'2','from':'FRA','to':'BCN','dep':'2027-02-10T09:10','arr':'x','min':60}]
        self.assertFalse(flights.valid_flight(F(legs=L)))
class Access(unittest.TestCase):
    def test_parking_week(self): self.assertEqual(access.parking('KRK',7),150)
    def test_parking_override(self): self.assertEqual(access.parking('KRK',7,70),70)
    def test_parking_min_days(self): self.assertEqual(access.parking('KRK',1),access.parking('KRK',3))
    def test_parking_long(self): self.assertGreater(access.parking('KRK',14),150)
    def test_car(self):
        c=access.cost('car','KRK',{'km':300,'min':200},7,2,{'consumption':8,'fuelPrice':6,'tollOneWay':18})
        self.assertEqual(c['total'],round(600*8/100*6)+150+36)
    def test_dropoff_four_runs(self):
        c=access.cost('dropoff','KRK',{'km':100,'min':60},7,2,{'consumption':10,'fuelPrice':6,'tollOneWay':0})
        self.assertEqual(c['total'],240)
    def test_public_scales(self):
        a=access.cost('public','KRK',{'km':300,'min':200},7,1,{})['total'];b=access.cost('public','KRK',{'km':300,'min':200},7,2,{})['total']
        self.assertEqual(b,a*2)
class Windows(unittest.TestCase):
    def fut(self,n): return (dt.date.today()+dt.timedelta(days=n)).isoformat()
    def test_dates(self):
        a,b,n,m=search.window({'mode':'dates','from':self.fut(10),'to':self.fut(17)});self.assertEqual(n,[7]);self.assertEqual(a,b)
    def test_back_before(self):
        with self.assertRaises(ValueError): search.window({'mode':'dates','from':self.fut(10),'to':self.fut(9)})
    def test_past(self):
        with self.assertRaises(ValueError): search.window({'mode':'dates','from':'2020-01-01','to':'2020-01-05'})
    def test_month_no_past(self):
        t=dt.date.today();a,b,n,m=search.window({'mode':'month','year':t.year,'month':t.month,'nights':[7]}) if t.day<27 else (t+dt.timedelta(1),t,[7],t.month)
        self.assertGreater(a,t)
    def test_samples_in_window(self):
        a=dt.date(2027,2,1);b=dt.date(2027,2,28)
        for d in search.sample_days(a,b): self.assertTrue(a<=d<=b)
class Leave(unittest.TestCase):
    def test_before_flight(self):
        lh,buf=search.leave_home('2027-02-10T06:10',{'km':300,'min':180},'car')
        self.assertEqual(lh,'2027-02-09T23:58') # 120+25+(207+20) = 6 h 12 min
    def test_non_schengen_more(self):
        a,_=search.leave_home('2027-02-10T12:00',{'km':10,'min':20},'car',True);b,_=search.leave_home('2027-02-10T12:00',{'km':10,'min':20},'car',False)
        self.assertLess(b,a)
class Climate(unittest.TestCase):
    D={'climate':{'tmax':[12]*6+[32]*6,'tmin':[5]*12,'rain':[50]*12,'sea':[13]*6+[26]*6}}
    def test_winter_beach_bad(self):
        s,why=climate.fit(self.D,2,'beach');self.assertLess(s,.55);self.assertIn('zimno',why)
    def test_summer_beach_good(self):
        s,_=climate.fit(self.D,8,'beach');self.assertGreater(s,.7)
    def test_no_data_is_unknown(self): self.assertIsNone(climate.fit({},2,'beach')[0])
class Links(unittest.TestCase):
    def test_ryanair_first(self):
        L=links.flight_links('KRK','BCN','2027-02-10','2027-02-17',2,0,'FR');self.assertEqual(L[0]['site'],'Ryanair');self.assertIn('dateOut=2027-02-10',L[0]['url'])
    def test_skyscanner_dates(self):
        L=links.flight_links('KRK','BCN','2027-02-10','2027-02-17',1,0);self.assertIn('/krk/bcn/270210/270217/',[x for x in L if x['site']=='Skyscanner'][0]['url'])
    def test_hotel_dates(self):
        self.assertIn('checkin=2027-02-10',links.hotel_links('Hotel X','Rome','2027-02-10','2027-02-14',2,0)['Booking.com'])
class Rooms(unittest.TestCase):
    def test_rooms(self):
        self.assertEqual(hotels.rooms_for(2,0),1);self.assertEqual(hotels.rooms_for(3,0),2);self.assertEqual(hotels.rooms_for(2,1),1);self.assertEqual(hotels.rooms_for(4,2),2)
class Cluster(unittest.TestCase):
    def test_all_items_kept(self):
        it=[{'lat':41.9+i*.01,'lon':12.5,'l':10-i,'q':str(i)} for i in range(9)]
        g=plan.cluster(it,(41.9,12.5),3);self.assertEqual(sum(len(x) for x in g),9)
    def test_order_visits_all(self):
        it=[{'lat':1,'lon':1},{'lat':0.1,'lon':0.1}];self.assertEqual(plan.order(it,(0,0))[0]['lat'],0.1)
if __name__=='__main__': unittest.main()
