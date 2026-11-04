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
class GoogleLink(unittest.TestCase):
    def test_dates_in_words(self):
        from urllib.parse import unquote_plus
        u=unquote_plus(links.hotel_links('Catania Inn','Catania','2027-05-24','2027-05-29',2,0)['Google'])
        self.assertIn('Catania Inn Catania from May 24 2027 to May 29 2027',u)
class Rooms(unittest.TestCase):
    def test_rooms(self):
        self.assertEqual(hotels.rooms_for(2,0),1);self.assertEqual(hotels.rooms_for(3,0),2);self.assertEqual(hotels.rooms_for(2,1),1);self.assertEqual(hotels.rooms_for(4,2),2)
class Cluster(unittest.TestCase):
    def test_all_items_kept(self):
        it=[{'lat':41.9+i*.01,'lon':12.5,'l':10-i,'q':str(i)} for i in range(9)]
        g=plan.cluster(it,(41.9,12.5),3);self.assertEqual(sum(len(x) for x in g),9)
    def test_order_visits_all(self):
        it=[{'lat':1,'lon':1},{'lat':0.1,'lon':0.1}];self.assertEqual(plan.order(it,(0,0))[0]['lat'],0.1)
class Dest(unittest.TestCase):
    def test_city_ignores_style(self):
        geo.BYID['x']={'id':'x','name':'X','cc':'IT','air':['FCO'],'tags':['city'],'climate':{'tmax':[12]*12,'tmin':[5]*12,'rain':[1]*12}}
        ds,notes=search.pick_dests({'dest':{'mode':'city','ids':['x'],'style':'beach'}},2);self.assertEqual(notes,[]);self.assertEqual(len(ds),1)
class Season(unittest.TestCase):
    def test_real_data(self):
        p=os.path.join(os.path.dirname(__file__),'..','data','destinations.json');ds=json.load(open(p,encoding='utf8'));B={d['name']:d for d in ds}
        g=lambda n,m,st:climate.fit(B[n],m,st)[0]
        self.assertGreaterEqual(g('Teneryfa',2,'beach'),.55);self.assertLess(g('Gdańsk',2,'beach'),.2);self.assertLess(g('Split',2,'beach'),.55)
        self.assertGreaterEqual(g('Split',7,'beach'),.8);self.assertGreaterEqual(g('Chamonix',2,'ski'),.5);self.assertLess(g('Chamonix',7,'ski'),.1)
class Confirm(unittest.TestCase):
    def fl(self,o,d,day,p): return {'price':p,'stops':0,'min':120,'legs':[{'airline':'FR','no':'1','from':o,'to':d,'dep':day+'T06:10','arr':day+'T09:00','min':170}]}
    def setUp(self): self.r,self.o=flights.roundtrip,flights.oneway
    def tearDown(self): flights.roundtrip,flights.oneway=self.r,self.o
    def C(self): return {'o':'WMI','d':'BCN','dep':'2027-03-06','ret':'2027-03-13','one':250,'grid':[{'dep':'2027-03-06','ret':'2027-03-13','price':250},{'dep':'2027-03-09','ret':'2027-03-16','price':300}]}
    def test_falls_back_to_separate(self):
        flights.roundtrip=lambda *a,**k:([],0)
        flights.oneway=lambda o,d,day,*a,**k:([self.fl(o[0],d[0],day,200 if o[0]=='WMI' else 150)],0)
        r,_=search.confirm(self.C(),2,0,None);self.assertEqual(r[0]['total'],350);self.assertTrue(r[0]['separate'])
    def test_next_date(self):
        flights.roundtrip=lambda o,d,dep,ret,*a,**k:([],0) if dep=='2027-03-06' else ([{'total':700,'out':self.fl(o,d,dep,700),'back':self.fl(d,o,ret,700)}],0)
        flights.oneway=lambda *a,**k:([],0)
        c=self.C();r,_=search.confirm(c,2,0,None);self.assertEqual(c['dep'],'2027-03-09');self.assertEqual(r[0]['total'],700)
    def test_nothing_is_empty(self):
        flights.roundtrip=lambda *a,**k:([],0);flights.oneway=lambda *a,**k:([],0)
        self.assertEqual(search.confirm(self.C(),2,0,None)[0],[])
