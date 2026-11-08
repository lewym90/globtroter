# Adapter biura podróży (server/tours/<op>.py)

Pure Python 3.10 standard library only (urllib via `tours.http.get`, re, json, html). No Playwright, no third-party packages: the server has 320 MB RAM and no browser.

## Module API
```python
NAME = 'Itaka'            # display name
SITE = 'https://www.itaka.pl'
COUNTRIES = {'ES': '<biuro-specific slug or id>', ...}   # ISO codes this biuro sells; only verified ones
def search(cc: str, ym: str, origin: str | None, limit_pages: int = 40) -> dict
def parse(text: str, ...) -> list[dict]   # pure function used by search; unit-tested offline on fixture
```
- `cc`: ISO country code, e.g. 'ES','GR','TR','EG','BG','HR','IT','PT','CY','AL','TN','MA','MT','ME'.
- `ym`: 'YYYY-MM'. Return offers whose DEPARTURE date falls in that month.
- `origin`: Polish departure airport IATA or None for any. Accept: WAW (= Chopin + Modlin, also Radom if the site groups it), KTW, KRK, GDN, WRO, POZ, RZE, LUZ, BZG, LCJ, SZZ, OSZ (Szczytno-Szymany). If the biuro has no flights from it, return no offers.
- Return `{'offers': [...], 'total': <int or None — how many offers/hotels the biuro itself reports for this query>, 'complete': bool — True if all pages were read, 'url': '<link to the same list on the biuro site for the user>'}`.
- Raise `tours.http.Blocked` if the site blocks; other exceptions on failure. Never return fake or estimated data.

## Offer dict (all strings in Polish where human-readable)
```
{'op': 'itaka', 'name': 'Hotel name', 'stars': 4 or None (float allowed, e.g. 4.5),
 'place': 'Teneryfa, Puerto de la Cruz' (region, town as the biuro gives it),
 'dep': '2027-05-17', 'ret': '2027-05-24', 'nights': 7,
 'board': 'All inclusive' | 'Śniadania' | 'Śniadania i obiadokolacje' | 'Pełne wyżywienie' | 'Bez wyżywienia' | original text if unknown,
 'from': 'KTW' (IATA of departure, or city name if no code) ,
 'ppp': 2199 (int PLN per adult, including obligatory fees the biuro shows in the final price such as TFG/TFP if they are always added; say in a comment what is included),
 'adults': 2, 'total': 4398 (int PLN for those adults, as shown by the biuro),
 'rating': 8.4 or None (customer rating 0-10 if shown),
 'kind': 'wypoczynek' | 'objazd' | 'city break',
 'url': 'https://... exact offer link (that hotel, that date, that departure)'}
```
Do not include images or descriptions (their copyright).

## Rules
- Obey robots.txt for User-agent * (check it). Fetch only allowed paths. No login, no captcha solving, no bypassing blocks, no faking a browser to evade protection: use `tours.http.get`, which sends an honest User-Agent and waits between requests. If a site refuses that User-Agent, report it; do not switch to a fake one.
- Keep the number of requests per search reasonable (a few to a few dozen pages).
- Prefer the cheapest-first sort if the site has one, so a page limit still returns the cheapest offers.
- Save one small real fixture file (trim it to a few offers if large; under 300 KB) in tests/fixtures/tours/<op>.<ext> and add tests/test_tours_<op>.py (unittest, offline) checking parse() returns well-formed offers.
- Live-verify: run search() for 2 real queries (e.g. ES 2027-05 KTW, and another country/origin) and open 5 offer URLs to confirm hotel, date and price match. Report numbers.
