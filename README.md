# Globtroter

Planer wyjazdów po Europie jako PWA. Znajduje najtańszy termin i lotnisko, liczy koszt od drzwi do drzwi, porównuje ceny hoteli na kilku stronach i układa plan każdej godziny.

**Aplikacja:** https://lewym90.github.io/globtroter/
**Instalacja na iPhonie:** Safari, Udostępnij, Do ekranu początkowego.

Aplikacja niekomercyjna, dla właściciela i znajomych. Niczego nie sprzedaje ani nie rezerwuje: prowadzi do stron linii i hoteli z wypełnionymi danymi.

## Jak to działa
- `index.html`, `js/`, `css/`: PWA na GitHub Pages, czysty JavaScript bez budowania.
- `server/`: API w Pythonie na VPS (`127.0.0.1:8796`, trasa `/globtroter/` w Caddy).
- `data/`: lotniska, kierunki, klimat, morze, atrakcje. Budowane przez `tools/`.

Wyszukiwanie ma trzy kroki, żeby jak najmniej pytać Google:
1. Rozpoznanie: kilka dat, wszystkie lotniska naraz (jedno zapytanie daje ceny każdej pary).
2. Kalendarz: najlepsze pary, cena dla każdej daty wylotu.
3. Potwierdzenie: konkretne loty. Termin wybierany po sumie lot plus nocleg.

## Zasady wiarygodności
- Wynik pusty (brak lotów) i błąd źródła (nie wiadomo) to różne rzeczy. Błąd nigdy nie udaje braku lotów.
- Każda wartość ma oznaczenie: sprawdzone, szacunek albo sprawdź.
- Rekordy niespójne (zła data, zerwany łańcuch przesiadek, zerowa cena) są odrzucane.
- Klucze hoteli są sprawdzane geograficznie: hotel musi leżeć przy celu.

## Źródła danych
| Dane | Źródło | Uwaga |
|---|---|---|
| Loty i kalendarz cen | Google Flights przez bibliotekę `fli` | Nieoficjalne, może się zepsuć |
| Hotele | Xotelo (dane TripAdvisora) i Google Hotels, łączone bez duplikatów | Nieoficjalne, cena za pokój |
| Dojazd autem | OSRM | Serwer publiczny |
| Komunikacja | Transitous | Darmowe, społecznościowe |
| Restauracje | OpenStreetMap, budowane przez GitHub Actions (`data/food/`) | Z linkiem do mapy jako zapas |
| Klimat | Meteostat (CC BY-NC), normy wieloletnie | |
| Morze | Open-Meteo Marine (CC BY), 2025 | |
| Atrakcje | Wikidata (CC0), zdjęcia Wikimedia | |
| Lotniska | OurAirports (domena publiczna) | |
| Kursy | NBP | |

Zdjęcia kierunków pochodzą z Wikimedia Commons, startowe (`photos/hero/`) zmieniają się codziennie o 8:00. Mapa lotnicza: Esri przez Leaflet.

Ceny parkingów i dopłaty za bagaż to szacunki z `server/access.py` i `server/search.py`, użytkownik może wpisać własną cenę parkingu.

## Instalacja API na VPS
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lewym90/globtroter/main/deploy/install.sh)
```

## Testy
```bash
python3 -m unittest discover tests      # logika, bez sieci
python3 tests/flow.py Barcelona         # pełny przejazd na widoku iPhone'a
```


## Serwer i dane

Wyjazdy wspólne, wydatki i powiadomienia są w `/opt/globtroter/data-run/trips.db`. Klucze powiadomień w `data-run/vapid.pem`. Klucz Gemini w `/etc/globtroter.env`, czytelny tylko dla roota. Pamięć cen to `cache.db`, można ją usunąć bez szkody.

Serwer robi kopię bazy raz dziennie w `data-run/backup/`, sprawdza ją i trzyma 7 ostatnich. To ten sam dysk, więc przy awarii całego serwera pomaga kopia z telefonu: Profil, Pobierz kopię.

### Przywracanie

    bash <(curl -fsSL https://raw.githubusercontent.com/lewym90/globtroter/main/deploy/restore.sh)

Skrypt zatrzymuje usługę, zachowuje obecną bazę, wstawia najnowszą dobrą kopię i uruchamia usługę. Inną kopię wskażesz argumentem. Nowy serwer: najpierw `deploy/install.sh`, potem przenieś `data-run` i `/etc/globtroter.env`. Bez `vapid.pem` trzeba od nowa włączyć powiadomienia na telefonach.

## Nocne zadania

O 4:00 serwer odświeża kalendarze cen szukane w ostatnich dwóch tygodniach (do 40 zapytań) i sprawdza obserwowane ceny (do 30 tras).

## Źródła, które mogą zniknąć

Ceny Ryanaira, Google Flights, Google Hotels i Xotelo to nieoficjalne dostępy. Gdy któreś padnie, reszta działa, a aplikacja mówi, czego nie sprawdziła. Lista hoteli Xotelo od listopada 2026 nie odpowiada, więc 57 miast bez zapisanej listy korzysta tylko z Google.