class FoodParse(unittest.TestCase):
    def test_parse(self):
        sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','tools'));import build_food as b
        L=b.parse({'elements':[{'lat':1,'lon':2,'tags':{'name':'A','cuisine':'pizza;italian','website':'http://a.pl','opening_hours':'Mo 10:00'}},{'type':'way','center':{'lat':3,'lon':4},'tags':{'name':'B'}},{'lat':1,'lon':2,'tags':{'name':'A'}},{'lat':1,'lon':2,'tags':{'cuisine':'x'}},{'lat':1,'lon':2,'tags':{'name':'Zamk','opening_hours':'off'}}]})
        self.assertEqual([x['n'] for x in L],['A','B']);self.assertEqual(L[0]['c'],'pizza, italian');self.assertEqual(L[0]['h'],'Mo 10:00')
class HotelList(unittest.TestCase):
    def setUp(self):
        self.p,self.f,self.g,self.u=hotels._page,hotels.net.fetch_json,hotels.store.get,hotels.store.put
        hotels.store.get=lambda *a:(None,None);hotels.store.put=lambda *a:None
    def tearDown(self): hotels._page,hotels.net.fetch_json,hotels.store.get,hotels.store.put=self.p,self.f,self.g,self.u
    def test_snapshot_first(self):
        hotels.net.fetch_json=lambda *a,**k:{'r':[{'key':'a'}]};hotels._page=lambda *a:self.fail('nie pytaj zrodla')
        self.assertEqual(hotels._list({'id':'x','ta':'1'}),[{'key':'a'}])
    def test_all_down_is_error_not_empty(self):
        def no(*a,**k): raise hotels.net.SourceDown('x')
        hotels.net.fetch_json=no;hotels._page=lambda *a:None
        with self.assertRaises(hotels.net.SourceDown): hotels._list({'id':'x','ta':'1'})
    def test_search_reports_source_down(self):
        def no(*a,**k): raise hotels.net.SourceDown('x')
        hotels.net.fetch_json=no;hotels._page=lambda *a:None
        geo.BYID['y']={'id':'y','en':'Y','ta':'1','tags':['city'],'lat':1,'lon':1}
        hotels.ghotels.deep=lambda *a:None;r=hotels.search('y','2027-05-05','2027-05-12',2,0);self.assertTrue(r['sourceDown']);self.assertTrue(r['fallback'])
class GoogleHotels(unittest.TestCase):
    def rec(self,a=(2027,6,10),b=(2027,6,17),offer=True):
        r=[None]*27;r[1]='Senses';r[2]=[[43.14,16.37]];r[3]=['Hotel 5-gwiazdkowy',5];r[7]=[[4.5,1000]];r[20]='abc'
        o=[None]*11;o[1]=['$150','$169',149.7,None,150];o[10]=['$1,048','$1,182']
        r[6]=[None,[[150,0],None,None,'USD',[list(a),list(b),7,1]],o if offer else None];return r
    def test_parse(self):
        import ghotels
        h=ghotels.parse(self.rec(),'2027-06-10','2027-06-17');self.assertEqual((h['night'],h['total'],h['rating'],h['stars']),(150,1048,4.5,5))
    def test_wrong_dates_rejected(self):
        import ghotels
        self.assertIsNone(ghotels.parse(self.rec(a=(2026,11,9)),'2027-06-10','2027-06-17'))
    def test_no_offer_rejected(self):
        import ghotels
        self.assertIsNone(ghotels.parse(self.rec(offer=False),'2027-06-10','2027-06-17'))
    def test_query_dates(self):
        import ghotels
        self.assertEqual(ghotels.query('Hvar','2026-12-28','2027-01-04'),'hotels in Hvar from December 28 2026 to January 4 2027')
class Amen(unittest.TestCase):
    def test_parse(self):
        import ghotels
        a=ghotels.amenities('<div class="x">  Amenities for Hotel Park, a 4-star hotel.: Free breakfast, Free Wi-Fi, Outdoor pool,  <div>')
        self.assertEqual(a['Hotel Park'][:2],['Free breakfast','Free Wi-Fi']);self.assertEqual(ghotels._breakfast(a['Hotel Park']),'free')
        self.assertEqual(ghotels._breakfast(['Breakfast']),'paid');self.assertIsNone(ghotels._breakfast(['Bar']))
