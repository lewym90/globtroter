"""Linki do zakupu i rezerwacji z wypelnionymi danymi."""
from urllib.parse import quote,urlencode
def flight_links(o,d,dep,ret,A,C,carrier=None):
    s=lambda x:x[2:4]+x[5:7]+x[8:10]
    q=quote(f'Flights to {d} from {o} on {dep} through {ret}')
    L=[{'site':'Google Flights','url':f'https://www.google.com/travel/flights?q={q}&curr=PLN&hl=pl'},
       {'site':'Skyscanner','url':f'https://www.skyscanner.pl/transport/loty/{o.lower()}/{d.lower()}/{s(dep)}/{s(ret)}/?adultsv2={A}&cabinclass=economy&childrenv2={"|".join(["8"]*C)}&currency=PLN&locale=pl-PL&market=PL'},
       {'site':'Kayak','url':f'https://www.kayak.pl/flights/{o}-{d}/{dep}/{ret}/{A}adults{"/children-"+"-".join(["8"]*C) if C else ""}?sort=price_a'},
       {'site':'Momondo','url':f'https://www.momondo.pl/flight-search/{o}-{d}/{dep}/{ret}/{A}adults{"/children-"+"-".join(["8"]*C) if C else ""}?sort=price_a'}]
    if carrier=='FR': L.insert(0,{'site':'Ryanair','url':f'https://www.ryanair.com/pl/pl/trip/flights/select?adults={A}&teens=0&children={C}&infants=0&dateOut={dep}&dateIn={ret}&isConnectedFlight=false&isReturn=true&originIata={o}&destinationIata={d}'})
    if carrier=='W6': L.insert(0,{'site':'Wizz Air','url':f'https://www.wizzair.com/pl-pl/booking/select-flight/{o}/{d}/{dep}/{ret}/{A}/{C}/0/null'})
    return L
MONTHS='January February March April May June July August September October November December'.split()
def eng(d):
    # Google rozumie daty tylko w takim zapisie: inaczej traktuje je jak tekst i nic nie znajduje
    y,m,dd=d.split('-');return f'{MONTHS[int(m)-1]} {int(dd)} {y}'
def hotel_links(name,city,ci,co,A,C,rooms=1):
    q=f'{name} {city}'
    return {'Booking.com':'https://www.booking.com/searchresults.pl.html?'+urlencode({'ss':q,'checkin':ci,'checkout':co,'group_adults':A,'group_children':C,'no_rooms':rooms,'selected_currency':'PLN'}),
      'Agoda.com':'https://www.agoda.com/pl-pl/search?'+urlencode({'textToSearch':q,'checkIn':ci,'checkOut':co,'adults':A,'children':C,'rooms':rooms}),
      'Trip.com':'https://pl.trip.com/hotels/list?'+urlencode({'keyword':q,'checkin':ci,'checkout':co,'adult':A,'children':C,'crn':rooms}),
      'Expedia':'https://www.expedia.pl/Hotel-Search?'+urlencode({'destination':q,'startDate':ci,'endDate':co,'adults':A}),
      'Hotels.com':'https://pl.hotels.com/Hotel-Search?'+urlencode({'destination':q,'startDate':ci,'endDate':co,'adults':A}),
      'Google':'https://www.google.com/travel/search?'+urlencode({'q':f'{q} from {eng(ci)} to {eng(co)}','hl':'pl','gl':'pl','curr':'PLN'})}

