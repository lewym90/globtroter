import { scene, themeOf, landmarkOf } from './scene.js';
import { flapRow } from './flap.js';

const API = ['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://127.0.0.1:8796' : 'https://188-68-247-201.sslip.io/globtroter';
const VERSION = '1.0.0';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const app = $('#app');
const backdrop = $('#backdrop');
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const url = (u) => (/^https?:\/\//.test(u || '') ? esc(u) : '#');
const zl = (n) => Math.round(n).toLocaleString('pl-PL').replace(/,/g, ' ') + ' zł';
const MONTHS = ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec', 'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'];
const MONTHS_G = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'];
const DAYS = ['pon', 'wt', 'śr', 'czw', 'pt', 'sob', 'nd'];
const WEEK = ['niedziela', 'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota'];
const dateL = (iso) => { const d = new Date(iso.slice(0, 10) + 'T12:00'); return `${d.getDate()} ${MONTHS_G[d.getMonth()]}`; };
const timeL = (iso) => iso.slice(11, 16);
const dur = (m) => (m >= 60 ? `${Math.floor(m / 60)} h ${m % 60 ? m % 60 + ' min' : ''}` : `${m} min`).trim();
const ICON = {
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>',
  plane: '<svg viewBox="0 0 24 24"><path d="M21 12c0-.9-.8-1.5-1.5-1.5H15L10 3H8l2.5 7.5H6L4.5 8.5H3L4 12l-1 3.500h1.500L6 13.500h4.500L8 21h2l5-7.500h4.500c.7 0 1.500-.6 1.500-1.500z"/></svg>',
};

const load = (k, d) => { try { return JSON.parse(localStorage.getItem('gt.' + k)) ?? d; } catch { return d; } };
const save = (k, v) => { try { localStorage.setItem('gt.' + k, JSON.stringify(v)); return true; } catch { return false; } };

const now = new Date();
const defaults = () => ({
  origin: null, radius: 450, originsManual: null,
  dest: { mode: 'style', style: 'beach', ids: [], countries: [] },
  when: { mode: 'month', year: now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear(), month: (now.getMonth() + 1) % 12 + 1, nights: [7], from: '', to: '' },
  pax: { adults: 2, children: 0 }, bags: { cabin: 1, checked: 0 },
  transport: { mode: 'car', consumption: 7.5, fuelPrice: 5.99 },
  stay: { budget: 3000, pref: 'balanced', minRating: 4, breakfast: false, kind: 'all' },
});
const S = {
  q: { ...defaults(), ...load('prefs', {}) }, step: 0, airports: [], dests: [], result: null, option: null, plan: null, tab: 'droga', day: 0,
};

let backKey = '';
function setBackdrop(opts) {
  const k = JSON.stringify(opts);
  if (k === backKey) return;
  backKey = k;
  const old = $('.scene', backdrop);
  backdrop.insertAdjacentHTML('beforeend', scene({ ...opts, animated: true }));
  const nw = backdrop.lastElementChild;
  nw.style.opacity = 0;
  requestAnimationFrame(() => { nw.style.opacity = 1; });
  if (old) setTimeout(() => old.remove(), 950);
}
function toast(t) {
  const e = $('#toast'); e.textContent = t; e.classList.add('on');
  clearTimeout(toast.t); toast.t = setTimeout(() => e.classList.remove('on'), 3800);
}
async function api(path, body) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 90000);
  let res;
  try {
    res = await fetch(API + path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: ctl.signal } : { signal: ctl.signal });
  } catch {
    throw new Error('Brak połączenia z serwerem Globtrotera. Sprawdź internet i spróbuj ponownie.');
  } finally { clearTimeout(timer); }
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(j.error || 'Serwer nie odpowiedział poprawnie.');
  return j;
}
const data = async () => {
  if (S.airports.length) return;
  const [a, d] = await Promise.all([fetch('data/airports.json').then((r) => r.json()), fetch('data/destinations.json').then((r) => r.json())]);
  S.airports = a; S.dests = d;
};
function km(a, b, c, d) {
  const p = Math.PI / 180;
  const x = Math.sin(((c - a) * p) / 2) ** 2 + Math.cos(a * p) * Math.cos(c * p) * Math.sin(((d - b) * p) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(x));
}

const sceneOf = (d) => { const landmark = landmarkOf(d.id); return { seed: d.id, theme: landmark ? 'city' : themeOf(d.tags), landmark, time: landmark === 'rzym' || landmark === 'barcelona' ? 'dusk' : undefined }; };

/* ---------- Start ---------- */
function viewHome() {
  setBackdrop({ seed: 'start', theme: 'beach', time: 'dusk', plane: true });
  const trips = load('trips', []);
  app.innerHTML = `<section class="hero">
    <div>
      <h1 class="brand"><span><i>Glob</i></span><span><i>troter</i></span></h1>
    </div>
    <div class="hero-act">
      <p>Najtańszy termin, lotnisko, nocleg i plan każdej godziny. Od Twoich drzwi i z powrotem.</p>
      ${trips.length ? `<div class="trips-mini">${trips.slice(0, 3).map((t, i) => `<button class="btn ghost small" data-trip="${i}">${esc(t.dest.name)}, ${dateL(t.option.dep)}</button>`).join('')}</div>` : ''}
      ${load('last', null) && Date.now() - load('last').t < 6 * 36e5 ? '<button class="btn ghost" id="lastr">Wróć do ostatnich wyników</button>' : ''}
      <button class="btn" id="go">Zaplanuj wyjazd</button>
    </div></section>`;
  $('#go').onclick = () => { S.step = 0; viewWizard(); };
  const lr = $('#lastr'); if (lr) lr.onclick = () => { const l = load('last'); S.result = l.result; S.q = l.q; viewResults(); };
  $$('[data-trip]').forEach((b) => { b.onclick = () => { S.plan = load('trips', [])[+b.dataset.trip]; S.tab = 'droga'; viewPlan(); }; });
}