class Merge(unittest.TestCase):
    def test_no_duplicates_and_breakfast_joined(self):
        ox,og=hotels.search_xotelo,hotels.search_google
        base=dict(score=50,overBudget=False,prices=[{'site':'Agoda.com','night':100,'total':700,'url':'u'}],bestTotal=700,bestNight=100,breakfast=False)
        hotels.search_xotelo=lambda *a,**k:{'hotels':[dict(base,name='Hotel Park',key='x',prices=list(base['prices']))],'nights':7}
        hotels.search_google=lambda *a,**k:{'hotels':[dict(base,name='HOTEL PARK!',key='g',breakfast=True,breakfastPaid=False,amen=['basen'],bestTotal=600,bestNight=86,prices=[{'site':'G','night':86,'total':600,'url':'u'}]),dict(base,name='Inny',key='h',breakfastPaid=False,amen=[])],'nights':7}
        try:
            geo.BYID['z']={'id':'z','en':'Z','ta':'1','tags':['city'],'lat':1,'lon':1}
            r=hotels.search('z','2027-06-10','2027-06-17',2,0)
            self.assertEqual(len(r['hotels']),2);h=[x for x in r['hotels'] if x['key']=='x'][0]
            self.assertTrue(h['breakfast']);self.assertEqual(h['bestTotal'],600);self.assertEqual(h['amen'],['basen'])
        finally: hotels.search_xotelo,hotels.search_google=ox,og
class Compare(unittest.TestCase):
    def opt(self,fr,n,total,hotel,id_):
        return {'id':id_,'dest':{'id':'bcn'},'from':fr,'nights':n,'drive':{'km':300,'min':200},'tickets':total-200,'access':{'total':200},'bags':0,'total':total,'dep':'2027-05-11','ret':'2027-05-18','verified':True,'hotelEst':{'total':hotel},'totalWithHotel':total+hotel}
    def run_(self,o,best={},codes=[]):
        geo.BYID['bcn']={'id':'bcn','air':['BCN'],'cc':'ES'};geo.AIRPORTS.setdefault('KRK',{'city':'Krakow'});geo.AIRPORTS.setdefault('WMI',{'city':'Modlin'})
        search.compare_airports(o,best,{},'car',{},2,codes,51,22)
    def test_two_options_same_airport_keeps_cheaper(self):
        a=self.opt('KRK',7,1668,4985,'a');b=self.opt('KRK',7,6000,5772,'b');self.run_([a,b])
        c=a['compare'];self.assertEqual(len(c),1);self.assertEqual(c[0]['total'],1668)
    def test_other_stay_length_ignored(self):
        a=self.opt('KRK',7,1668,4985,'a');b=self.opt('WMI',5,900,9000,'b');self.run_([a,b])
        self.assertEqual([r['from'] for r in a['compare']],['KRK'])
    def test_no_negative_and_hotel_excluded(self):
        a=self.opt('KRK',7,1668,1000,'a');b=self.opt('WMI',7,1200,4000,'b');self.run_([a,b])
        self.assertEqual(a['compare'][0]['from'],'WMI');self.assertNotIn('-',a['insight']);self.assertIn('468 zł',a['insight'])
class CompareReal(unittest.TestCase):
    def test_unchecked_airport_is_not_guessed(self):
        o={'id':'a','dest':{'id':'bcn'},'from':'KRK','nights':7,'drive':{'km':300,'min':200},'tickets':800,'access':{'total':200},'bags':0,'total':1000,'dep':'2027-05-11','ret':'2027-05-18','verified':True,'hotelEst':{'total':2000},'totalWithHotel':3000}
        geo.BYID['bcn']={'id':'bcn','air':['BCN'],'cc':'ES'};geo.AIRPORTS.setdefault('KTW',{'city':'Katowice'})
        search.compare_airports([o],{('KTW','BCN'):{'price':10}},{'KTW':{'km':100,'min':60}},'public',{},2,['KTW'],51,22,{},False,set())
        self.assertEqual([r['from'] for r in o['compare']],['KRK']);self.assertNotIn('insight',o)
    def test_checked_without_flights_says_none(self):
        o={'id':'a','dest':{'id':'bcn'},'from':'KRK','nights':7,'drive':{'km':300,'min':200},'tickets':800,'access':{'total':200},'bags':0,'total':1000,'dep':'2027-05-11','ret':'2027-05-18','verified':True,'hotelEst':{'total':2000},'totalWithHotel':3000}
        search.compare_airports([o],{('KTW','BCN'):{'price':10}},{'KTW':{'km':100,'min':60}},'public',{},2,['KTW'],51,22,{},False,{('KTW','bcn','')})
        self.assertEqual(next(r for r in o['compare'] if r['from']=='KTW')['state'],'none')
