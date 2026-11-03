#!/usr/bin/env bash
# Instalacja API Globtrotera na VPS. Uruchom jako root:
#   bash <(curl -fsSL https://raw.githubusercontent.com/lewym90/globtroter/main/deploy/install.sh)
# Wzorzec jak w Poczcie: osobny uzytkownik, /opt/globtroter, usluga tylko na 127.0.0.1, jedna trasa w conf.d (walidacja + wycofanie).
set -uo pipefail
REPO="${GLOBTROTER_REPO:-lewym90/globtroter}"; BRANCH="${GLOBTROTER_BRANCH:-main}"
APP=/opt/globtroter; USR=globtroter; PORT=8796
CF="${CADDYFILE:-/etc/caddy/Caddyfile}"; CD="${CONFD:-$(dirname "$CF")/conf.d}"; ROUTE="$CD/globtroter.caddy"
say(){ printf '== %s\n' "$*"; }; die(){ printf 'PRZERWANO: %s\n' "$*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || die "uruchom jako root"
command -v systemctl >/dev/null || die "brak systemd"
command -v caddy >/dev/null || die "nie widzę Caddy"
grep -qF "$CD" "$CF" || die "Caddy nie wczytuje $CD"
command -v python3 >/dev/null || die "brak python3"
python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || die "potrzebny Python 3.10 lub nowszy"
AV="$(df -Pm / | awk 'NR==2{print $4}')"; [ "${AV:-0}" -gt 400 ] || die "za mało miejsca: ${AV:-?} MB wolnych, potrzeba 400 MB"
ss -ltn 2>/dev/null | grep -q ":$PORT " && [ ! -f /etc/systemd/system/globtroter.service ] && die "port $PORT jest zajęty"
id "$USR" >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin "$USR" || die "useradd"
mkdir -p "$APP/data-run"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" | tar -xz -C "$TMP" --strip-components=1 || die "pobieranie kodu"
rm -rf "$APP/server" "$APP/data"; cp -r "$TMP/server" "$TMP/data" "$APP/"
python3 -m venv "$APP/venv" 2>/dev/null || { apt-get install -y python3-venv >/dev/null 2>&1 && python3 -m venv "$APP/venv"; } || die "venv"
"$APP/venv/bin/pip" -q install --upgrade pip >/dev/null
"$APP/venv/bin/pip" -q install -r "$APP/server/requirements.txt" || die "instalacja bibliotek"
"$APP/venv/bin/python" -c 'from fli.search import SearchFlights' || die "biblioteka lotów nie działa"
chown -R "$USR":"$USR" "$APP/data-run"
cat > /etc/systemd/system/globtroter.service <<U
[Unit]
Description=Globtroter API
After=network-online.target
Wants=network-online.target
[Service]
User=$USR
Environment=GLOBTROTER_PORT=$PORT
Environment=GLOBTROTER_DATA=$APP/data-run
Environment=TZ=Europe/Warsaw
WorkingDirectory=$APP/server
ExecStart=$APP/venv/bin/python $APP/server/app.py
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$APP/data-run
MemoryMax=260M
[Install]
WantedBy=multi-user.target
U
systemctl daemon-reload; systemctl enable globtroter >/dev/null 2>&1; systemctl restart globtroter; sleep 3
systemctl is-active --quiet globtroter || { journalctl -u globtroter -n 20 --no-pager >&2; die "usługa nie wystartowała (Caddy nietknięty)"; }
curl -fsS -m 5 "http://127.0.0.1:$PORT/api/health" >/dev/null || die "API nie odpowiada"
OLD=""; [ -f "$ROUTE" ] && OLD="$(cat "$ROUTE")"
cat > "$ROUTE" <<R
handle_path /globtroter/* {
	reverse_proxy 127.0.0.1:$PORT
}
R
chmod 755 "$CD"; chmod 644 "$ROUTE"
if ! caddy validate --config "$CF" --adapter caddyfile >/dev/null 2>&1; then
  if [ -n "$OLD" ]; then printf '%s\n' "$OLD" > "$ROUTE"; else rm -f "$ROUTE"; fi
  die "konfiguracja Caddy niepoprawna, wycofano zmianę"
fi
systemctl reload caddy || die "reload Caddy"
say "Gotowe. Sprawdź: $(sed -nE '0,/^[^[:space:]{#(][^{]*\{/s/[[:space:]]*\{.*$//p' "$CF")/globtroter/api/health"