/* ---------- Kreator ---------- */
const STEPS = [stepFrom, stepWhere, stepWhen, stepWho, stepAccess, stepStay, stepPlan];
const STYLES = [['beach', 'Plaża'], ['city', 'Zwiedzanie'], ['ski', 'Narty'], ['nature', 'Przyroda'], ['party', 'Imprezy'], ['family', 'Z rodziną'], ['food', 'Jedzenie'], ['romance', 'We dwoje']];
function wizTop() {
  const p = (S.step + 1) / STEPS.length;
  return `<div class="wiz-top"><button class="round" id="back" aria-label="Wstecz">${ICON.back}</button>
    <div class="route" aria-label="Krok ${S.step + 1} z ${STEPS.length}"><svg viewBox="0 0 300 30" preserveAspectRatio="none"><path d="M2 26Q150 -14 298 26" fill="none" stroke="#ffffff66" stroke-width="2" stroke-dasharray="3 6"/><path d="M2 26Q150 -14 298 26" fill="none" stroke="#ffb627" stroke-width="3" pathLength="1" stroke-dasharray="${p} 1"/></svg></div></div>`;
}
function backdropForStep() {
  const t = S.q.dest;
  const theme = t.style === 'ski' ? 'ski' : t.style === 'beach' ? 'beach' : t.style === 'nature' ? 'nature' : t.style === 'party' ? 'night' : t.style ? 'city' : 'sky';
  setBackdrop({ seed: 'wiz' + (t.style || ''), theme, plane: S.step === 0 });
}
function viewWizard() {
  backdropForStep();
  app.innerHTML = `<section class="wiz">${wizTop()}<div class="sheet" id="sheet"></div></section>`;
  $('#back').onclick = () => { if (S.step > 0) { S.step--; viewWizard(); } else viewHome(); };
  STEPS[S.step]($('#sheet'));
  scrollTo(0, 0);
}
const navBtns = (label = 'Dalej', ok = true) => `<div class="nav"><button class="btn" id="next" ${ok ? '' : 'disabled'}>${label}</button></div>`;
const next = () => { save('prefs', { ...S.q, origin: S.q.origin }); S.step++; viewWizard(); };