class Manual(unittest.TestCase):
    def test_drop_rule(self):
        import push
        self.assertTrue(push.drop(500,450));self.assertFalse(push.drop(500,480));self.assertFalse(push.drop(100,80))
    def test_custom_dest(self):
        import plan
        d=plan.custom_dest({'name':'Kołobrzeg','cc':'pl','lat':54.17,'lon':15.57});self.assertEqual(d['id'],'x-kolobrzeg');self.assertEqual(d['cc'],'PL')
        with self.assertRaises(ValueError): plan.custom_dest({'name':'x'})
class Periods(unittest.TestCase):
    def test_month_is_strict(self):
        y=dt.date.today().year+1;w={'mode':'month','year':y,'month':5,'nights':[7]};a,b,n,m=search.window(w);lim=search.last_return(w,b)
        self.assertTrue(search.allowed({'dep':f'{y}-05-20','ret':f'{y}-05-27'},a,b,lim,set()))
        self.assertFalse(search.allowed({'dep':f'{y}-05-28','ret':f'{y}-06-04'},a,b,lim,set()))
    def test_preset_may_spill_own_may_not(self):
        y=dt.date.today().year+1;w={'mode':'range','from':f'{y}-04-01','to':f'{y}-06-30','nights':[7],'spill':True};a,b,_,_=search.window(w)
        self.assertIsNone(search.last_return(w,b));self.assertEqual(search.last_return({**w,'spill':False},b),b)
    def test_weekday_filter(self):
        y=dt.date.today().year+1;a=dt.date(y,5,1);b=dt.date(y,5,31);x={'dep':a.isoformat(),'ret':(a+dt.timedelta(days=7)).isoformat()}
        self.assertTrue(search.allowed(x,a,b,None,{a.weekday()}));self.assertFalse(search.allowed(x,a,b,None,{(a.weekday()+1)%7}))
    def test_spans_cover_year_in_60_days(self):
        a=dt.date(2027,1,1);b=dt.date(2027,12,31);p=search.spans(a,b)
        self.assertEqual(p[0][0],a);self.assertEqual(p[-1][1],b);self.assertTrue(all((e-s).days<=59 for s,e in p))
        self.assertTrue(all((p[i+1][0]-p[i][1]).days==1 for i in range(len(p)-1)))
    def test_merge_keeps_lowest(self):
        g=search.merge([{'dep':'2027-05-01','ret':'2027-05-08','price':900}],[{'dep':'2027-05-01','ret':'2027-05-08','price':700}]);self.assertEqual(len(g),1);self.assertEqual(g[0]['price'],700)
    def test_ryanair_grid_pairs_days(self):
        import ryanair
        t={'2027-05-03':{'price':200.4}};z={'2027-05-10':{'price':300.2}}
        g=ryanair.grid(t,z,dt.date(2027,5,1),dt.date(2027,5,31),7);self.assertEqual(g,[{'dep':'2027-05-03','ret':'2027-05-10','price':501,'src':'FR'}])
    def test_ryanair_duration_ignores_timezone(self):
        import ryanair
        geo.AIRPORTS.setdefault('KRK',{'lat':50.08,'lon':19.78,'city':'Krakow'});geo.AIRPORTS.setdefault('DUB',{'lat':53.42,'lon':-6.27,'city':'Dublin'})
        f=ryanair._flight('KRK','DUB',{'price':100,'dep':'2027-05-03T10:00','arr':'2027-05-03T11:45'})
        self.assertEqual(f['min'],165);self.assertTrue(flights.valid_flight(f,['KRK'],['DUB'],'2027-05-03'))
