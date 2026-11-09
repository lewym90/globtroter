"""Hotel z linku: nazwa i daty z samego linku, bez wchodzenia na strone serwisu."""
import os,sys,tempfile,unittest
os.environ.setdefault('GLOBTROTER_DATA',tempfile.mkdtemp())
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','server'))
import hotels
class Link(unittest.TestCase):
    def test_booking(self):
        r=hotels.parse_link('https://www.booking.com/hotel/es/panoramica-garden.pl.html?aid=1&checkin=2026-12-21&checkout=2026-12-28')
        self.assertEqual((r['name'],r['ci'],r['co']),('panoramica garden','2026-12-21','2026-12-28'))
    def test_booking_split_dates(self):
        r=hotels.parse_link('https://www.booking.com/hotel/pl/willa-x.html?checkin_year=2026&checkin_month=12&checkin_monthday=23&checkout_year=2026&checkout_month=12&checkout_monthday=27')
        self.assertEqual((r['ci'],r['co']),('2026-12-23','2026-12-27'))
    def test_agoda(self):
        r=hotels.parse_link('https://www.agoda.com/pl-pl/hotel-a/hotel/tenerife-es.html?checkIn=2026-12-21&los=7')
        self.assertEqual(r['co'],'2026-12-28')
    def test_text_around(self):
        r=hotels.parse_link('Zobacz to: https://pl.hotels.com/ho1/hotel-b-c/?chkin=2026-12-21&chkout=2026-12-28 :)')
        self.assertEqual(r['name'],'hotel b c')
    def test_bad(self):
        with self.assertRaises(ValueError): hotels.parse_link('nie link')
        r=hotels.parse_link('https://www.booking.com/hotel/es/x.html?checkin=2026-13-40')
        self.assertIsNone(r['ci'])
if __name__=='__main__': unittest.main()