function stepFrom(el) {
  const q = S.q;
  const draw = () => {
    const near = q.origin ? S.airports.map((a) => ({ ...a, d: km(q.origin.lat, q.origin.lon, a.lat, a.lon) }))
      .filter((a) => (a.cc === 'PL' && a.d < Math.max(q.radius, 700)) || (a.d < q.radius && a.large)).sort((a, b) => a.d - b.d).slice(0, 16) : [];
    el.innerHTML = `<h1>Skąd startujesz?</h1><p class="sub">Porównamy wszystkie lotniska w zasięgu, razem z dojazdem i parkingiem.</p>
    <div class="field"><button class="btn line" id="gps">Użyj mojej lokalizacji</button></div>
    <div class="field"><label for="city">albo wpisz miasto</label><input id="city" type="search" autocomplete="off" placeholder="np. Lublin" value="${esc(q.origin?.label || '')}"><div class="list" id="hits"></div></div>
    ${q.origin ? `<div class="field"><span class="lab">Zasięg lotnisk</span><div class="seg" id="rad">${[[300, '300 km'], [450, '450 km'], [700, '700 km']].map(([v, l]) => `<button data-v="${v}" aria-pressed="${q.radius === v}">${l}</button>`).join('')}</div>
    <p class="hint">Znalezione lotniska: ${near.map((a) => a.iata).join(', ')}</p></div>` : ''}
    ${navBtns('Dalej', !!q.origin)}`;
    $('#gps').onclick = gps;
    let t;
    $('#city').oninput = (e) => { clearTimeout(t); t = setTimeout(() => geocode(e.target.value), 320); };
    $$('#rad button').forEach((b) => { b.onclick = () => { q.radius = +b.dataset.v; draw(); }; });
    $('#next').onclick = next;
  };
  async function gps() {
    if (!navigator.geolocation) return toast('Ten telefon nie udostępnia lokalizacji. Wpisz miasto.');
    $('#gps').textContent = 'Szukam Cię na mapie…';
    navigator.geolocation.getCurrentPosition(async (p) => {
      const { latitude: lat, longitude: lon } = p.coords;
      let label = 'Moja lokalizacja';
      try {
        const r = await fetch(`https://photon.komoot.io/reverse?lat=${lat}&lon=${lon}&lang=default`).then((x) => x.json());
        const pr = r.features?.[0]?.properties;
        if (pr) label = pr.city || pr.town || pr.village || pr.county || label;
      } catch { /* nazwa jest tylko ozdobą, współrzędne mamy */ }
      q.origin = { lat, lon, label }; draw();
    }, (e) => {
      toast(e.code === 1 ? 'Brak zgody na lokalizację. Włącz ją dla Safari albo wpisz miasto.' : 'Nie udało się ustalić lokalizacji. Wpisz miasto.');
      $('#gps').textContent = 'Użyj mojej lokalizacji';
    }, { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 });
  }
  async function geocode(v) {
    const box = $('#hits');
    if (v.trim().length < 2) { box.innerHTML = ''; return; }
    try {
      const r = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(v)}&limit=6&lang=default&lat=52&lon=19`).then((x) => x.json());
      box.innerHTML = (r.features || []).filter((f) => f.properties.countrycode).map((f, i) => {
        const p = f.properties;
        return `<button class="row" data-i="${i}"><span>${esc(p.name)}<small>${esc([p.county, p.state, p.country].filter(Boolean).join(', '))}</small></span></button>`;
      }).join('') || '<p class="hint">Nic nie znaleziono.</p>';
      $$('.row', box).forEach((b) => {
        b.onclick = () => { const f = r.features.filter((x) => x.properties.countrycode)[+b.dataset.i]; q.origin = { lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0], label: f.properties.name }; draw(); };
      });
    } catch { box.innerHTML = '<p class="hint">Wyszukiwarka miejsc nie odpowiada. Użyj lokalizacji.</p>'; }
  }
  draw();
}

function stepWhere(el) {
  const t = S.q.dest;
  const countries = [...new Map(S.dests.map((d) => [d.cc, d])).keys()];
  const CN = { IT: 'Włochy', ES: 'Hiszpania', PT: 'Portugalia', FR: 'Francja', GB: 'Wielka Brytania', IE: 'Irlandia', IS: 'Islandia', NL: 'Holandia', BE: 'Belgia', DE: 'Niemcy', CH: 'Szwajcaria', AT: 'Austria', CZ: 'Czechy', HU: 'Węgry', SK: 'Słowacja', SI: 'Słowenia', HR: 'Chorwacja', ME: 'Czarnogóra', BA: 'Bośnia', RS: 'Serbia', AL: 'Albania', MK: 'Macedonia', GR: 'Grecja', CY: 'Cypr', MT: 'Malta', TR: 'Turcja', BG: 'Bułgaria', RO: 'Rumunia', MD: 'Mołdawia', NO: 'Norwegia', SE: 'Szwecja', DK: 'Dania', FI: 'Finlandia', EE: 'Estonia', LV: 'Łotwa', LT: 'Litwa', PL: 'Polska', GE: 'Gruzja', MA: 'Maroko' };
  const tiles = () => `<div class="tiles">${STYLES.map(([k, l]) => `<button class="tile" data-style="${k}" aria-pressed="${t.style === k}">${scene({ seed: 't' + k, theme: k === 'ski' ? 'ski' : k === 'beach' ? 'beach' : k === 'nature' ? 'nature' : k === 'party' ? 'night' : k === 'family' ? 'beach' : 'city', time: k === 'romance' ? 'dusk' : k === 'family' ? 'noon' : undefined })}<b>${l}</b></button>`).join('')}</div>`;
  const draw = () => {
    let body = '';
    if (t.mode === 'city') body = `<div class="field"><label for="p">Miejsce</label><input id="p" type="search" autocomplete="off" placeholder="np. Barcelona"><div class="list" id="hits"></div><div class="chips" id="sel" style="margin-top:10px">${t.ids.map((i) => `<button class="chip" aria-pressed="true" data-rm="${i}">${esc(S.dests.find((d) => d.id === i)?.name)} ×</button>`).join('')}</div><p class="hint">Możesz dodać kilka miejsc i porównać.</p></div>`;
    if (t.mode === 'country') body = `<div class="field"><span class="lab">Kraj</span><div class="chips">${countries.map((c) => `<button class="chip" data-c="${c}" aria-pressed="${t.countries.includes(c)}">${CN[c] || c}</button>`).join('')}</div></div><div class="field"><span class="lab">Po co jedziesz? (opcjonalnie)</span>${tiles()}</div>`;
    if (t.mode === 'style') body = `<div class="field">${tiles()}</div>`;
    if (t.mode === 'anywhere') body = `<div class="field"><p>Sprawdzimy kilkanaście najlepszych miejsc na ten termin i pokażemy, gdzie polecisz najtaniej.</p></div><div class="field"><span class="lab">Klimat wyjazdu (opcjonalnie)</span>${tiles()}</div>`;
    el.innerHTML = `<h1>Dokąd?</h1><p class="sub">Znasz cel albo tylko wiesz, na co masz ochotę.</p>
      <div class="field seg" id="md">${[['city', 'Miejsce'], ['country', 'Kraj'], ['style', 'Styl'], ['anywhere', 'Gdziekolwiek']].map(([k, l]) => `<button data-m="${k}" aria-pressed="${t.mode === k}">${l}</button>`).join('')}</div>${body}
      ${navBtns('Dalej', valid())}`;
    $$('#md button').forEach((b) => { b.onclick = () => { t.mode = b.dataset.m; if (t.mode === 'city') t.style = t.style || null; draw(); }; });
    $$('[data-style]').forEach((b) => { b.onclick = () => { t.style = t.style === b.dataset.style && t.mode !== 'style' ? null : b.dataset.style; backdropForStep(); draw(); }; });
    $$('[data-c]').forEach((b) => { b.onclick = () => { const c = b.dataset.c; t.countries = t.countries.includes(c) ? t.countries.filter((x) => x !== c) : [...t.countries, c].slice(-3); draw(); }; });
    $$('[data-rm]').forEach((b) => { b.onclick = () => { t.ids = t.ids.filter((i) => i !== b.dataset.rm); draw(); }; });
    const p = $('#p');
    if (p) p.oninput = () => {
      const v = p.value.trim().toLowerCase();
      const hits = v.length < 2 ? [] : S.dests.filter((d) => d.name.toLowerCase().includes(v) || d.en.toLowerCase().includes(v)).slice(0, 6);
      $('#hits').innerHTML = hits.map((d) => `<button class="row" data-add="${d.id}"><span>${esc(d.name)}<small>${esc(d.air.join(', '))}</small></span></button>`).join('') || (v.length > 1 ? '<p class="hint">Tego miejsca nie ma jeszcze w bazie. Wybierz najbliższe większe miasto.</p>' : '');
      $$('[data-add]').forEach((b) => { b.onclick = () => { if (!t.ids.includes(b.dataset.add)) t.ids = [...t.ids, b.dataset.add].slice(-6); draw(); }; });
    };
    $('#next').onclick = next;
  };
  const valid = () => (t.mode === 'city' ? t.ids.length > 0 : t.mode === 'country' ? t.countries.length > 0 : t.mode === 'style' ? !!t.style : true);
  draw();
}

function stepWhen(el) {
  const w = S.q.when;
  const list = [];
  for (let i = 0; i < 12; i++) { const d = new Date(now.getFullYear(), now.getMonth() + i, 1); list.push([d.getFullYear(), d.getMonth() + 1]); }
  const draw = () => {
    const today = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
    el.innerHTML = `<h1>Kiedy?</h1><p class="sub">Im szerszy termin, tym większa szansa na okazję.</p>
    <div class="field seg" id="md">${[['month', 'Miesiąc'], ['range', 'Zakres'], ['dates', 'Dokładnie']].map(([k, l]) => `<button data-m="${k}" aria-pressed="${w.mode === k}">${l}</button>`).join('')}</div>
    ${w.mode === 'month' ? `<div class="field chips">${list.map(([y, m]) => `<button class="chip" data-y="${y}" data-m2="${m}" aria-pressed="${w.year === y && w.month === m}">${MONTHS[m - 1]}${y !== now.getFullYear() ? ' ' + y : ''}</button>`).join('')}</div>` : ''}
    ${w.mode !== 'month' ? `<div class="field grid2"><div><label class="lab" for="f">${w.mode === 'dates' ? 'Wylot' : 'Najwcześniej'}</label><input id="f" type="date" min="${today}" value="${esc(w.from)}"></div><div><label class="lab" for="t">${w.mode === 'dates' ? 'Powrót' : 'Najpóźniej'}</label><input id="t" type="date" min="${today}" value="${esc(w.to)}"></div></div>` : ''}
    ${w.mode !== 'dates' ? `<div class="field"><span class="lab">Ile nocy? Możesz wybrać do trzech</span><div class="chips">${[2, 3, 4, 5, 7, 10, 14].map((n) => `<button class="chip" data-n="${n}" aria-pressed="${w.nights.includes(n)}">${n}</button>`).join('')}</div></div>` : ''}
    ${navBtns('Dalej', ok())}`;
    $$('#md button').forEach((b) => { b.onclick = () => { w.mode = b.dataset.m; draw(); }; });
    $$('[data-m2]').forEach((b) => { b.onclick = () => { w.year = +b.dataset.y; w.month = +b.dataset.m2; draw(); }; });
    $$('[data-n]').forEach((b) => { b.onclick = () => { const n = +b.dataset.n; w.nights = w.nights.includes(n) ? (w.nights.length > 1 ? w.nights.filter((x) => x !== n) : w.nights) : [...w.nights, n].slice(-3).sort((a, c) => a - c); draw(); }; });
    ['f', 't'].forEach((i) => { const x = $('#' + i); if (x) x.onchange = () => { w[i === 'f' ? 'from' : 'to'] = x.value; draw(); }; });
    $('#next').onclick = next;
  };
  const ok = () => w.mode === 'month' || (w.from && w.to && w.to > w.from);
  if (!list.some(([y, m]) => y === w.year && m === w.month)) { [w.year, w.month] = list[1]; }
  draw();
}

function stepWho(el) {
  const p = S.q.pax; const b = S.q.bags;
  const draw = () => {
    const stp = (k, l, min, max, o) => `<div class="stepper"><span>${l}</span><div><button data-k="${k}" data-d="-1" aria-label="Mniej" ${o[k] <= min ? 'disabled' : ''}>−</button><output>${o[k]}</output><button data-k="${k}" data-d="1" aria-label="Więcej" ${o[k] >= max ? 'disabled' : ''}>+</button></div></div>`;
    el.innerHTML = `<h1>Kto leci?</h1><p class="sub">Ceny liczymy dla całej grupy.</p>
    <div class="field">${stp('adults', 'Dorośli', 1, 8, p)}${stp('children', 'Dzieci (2–11 lat)', 0, 6, p)}</div>
    <div class="field"><span class="lab">Bagaż na osobę</span>
    <label class="switch">Walizka do kabiny 10 kg<input type="checkbox" id="cab" ${b.cabin ? 'checked' : ''}></label>
    <label class="switch">Bagaż rejestrowany 20 kg<input type="checkbox" id="chk" ${b.checked ? 'checked' : ''}></label>
    <p class="hint">W tanich liniach doliczamy szacunkową dopłatę. Dokładną kwotę zobaczysz przy zakupie.</p></div>
    <div class="field"><span class="lab">Loty</span>
    <label class="switch">Tylko bez przesiadek<input type="checkbox" id="dir" ${S.q.direct ? 'checked' : ''}></label>
    <label class="switch">Unikaj wylotów przed 7:00<input type="checkbox" id="ear" ${S.q.earliest ? 'checked' : ''}></label></div>${navBtns()}`;
    $('#dir').onchange = (e) => { S.q.direct = e.target.checked; };
    $('#ear').onchange = (e) => { S.q.earliest = e.target.checked ? 7 : 0; };
    $$('[data-k]').forEach((x) => { x.onclick = () => { p[x.dataset.k] += +x.dataset.d; draw(); }; });
    $('#cab').onchange = (e) => { b.cabin = +e.target.checked; };
    $('#chk').onchange = (e) => { b.checked = +e.target.checked; };
    $('#next').onclick = next;
  };
  draw();
}

function stepAccess(el) {
  const t = S.q.transport;
  const draw = () => {
    el.innerHTML = `<h1>Jak na lotnisko?</h1><p class="sub">Dojazd liczymy do ceny, bo tańszy lot daleko od domu bywa droższy w sumie.</p>
    <div class="field seg" id="md">${[['car', 'Autem'], ['dropoff', 'Podwiezie mnie'], ['public', 'Komunikacją']].map(([k, l]) => `<button data-m="${k}" aria-pressed="${t.mode === k}">${l}</button>`).join('')}</div>
    ${t.mode !== 'public' ? `<div class="field grid2"><div><label class="lab" for="l">Spalanie l/100 km</label><input id="l" type="number" inputmode="decimal" step="0.1" min="2" max="30" value="${t.consumption}"></div><div><label class="lab" for="fp">Paliwo zł/l</label><input id="fp" type="number" inputmode="decimal" step="0.01" min="1" max="15" value="${t.fuelPrice}"></div></div>` : ''}
    ${t.mode === 'car' ? `<div class="field"><label class="lab" for="pk">Własna cena parkingu za 7 dni (opcjonalnie)</label><input id="pk" type="number" inputmode="numeric" min="0" max="2000" placeholder="Domyślnie cennik szacunkowy" value="${t.parkingOverride ?? ''}"></div>` : ''}
    ${t.mode === 'public' ? '<p class="hint" style="margin-top:14px">Cenę biletów szacujemy z odległości. Godziny pokażemy w planie.</p>' : ''}${navBtns()}`;
    $$('#md button').forEach((b) => { b.onclick = () => { t.mode = b.dataset.m; draw(); }; });
    const num = (id, key, min, max) => { const x = $('#' + id); if (x) x.onchange = () => { const v = parseFloat(x.value.replace(',', '.')); if (Number.isFinite(v) && v >= min && v <= max) t[key] = v; else if (key === 'parkingOverride' && x.value === '') delete t[key]; else { toast('Wpisz wartość od ' + min + ' do ' + max); x.value = t[key] ?? ''; } }; };
    num('l', 'consumption', 2, 30); num('fp', 'fuelPrice', 1, 15); num('pk', 'parkingOverride', 0, 2000);
    $('#next').onclick = next;
  };
  draw();
}

function stepStay(el) {
  const s = S.q.stay;
  const draw = () => {
    el.innerHTML = `<h1>Jaki nocleg?</h1><p class="sub">Według tego ułożymy ranking hoteli.</p>
    <div class="field"><label class="lab" for="b">Budżet na cały pobyt</label><input id="b" type="number" inputmode="numeric" min="0" step="100" value="${s.budget}"></div>
    <div class="field"><span class="lab">Co jest najważniejsze</span><div class="chips">${[['balanced', 'Najlepszy stosunek'], ['luxury', 'Wysoki standard'], ['cheap', 'Najniższa cena'], ['center', 'Blisko centrum']].map(([k, l]) => `<button class="chip" data-p="${k}" aria-pressed="${s.pref === k}">${l}</button>`).join('')}</div></div>
    <div class="field"><span class="lab">Minimalna ocena gości</span><div class="seg" id="mr">${[[0, 'Dowolna'], [4, '4,0+'], [4.5, '4,5+']].map(([v, l]) => `<button data-r="${v}" aria-pressed="${s.minRating === v}">${l}</button>`).join('')}</div></div>
    <label class="switch field">Śniadanie w cenie<input type="checkbox" id="bf" ${s.breakfast ? 'checked' : ''}></label>
    ${navBtns()}`;
    $$('[data-p]').forEach((b) => { b.onclick = () => { s.pref = b.dataset.p; draw(); }; });
    $$('[data-r]').forEach((b) => { b.onclick = () => { s.minRating = +b.dataset.r; draw(); }; });
    $('#b').onchange = (e) => { s.budget = Math.max(0, +e.target.value || 0); };
    $('#bf').onchange = (e) => { s.breakfast = e.target.checked; };
    $('#next').onclick = next;
  };
  draw();
}

function stepPlan(el) {
  const p = (S.q.plan ||= { pace: 'normal', interests: [] });
  const INT = [['museum', 'Muzea'], ['church', 'Świątynie'], ['castle', 'Zamki'], ['palace', 'Pałace'], ['ruins', 'Starożytność'], ['park', 'Parki'], ['beach', 'Plaże'], ['nature', 'Przyroda'], ['sight', 'Zabytki']];
  const draw = () => {
    el.innerHTML = `<h1>Jak zwiedzasz?</h1><p class="sub">Według tego ułożymy dni na miejscu.</p>
    <div class="field"><span class="lab">Tempo</span><div class="seg" id="pc">${[['slow', 'Spokojnie'], ['normal', 'Normalnie'], ['fast', 'Intensywnie']].map(([k, l]) => `<button data-k="${k}" aria-pressed="${p.pace === k}">${l}</button>`).join('')}</div></div>
    <div class="field"><span class="lab">Co lubisz najbardziej</span><div class="chips">${INT.map(([k, l]) => `<button class="chip" data-i="${k}" aria-pressed="${p.interests.includes(k)}">${l}</button>`).join('')}</div></div>
    ${navBtns('Szukaj najlepszych opcji')}`;
    $$('#pc button').forEach((b) => { b.onclick = () => { p.pace = b.dataset.k; draw(); }; });
    $$('[data-i]').forEach((b) => { b.onclick = () => { const k = b.dataset.i; p.interests = p.interests.includes(k) ? p.interests.filter((x) => x !== k) : [...p.interests, k]; draw(); }; });
    $('#next').onclick = () => { save('prefs', S.q); viewSearch(); };
  };
  draw();
}

/* ---------- Szukanie: tablica odlotów ---------- */
async function viewSearch(resumeId) {
  if (typeof resumeId !== 'string') resumeId = null;
  setBackdrop({ seed: 'night-board', theme: 'night', time: 'night', plane: true });
  const W = window.innerWidth < 380 ? 14 : 16;
  app.innerHTML = `<section class="board-wrap"><h1 class="board-title">Szukamy</h1><div class="board" id="bd"></div>
    <div class="bar"><i id="pr"></i></div><p class="board-label" id="lb" role="status">Przygotowuję trasy</p><p class="board-label" style="font-weight:400;font-size:14px">Zwykle 1–5 minut, bo sprawdzamy ceny na żywo. Możesz zamknąć aplikację, wyniki tu poczekają.</p></section>`;
  const rows = [flapRow(W), flapRow(W), flapRow(W), flapRow(W)];
  rows.forEach((r) => $('#bd').append(r.el));
  const names = S.dests.filter((d) => matches(d)).sort(() => Math.random() - 0.5).map((d) => d.name.toUpperCase());
  if (names.length < 5) names.push('NAJTAŃSZE DATY', 'WSZYSTKIE LOTNISKA', 'NOCLEGI', 'DOJAZD');
  const t = () => rows.forEach((r, i) => r.set((names[(i + Math.floor(Date.now() / 3200)) % Math.max(1, names.length)] || 'EUROPA').replace(/\(.*/, '').trim()));
  t(); const ticker = setInterval(t, 3200);
  const stop = () => clearInterval(ticker);
  try {
    const id = resumeId || (await api('/api/search', S.q)).id;
    save('job', { id, q: S.q, t: Date.now() });
    for (;;) {
      await new Promise((r) => setTimeout(r, 1300));
      const j = await api('/api/job?id=' + id);
      const bar = $('#pr'); const lb = $('#lb');
      if (!bar) { stop(); return; }
      bar.style.width = j.progress * 100 + '%'; lb.textContent = j.label;
      if (j.state === 'done') { stop(); S.result = j.result; S.resultAt = Date.now(); save('job', null); save('last', { result: j.result, q: S.q, t: Date.now() }); return viewResults(); }
      if (j.state === 'error') { save('job', null); throw new Error(j.error); }
    }
  } catch (e) {
    stop();
    app.innerHTML = `<section class="board-wrap"><div class="card"><div class="in"><h2 class="big">Nie mamy pewnych wyników</h2><p style="margin-top:8px">${esc(e.message)}</p><div class="acts"><button class="btn" id="r">Spróbuj ponownie</button><button class="btn line" id="b">Zmień wyszukiwanie</button></div></div></div></section>`;
    $('#r').onclick = () => viewSearch(); $('#b').onclick = () => { S.step = 0; viewWizard(); };
  }
}
function matches(d) {
  const t = S.q.dest;
  if (t.mode === 'city') return t.ids.includes(d.id);
  if (t.mode === 'country') return t.countries.includes(d.cc);
  return !t.style || d.tags.includes(t.style);
}

/* ---------- Wyniki ---------- */
function posterOf(o, h = '') {
  const d = o.dest;
  return `<div class="poster">${scene(sceneOf(d))}${h}<h3>${esc(d.name.replace(/\s*\(.*/, ''))}</h3></div>`;
}
function viewResults() {
  const R = S.result;
  const opts = (R.options || []).filter((o) => o.insight !== undefined || o.compare || true);
  const best = new Map();
  opts.forEach((o) => { if (!best.has(o.dest.id)) best.set(o.dest.id, o); });
  const top = [...best.values()];
  if (top[0]) setBackdrop(sceneOf(top[0].dest));
  const ago = R.at ? new Date(R.at * 1000).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' }) : '';
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${top.length ? 'Najlepsze opcje' : 'Brak wyników'}</h2></div>
  <section class="page">
  ${(R.notes || []).map((n) => `<div class="note"><b>${esc(n.text)}</b>${n.alternatives?.length ? `<p class="mute">Ciepło jest wtedy tutaj: ${n.alternatives.map((a) => `${esc(a.name)}${a.fit?.tmax != null ? ` (${Math.round(a.fit.tmax)}°C)` : ''}`).join(', ')}.</p><div class="chips" style="margin-top:8px">${n.alternatives.map((a) => `<button class="chip" data-alt="${a.id}">${esc(a.name)}</button>`).join('')}</div>` : ''}</div>`).join('')}
  ${R.partial ? '<div class="note"><b>Część zapytań nie przeszła.</b><p class="mute">Mogą istnieć tańsze opcje, których nie widzimy. Pokazujemy tylko to, co udało się sprawdzić.</p></div>' : ''}
  ${!top.length ? `<div class="note info"><b>Na ten termin nie ma lotów z Twoich lotnisk.</b><p class="mute">Spróbuj szerszego terminu albo większego zasięgu lotnisk.</p></div>` : ''}
  ${top.map((o, i) => `<article class="card"><button data-o="${o.id}" style="display:block;width:100%;text-align:left">${posterOf(o, `<span class="pr">${zl(o.perPerson)}<small style="font:600 12px var(--body)"> /os.</small></span>`)}
    <div class="in"><p><b>${dateL(o.dep)} – ${dateL(o.ret)}</b>, ${o.nights} nocy, z ${esc(o.fromGen)}</p>
    <p class="mute">${o.climate?.score != null ? esc(o.climate.why) + '. ' : ''}${o.hotelEst ? `Z noclegiem około ${zl(o.totalWithHotel)}.` : 'Bez ceny noclegu, mogą być zamknięte po sezonie.'}</p>
    ${o.insight ? `<p class="warn" style="color:var(--deep)">${esc(o.insight)}</p>` : ''}</div></button></article>`).join('')}
  <p class="foot">Ceny sprawdzone dziś o ${esc(ago)}. Linie zmieniają je często, ostateczną zobaczysz przy zakupie.</p></section>`;
  $('#b').onclick = () => { S.step = STEPS.length - 1; viewWizard(); };
  $$('[data-o]').forEach((b) => { b.onclick = () => { S.option = opts.find((o) => o.id === b.dataset.o); viewOption(); }; });
  $$('[data-alt]').forEach((b) => { b.onclick = () => { S.q.dest = { mode: 'city', ids: [b.dataset.alt], countries: [], style: 'beach' }; viewSearch(); }; });
  scrollTo(0, 0);
}
function heat(v, lo, hi) {
  const t = hi > lo ? (v - lo) / (hi - lo) : 0;
  const c = [[11, 143, 158], [18, 58, 140], [244, 83, 58]];
  const m = t < 0.5 ? [c[0], c[1], t * 2] : [c[1], c[2], (t - 0.5) * 2];
  return `rgb(${m[0].map((x, i) => Math.round(x + (m[1][i] - x) * m[2])).join(',')})`;
}
function calendar(o) {
  const g = o.calendar || [];
  if (g.length < 2) return '';
  const lo = Math.min(...g.map((x) => x.price)); const hi = Math.max(...g.map((x) => x.price));
  const map = Object.fromEntries(g.map((x) => [x.dep, x]));
  const first = new Date(g[0].dep + 'T12:00'); const last = new Date(g[g.length - 1].dep + 'T12:00');
  let cells = '';
  for (let i = 0; i < (first.getDay() + 6) % 7; i++) cells += '<span></span>';
  for (let d = new Date(first); d <= last; d.setDate(d.getDate() + 1)) {
    const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const x = map[k];
    cells += x ? `<button data-dep="${k}" data-ret="${x.ret}" style="background:${heat(x.price, lo, hi)}" aria-pressed="${k === o.dep}" aria-label="${dateL(k)}, ${x.price} zł">${d.getDate()}<small>${x.price}</small></button>` : `<span class="mute">${d.getDate()}</span>`;
  }
  return `<div class="in"><h3 class="big" style="font-size:32px">Kiedy najtaniej</h3><p class="mute">Bilet w obie strony dla 1 osoby według dnia wylotu, ${o.nights} nocy. Dotknij dnia, by sprawdzić.</p><div class="cal">${DAYS.map((d) => `<b>${d}</b>`).join('')}${cells}</div></div>`;
}
function passHtml(f, label) {
  const L = f.legs; const a = L[0]; const z = L[L.length - 1];
  return `<div class="pass"><small>${label}: ${dateL(a.dep)}, ${esc(a.airlineName)} ${esc(a.airline)} ${esc(a.no)}</small>
  <div class="pass-r"><div><div class="iata">${a.from}</div><b>${timeL(a.dep)}</b></div><div class="pass-mid">${ICON.plane}</div><div style="text-align:right"><div class="iata">${z.to}</div><b>${timeL(z.arr)}</b></div></div>
  <small>${dur(f.min)}, ${f.stops ? `${f.stops} przesiadk${f.stops > 1 ? 'i' : 'a'} (${L.slice(0, -1).map((l) => l.to).join(', ')})` : 'bez przesiadek'}</small></div>`;
}
function viewOption() {
  const o = S.option;
  const others = (S.result.options || []).filter((x) => x.dest.id === o.dest.id);
  const cmp = others.find((x) => x.compare)?.compare;
  const insight = others.find((x) => x.insight)?.insight;
  const max = cmp ? Math.max(...cmp.map((c) => c.total || 0)) : 1;
  setBackdrop(sceneOf(o.dest));
  const n = o.pax.adults + o.pax.children;
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${esc(o.dest.name)}</h2></div>
  <section class="page"><article class="card">${posterOf(o)}
   <div class="in"><p class="big">${zl(o.total)}</p><p class="mute">loty i dojazd dla ${n} ${n > 1 ? 'osób' : 'osoby'}, ${zl(o.perPerson)} na osobę${o.hotelEst ? `. Z noclegiem około ${zl(o.totalWithHotel)}` : ''}</p>
    <div style="margin-top:10px">
    <div class="kv"><span>Bilety</span><span>${zl(o.tickets)} <span class="sure ${o.verified ? 'fact' : 'est'}">${o.verified ? 'sprawdzone' : 'z kalendarza'}</span></span></div>
    ${o.access.items.map((i) => `<div class="kv"><span>${esc(i.label)}</span><span>${zl(i.pln)} <span class="sure est">szacunek</span></span></div>`).join('')}
    ${o.bags ? `<div class="kv"><span>Bagaż</span><span>${zl(o.bags)} <span class="sure est">szacunek</span></span></div>` : ''}
    ${o.hotelEst ? `<div class="kv"><span>Nocleg, ${o.nights} nocy</span><span>około ${zl(o.hotelEst.total)} <span class="sure est">szacunek</span></span></div>` : `<div class="kv"><span>Nocleg</span><span class="sure check">brak cen na ten termin</span></div>`}</div>
    ${o.bagNote ? `<p class="hint">${esc(o.bagNote)}</p>` : ''}
    ${(o.warnings || []).map((w) => `<p class="warn">${esc(w)}</p>`).join('')}
    ${o.climate?.month?.tmax != null ? `<p class="hint">Średnio w tym miesiącu: ${Math.round(o.climate.month.tmin)}–${Math.round(o.climate.month.tmax)}°C${o.climate.month.sea != null ? `, morze ${Math.round(o.climate.month.sea)}°C` : ''}${o.climate.month.rain != null ? `, opady ${Math.round(o.climate.month.rain)} mm` : ''}.</p>` : ''}
    ${o.flight ? passHtml(o.flight.out, 'Tam') + passHtml(o.flight.back, 'Z powrotem') : ''}
    ${o.leaveHome ? `<p style="margin-top:12px"><b>Z domu wyjeżdżasz ${dateL(o.leaveHome)} o ${timeL(o.leaveHome)}.</b></p>` : ''}
    <div class="acts">${o.flight ? `<button class="btn" id="hot">Wybierz nocleg</button>` : ''}</div></div>
   ${calendar(o)}
   ${cmp?.length > 1 ? `<div class="in"><h3 class="big" style="font-size:32px">Z którego lotniska</h3><p class="mute">Cały wyjazd: bilety, dojazd, parking i nocleg. Pozycje „około” to cena z rozpoznania rynku.</p>${insight ? `<div class="insight">${esc(insight)}</div>` : ''}
    <div class="bars">${cmp.map((c) => {
      if (c.state === 'none') return `<div class="cmp mute"><div class="t"><span>${esc(c.city)} ${c.from}, ${c.km} km</span><span>brak lotów w sprawdzonych dniach</span></div></div>`;
      const inner = `<div class="t"><span>${esc(c.city)} ${c.from}, ${c.km} km</span><span>${c.state === 'estimate' ? 'około ' : ''}${zl(c.total)}</span></div><div class="tr" style="width:${(c.total / max) * 100}%"><i class="a" style="flex:${c.tickets}"></i><i class="b" style="flex:${c.access}"></i><i class="c" style="flex:${c.hotel || 0}"></i></div>`;
      return c.optionId ? `<button class="cmp" data-c="${c.optionId}">${inner}</button>` : `<div class="cmp">${inner}</div>`;
    }).join('')}</div>
    <div class="legend"><span><i style="background:var(--deep)"></i>bilety</span><span><i style="background:var(--coral)"></i>dojazd</span><span><i style="background:var(--lagoon)"></i>nocleg</span></div></div>` : ''}
   <div class="in"><h3 class="big" style="font-size:32px">Kup bilety</h3><p class="mute">Otwierają się z wypełnionymi datami. Sprawdź cenę przed zapłatą.</p><div class="linkset">${o.links.map((l) => `<a class="btn line small" href="${url(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join('')}</div></div>
  </article></section>`;
  $('#b').onclick = viewResults;
  const h = $('#hot'); if (h) h.onclick = viewHotels;
  $$('[data-c]').forEach((b) => { b.onclick = () => { S.option = S.result.options.find((x) => x.id === b.dataset.c); viewOption(); }; });
  $$('.cal button').forEach((b) => { b.onclick = () => recheck(b.dataset.dep, b.dataset.ret); });
  scrollTo(0, 0);
}
async function recheck(dep, ret) {
  const o = S.option;
  toast('Sprawdzam loty na ' + dateL(dep));
  try {
    const r = await api('/api/option', { option: o, dep, ret, q: S.q });
    const list = S.result.options; const i = list.indexOf(o);
    r.compare = o.compare; r.insight = o.insight;
    list[i] = r; S.option = r; viewOption();
  } catch (e) { toast(e.message); }
}

/* ---------- Hotele ---------- */
async function viewHotels() {
  const o = S.option; const s = S.q.stay;
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi: ${esc(o.dest.name)}</h2></div><section class="page"><div class="card"><div class="in"><p>Porównuję ceny na kilku stronach dla najlepszych hoteli.</p><div class="spin"></div></div></div></section>`;
  $('#b').onclick = viewOption;
  const P = new URLSearchParams({ dest: o.dest.id, in: o.dep, out: o.ret, adults: o.pax.adults, children: o.pax.children, pref: s.pref, minRating: s.minRating, breakfast: s.breakfast ? 1 : 0 });
  if (s.budget) P.set('budget', s.budget);
  try {
    const r = await api('/api/hotels?' + P);
    S.hotels = r;
    const L = r.hotels;
    app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi: ${esc(o.dest.name)}</h2></div><section class="page">
    ${!L.length ? `<div class="note"><b>Nie mamy pewnych cen dla tych kryteriów.</b><p class="mute">Złagodź wymagania albo sprawdź oferty bezpośrednio.</p><div class="linkset">${Object.entries(r.fallback || {}).slice(0, 4).map(([k, v]) => `<a class="btn line small" href="${url(v)}" target="_blank" rel="noopener">${esc(k)}</a>`).join('')}</div></div>` : ''}
    ${L.map((h, i) => `<article class="card hot">${i === 0 && !h.overBudget ? '<span class="badge">Nasz wybór</span>' : ''}${h.image ? `<img src="${url(h.image)}" alt="${esc(h.name)}" loading="lazy" referrerpolicy="no-referrer">` : ''}
    <div class="in"><h3>${esc(h.name)}</h3><p><span class="stars">${String(h.rating ?? '').replace('.', ',')} / 5</span> <span class="mute">${(h.reviews || 0).toLocaleString('pl-PL')} opinii${h.distKm != null ? `, ${String(h.distKm).replace('.', ',')} km od centrum` : ''}</span></p>
    ${h.why.length ? `<p class="mute">${esc(h.why.join(', '))}.</p>` : ''}${h.overBudget ? '<p class="warn">Ponad Twój budżet.</p>' : ''}
    <div class="pricelist">${h.prices.map((p, j) => `<a class="pl ${j === 0 ? 'best' : ''}" href="${url(p.url)}" target="_blank" rel="noopener"><span>${esc(p.site)}</span><span>${zl(p.total)}</span></a>`).join('')}</div>
    <div class="acts"><button class="btn" data-h="${i}">Wybieram ten hotel</button></div></div></article>`).join('')}
    ${L.length ? `<p class="foot">${r.rooms} ${r.rooms > 1 ? 'pokoje' : 'pokój'}, ${r.nights} nocy. ${esc(r.note)} Link otwiera wyszukiwanie tego hotelu z datami. Dane: TripAdvisor przez Xotelo.</p>` : ''}</section>`;
    $('#b').onclick = viewOption;
    $$('[data-h]').forEach((b) => { b.onclick = () => buildPlan(L[+b.dataset.h]); });
    scrollTo(0, 0);
  } catch (e) {
    app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi</h2></div><section class="page"><div class="note"><b>${esc(e.message)}</b><div class="acts"><button class="btn" id="r">Spróbuj ponownie</button></div></div></section>`;
    $('#b').onclick = viewOption; $('#r').onclick = viewHotels;
  }
}

/* ---------- Kompendium ---------- */
async function buildPlan(hotel) {
  app.innerHTML = `<section class="board-wrap"><h1 class="board-title">Układam plan</h1><div class="bar"><i style="width:60%"></i></div><p class="board-label">Liczę godziny, dojazdy i dni na miejscu</p></section>`;
  try {
    S.plan = await api('/api/plan', { option: S.option, hotel, home: S.q.origin, prefs: S.q.plan || {} });
    const t = load('trips', []).filter((x) => x.option.id !== S.plan.option.id);
    t.unshift(S.plan);
    if (!save('trips', t.slice(0, 8))) toast('Telefon nie pozwolił zapisać planu offline.');
    S.tab = 'droga'; viewPlan();
  } catch (e) { toast(e.message); viewHotels(); }
}
const SURE = { fact: 'sprawdzone', est: 'szacunek', check: 'sprawdź' };
const evHtml = (e) => `<div class="ev"><time>${timeL(e.at)}</time> <span class="sure ${e.sure}">${SURE[e.sure]}</span><h4>${esc(e.title)}</h4><p>${esc(e.text)}${e.sample ? ' Rozkład z najbliższego takiego dnia tygodnia, sprawdź bliżej wyjazdu.' : ''}</p>
 ${e.legs?.length ? `<ul class="legs">${e.legs.map((l) => `<li>${l.mode === 'WALK' ? `Pieszo ${l.min} min` : `${esc(l.line || l.mode)}: ${esc(l.from)} → ${esc(l.to)}, ${l.min} min`}</li>`).join('')}</ul>` : ''}
 ${e.map ? `<a href="${url(e.map)}" target="_blank" rel="noopener">Pokaż na mapie</a>` : ''}</div>`;
function viewPlan() {
  const p = S.plan; const o = p.option; const c = p.country;
  setBackdrop(sceneOf(o.dest));
  const tabs = [['droga', 'Droga'], ['dni', 'Dni'], ['koszty', 'Koszty'], ['lista', 'Lista'], ['info', 'Info']];
  const byDay = (list) => { const m = {}; list.forEach((e) => { (m[e.at.slice(0, 10)] ||= []).push(e); }); return Object.entries(m); };
  const bodies = {
    droga: () => `<article class="card"><div class="in"><h3 class="big" style="font-size:34px">Tam</h3>${byDay(p.timeline).map(([d, L]) => `<p class="mute" style="margin-top:8px">${WEEK[new Date(d + 'T12:00').getDay()]}, ${dateL(d)}</p><div class="tl">${L.map(evHtml).join('')}</div>`).join('')}</div></article>
      <article class="card"><div class="in"><h3 class="big" style="font-size:34px">Z powrotem</h3>${byDay(p.return).map(([d, L]) => `<p class="mute" style="margin-top:8px">${WEEK[new Date(d + 'T12:00').getDay()]}, ${dateL(d)}</p><div class="tl">${L.map(evHtml).join('')}</div>`).join('')}</div></article>`,
    dni: () => p.days.map((d, i) => `<article class="card"><div class="in"><div class="dayh"><h3>Dzień ${i + 1}</h3><span class="mute">${WEEK[new Date(d.date + 'T12:00').getDay()]}, ${dateL(d.date)}</span></div>
      ${d.weather ? `<p class="mute">Prognoza: ${Math.round(d.weather.tmin)}–${Math.round(d.weather.tmax)}°C, deszcz ${d.weather.rain ?? '?'}%</p>` : ''}
      ${d.stops.length ? d.stops.map((s) => s.meal ? `<div class="stop"><time>${s.time}</time><div><b>${s.meal === 'lunch' ? 'Obiad' : 'Kolacja'} w okolicy</b>${s.options?.length ? s.options.map((r) => `<p><a href="${url(r.map)}" target="_blank" rel="noopener">${esc(r.name)}</a> <span class="mute">${esc(r.cuisine)}</span></p>`).join('') : ''}<p><a href="${url(s.mapSearch)}" target="_blank" rel="noopener">Restauracje w pobliżu i ich oceny</a></p></div></div>`
        : `<div class="stop"><time>${s.time}</time><div><a href="${url(s.map)}" target="_blank" rel="noopener">${esc(s.name)}</a><p class="mute">${esc(s.type)}, około ${dur(s.min)}${s.walk ? `, ${s.walk} min dojścia` : ''}</p>${s.web ? `<a href="${url(s.web)}" target="_blank" rel="noopener">Godziny i bilety</a>` : '<span class="sure check">sprawdź godziny</span>'}</div></div>`).join('') : `<p class="mute" style="margin-top:8px">${d.kind === 'departure' ? 'Dzień powrotu. Trzymaj się godzin z zakładki Droga.' : d.kind === 'arrival' ? 'Dzień przyjazdu. Rozpakuj się i odpocznij.' : 'Wolny dzień: plaża, spacer albo wycieczka.'}</p>`}</div></article>`).join('') + (p.foodOk ? '' : '<div class="note"><b>Baza restauracji chwilowo nie odpowiada.</b><p class="mute">Linki mapy pokażą lokale w okolicy z ocenami.</p></div>'),
    koszty: () => `<article class="card"><div class="in"><p class="big">${zl(p.total)}</p><p class="mute">cały wyjazd bez wyżywienia na miejscu</p><div style="margin-top:10px">${p.cost.map((i) => `<div class="kv"><span>${esc(i.label)}</span><span>${zl(i.pln)} <span class="sure ${i.sure}">${SURE[i.sure]}</span></span></div>`).join('')}</div></div></article>`,
    lista: () => `<article class="card"><div class="in checks">${p.checklist.map((x, i) => `<label><input type="checkbox" data-ck="${i}" ${(load('ck.' + o.id, {})[i]) ? 'checked' : ''}><span>${esc(x.t)}<br><small class="mute">${dateL(new Date(new Date(o.dep + 'T12:00').getTime() + x.d * 864e5).toISOString())}</small>${x.url ? ` <a href="${url(x.url)}" target="_blank" rel="noopener">Otwórz</a>` : ''}</span></label>`).join('')}</div></article>`,
    info: () => `<article class="card"><div class="in"><h3 class="big" style="font-size:34px">${esc(c?.name || p.dest.name)}</h3>${c ? `<div class="kv"><span>Dokument</span><span style="text-align:right">${esc(c.docs)}</span></div><div class="kv"><span>Waluta</span><span>${esc(c.currencyName)}${c.rate ? `, 1 ${c.currency} = ${c.rate.toFixed(2).replace('.', ',')} zł` : ''}</span></div><div class="kv"><span>Język</span><span>${esc(c.language)}</span></div><div class="kv"><span>Gniazdka</span><span>${esc(c.plugs)}</span></div><div class="kv"><span>Numer alarmowy</span><span><a href="tel:${esc(c.emergency.split(' ')[0])}">${esc(c.emergency)}</a></span></div><p class="hint">${esc(c.plugNote)}</p><div class="acts"><a class="btn line small" href="${url(c.msz)}" target="_blank" rel="noopener">Ostrzeżenia i wymogi MSZ</a></div>` : ''}
      ${p.holidays?.length ? `<p class="warn">Święta w czasie pobytu: ${p.holidays.map((h) => `${esc(h.name)} (${dateL(h.date)})`).join(', ')}. Część miejsc może być zamknięta.</p>` : ''}</div></article>`,
  };
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2></h2></div><section class="page">
    <div class="cover">${scene({ ...sceneOf(o.dest), animated: true })}<h1>${esc(p.dest.name.replace(/\s*\(.*/, ''))}</h1></div>
    <div class="tabs" role="tablist">${tabs.map(([k, l]) => `<button role="tab" data-t="${k}" aria-selected="${S.tab === k}">${l}</button>`).join('')}</div>
    <div id="body" style="display:grid;gap:14px">${bodies[S.tab]()}</div>
    <p class="foot">Plan z ${esc(p.at.replace('T', ', '))}. Zapisany w telefonie, działa bez internetu. <button id="del" style="text-decoration:underline">Usuń wyjazd</button></p></section>`;
  $('#b').onclick = viewHome;
  $$('.tabs button').forEach((b) => { b.onclick = () => { const y = scrollY; S.tab = b.dataset.t; viewPlan(); scrollTo(0, y); }; });
  $$('[data-ck]').forEach((x) => { x.onchange = () => { const m = load('ck.' + o.id, {}); m[x.dataset.ck] = x.checked; save('ck.' + o.id, m); }; });
  $('#del').onclick = () => { save('trips', load('trips', []).filter((x) => x.option.id !== o.id)); viewHome(); };
}

(async function boot() {
  viewHome();
  try { await data(); } catch { toast('Nie udało się wczytać bazy miejsc. Sprawdź internet.'); }
  const job = load('job', null);
  if (job && Date.now() - job.t < 3e6) { S.q = job.q; viewSearch(job.id); }
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
  window.__gt = { S, viewResults, viewOption, viewPlan, VERSION };
})();