class Shared(unittest.TestCase):
    PLAN={'option':{'dep':'2027-05-10','ret':'2027-05-17','leaveHome':'2027-05-10T04:00'},'dest':{'name':'Rzym (Włochy)'},'checklist':[{'t':'Paszport','d':-30},{'t':'Parking','d':-7}],'days':[{'date':'2027-05-11','stops':[{'name':'Koloseum'},{'meal':'lunch'}]}],'return':[{'at':'2027-05-17T09:00'}]}
    def test_merge_keeps_newer_both_ways(self):
        import trips
        a={'exp':{'x':{'u':5,'v':1},'y':{'u':9,'v':2}}};b={'exp':{'x':{'u':7,'v':3},'y':{'u':2,'v':4},'z':{'u':1,'v':5}}}
        m=trips.merge(a,b)['exp'];self.assertEqual((m['x']['v'],m['y']['v'],m['z']['v']),(3,2,5))
    def test_deleted_item_does_not_return(self):
        import trips
        m=trips.merge({'exp':{'x':{'u':9,'x':1}}},{'exp':{'x':{'u':5,'v':1}}})['exp'];self.assertEqual(m['x'].get('x'),1)
    def test_links_and_roles(self):
        import trips
        t=trips.create(self.PLAN,{});self.assertEqual(trips.get(t['edit'])['role'],'edit');self.assertEqual(trips.get(t['view'])['role'],'view');self.assertEqual(trips.get(t['edit'])['view'],t['view'])
        with self.assertRaises(PermissionError): trips.sync(t['view'],{'exp':{'a':{'u':1}}})
        r=trips.sync(t['edit'],{'exp':{'a':{'u':1,'n':1}}});self.assertEqual(r['rev'],2);self.assertIn('a',trips.get(t['view'])['s']['exp'])
        with self.assertRaises(trips.Denied): trips.get('z'*24)
        trips.delete(t['edit'])
        with self.assertRaises(trips.Denied): trips.get(t['edit'])
    def test_no_plain_keys_in_db(self):
        import trips
        t=trips.create(self.PLAN,{});r=trips._c.execute('SELECT hedit,hview FROM trips ORDER BY id DESC').fetchone();self.assertNotIn(t['edit'],r);self.assertNotIn(t['view'],r)
    def test_reminders_skip_done(self):
        import push
        now=dt.datetime(2027,5,1);R=push.reminders(self.PLAN,{'ck':{'0':{'u':1,'v':True}}},now);k=[r['key'] for r in R]
        self.assertNotIn('ck0',k);self.assertIn('ck1',k);self.assertIn('go',k);self.assertIn('day2027-05-11',k)
        self.assertEqual(next(r for r in R if r['key']=='go')['at'],dt.datetime(2027,5,10,2,30))
    def test_reminders_follow_changed_plan(self):
        import push
        R=push.reminders(self.PLAN,{'days':{'2027-05-11':{'u':1,'stops':[{'name':'Panteon'}]}}},dt.datetime(2027,5,1))
        self.assertEqual(next(r for r in R if r['key'].startswith('day'))['body'],'Panteon')
    def test_tick_sends_once(self):
        import push,trips
        t=trips.create(self.PLAN,{});sent=[];push.set_sender(lambda s,p:sent.append(p) or True)
        push.subscribe('urzadzenie-testowe',{'endpoint':'https://x.test/a','keys':{'p256dh':'a','auth':'b'}},[t['edit']])
        n=dt.datetime(2027,5,9,18,5);push.tick(n);push.tick(n);push.set_sender(None)
        self.assertEqual(len([p for p in sent if p['tag']=='d1']),1);trips.delete(t['edit']);push.unsubscribe('urzadzenie-testowe')
    def test_sentence(self):
        import ai
        r=ai.rules('Chcę spędzić pięć dni w Rzymie, jadę z drugą osobą, mam budżet 5000 zł');self.assertEqual((r['destIds'],r['nights'],r['adults'],r['budget']),(['rzym'],4,2,5000))
        self.assertEqual(ai.rules('na plażę do Chorwacji w czerwcu'),{'countries':['HR'],'month':6,'style':'beach'})
class Food(unittest.TestCase):
    D=lambda self:[{'stops':[{'meal':'lunch','lat':41.9,'lon':12.5},{'name':'X','lat':41.9,'lon':12.5}]}]
    def test_source_down_no_invented_names(self):
        o=plan.restaurants;plan.restaurants=lambda *a:None
        try:
            d=self.D();self.assertFalse(plan.attach_food(d,'rzym'));self.assertNotIn('options',d[0]['stops'][0]);self.assertIn('google.com/maps',d[0]['stops'][0]['mapSearch'])
        finally: plan.restaurants=o
    def test_near_only(self):
        o=plan.restaurants;plan.restaurants=lambda *a:[{'n':'Blisko','c':'pizza','lat':41.901,'lon':12.5,'s':1},{'n':'Daleko','c':'x','lat':42.2,'lon':12.5,'s':9}]
        try:
            d=self.D();plan.attach_food(d,'rzym');self.assertEqual([x['name'] for x in d[0]['stops'][0]['options']],['Blisko'])
        finally: plan.restaurants=o
if __name__=='__main__': unittest.main()
