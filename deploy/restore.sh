#!/usr/bin/env bash
# Przywraca baze wyjazdow z kopii. Uruchom jako root: bash restore.sh [plik_kopii]
set -uo pipefail
D=/opt/globtroter/data-run; B="$D/backup"
[ "$(id -u)" = 0 ] || { echo "Uruchom jako root"; exit 1; }
F="${1:-$(ls -1 "$B"/trips-*.db 2>/dev/null | tail -n1)}"
[ -f "$F" ] || { echo "Nie ma kopii: $F"; exit 1; }
python3 -c "import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);r=c.execute('PRAGMA integrity_check').fetchone()[0];sys.exit(0 if r=='ok' else 1)" "$F" || { echo "Kopia uszkodzona, nic nie zmieniam: $F"; exit 1; }
echo "Przywracam $F"
systemctl stop globtroter
S="$D/trips.db"; [ -f "$S" ] && cp "$S" "$S.przed-$(date +%Y%m%d%H%M%S)"
rm -f "$S-wal" "$S-shm"; cp "$F" "$S"; chown --reference="$D" "$S"; chmod 600 "$S"
systemctl start globtroter; sleep 3
systemctl is-active --quiet globtroter && echo "Gotowe" || { echo "Usługa nie wstała"; exit 1; }
