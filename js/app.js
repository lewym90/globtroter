import { scene, themeOf, landmarkOf } from './scene.js';
import { flapRow } from './flap.js';
import { initLive, swapDay, artOf } from './live.js';

// iOS Safari pomija user-scalable=no, więc blokujemy powiększanie gestem i dwuklikiem w skrypcie. Dwuklik blokuje touch-action w CSS. Mapy mają własne przybliżanie.
['gesturestart', 'gesturechange', 'gestureend'].forEach((t) => document.addEventListener(t, (e) => e.preventDefault(), { passive: false }));
document.addEventListener('touchmove', (e) => { if (e.touches.length > 1 && !e.target.closest('.leaflet-container')) e.preventDefault(); }, { passive: false });
const API = ['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://127.0.0.1:8796' : 'https://188-68-247-201.sslip.io/globtroter';
const VERSION = '3.6.0';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const app = $('#app');
const backdrop = $('#backdrop');
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const url = (u) => (/^https?:\/\//.test(u || '') ? esc(u) : '#');
const osob = (n) => (n === 1 ? 'osoba' : n < 5 ? 'osoby' : 'osób');
const osobD = (n) => (n === 1 ? 'osoby' : 'osób');
const zl = (n) => Math.round(n).toLocaleString('pl-PL').replace(/,/g, ' ') + ' zł';
const MONTHS = ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec', 'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'];
const MONTHS_G = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'];
const PRESETS = { y: { l: 'Cały rok', a: 1, b: 12 }, h1: { l: 'I półrocze', a: 1, b: 6 }, h2: { l: 'II półrocze', a: 7, b: 12 }, q1: { l: 'I kwartał', a: 1, b: 3 }, q2: { l: 'II kwartał', a: 4, b: 6 }, q3: { l: 'III kwartał', a: 7, b: 9 }, q4: { l: 'IV kwartał', a: 10, b: 12 } };
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
  q: { ...defaults(), ...load('prefs', {}) }, zone: load('zone', 'eu'), step: 0, airports: [], dests: [], photos: {}, hero: [], shapes: {}, result: null, option: null, plan: null, tab: 'droga', day: 0,
};

// Kafelki na starcie: Polska, Europa, poza Europą. Turcja i Gruzja leżą na granicy kontynentów, więc są w obu.
const WORLD = ['EG', 'TN', 'MA', 'CV', 'AE', 'JO', 'TR', 'GE'];
const inZone = (cc, z = S.zone) => (z === 'pl' ? cc === 'PL' : z === 'world' ? WORLD.includes(cc) : z === 'eu' ? cc !== 'PL' && (!WORLD.includes(cc) || cc === 'TR' || cc === 'GE') : true);
const zoneOf = (cc) => (cc === 'PL' ? 'pl' : WORLD.includes(cc) && cc !== 'TR' && cc !== 'GE' ? 'world' : 'eu');
const ZD = () => S.dests.filter((d) => inZone(d.cc));
const isPL = () => S.zone === 'pl';
function setZone(z) {
  const q = S.q; q.destZ ||= {};
  if (q.dest) q.destZ[S.zone] = q.dest;
  S.zone = z; save('zone', z);
  q.dest = q.destZ[z] || { mode: z === 'pl' ? 'style' : 'city', ids: [], countries: [], style: null };
  q.dest.zone = z;
  q.dest.ids = (q.dest.ids || []).filter((i) => { const d = S.dests.find((x) => x.id === i); return !d || inZone(d.cc, z); });
  save('prefs', q);
}
function openDest(id) {
  const d = S.dests.find((x) => x.id === id); if (!d) return;
  setZone(zoneOf(d.cc));
  S.q.dest = { mode: 'city', ids: [id], countries: [], style: null, zone: S.zone }; save('prefs', S.q);
  viewFly();
}
const goForm = () => viewFly();

let backKey = '';
function setBackdrop(opts) {
  const k = JSON.stringify(opts);
  if (k === backKey) return;
  backKey = k;
  const olds = [...backdrop.children];
  if (opts.photo) backdrop.insertAdjacentHTML('beforeend', `<div class="bdp art ${opts.strong ? 'strong' : ''}"><img src="${esc(opts.photo)}" alt="">${opts.strip ? `<img class="strip" src="art/band/${BANDS[dayIdx() % 3]}.jpg" alt="">` : ''}</div>`);
  else backdrop.insertAdjacentHTML('beforeend', scene({ ...opts, animated: true }));
  const nw = backdrop.lastElementChild;
  nw.style.opacity = 0;
  requestAnimationFrame(() => { nw.style.opacity = 1; });
  setTimeout(() => olds.forEach((x) => x.remove()), 950);
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
  const [a, d, p, h, sh] = await Promise.all(['airports', 'destinations', 'photos', 'hero', 'shapes'].map((n) => fetch(`data/${n}.json`).then((r) => r.json())));
  S.airports = a; S.dests = d; S.photos = p; S.hero = h; S.shapes = sh;
};
function km(a, b, c, d) {
  const p = Math.PI / 180;
  const x = Math.sin(((c - a) * p) / 2) ** 2 + Math.cos(a * p) * Math.cos(c * p) * Math.sin(((d - b) * p) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(x));
}

const sceneOf = (d) => { const landmark = landmarkOf(d.id); return { seed: d.id, theme: landmark ? 'city' : themeOf(d.tags), landmark, time: landmark === 'rzym' || landmark === 'barcelona' ? 'dusk' : undefined }; };

/* ---------- Zdjęcia: zmiana codziennie o 8:00 ---------- */
const dayIdx = () => Math.floor((Date.now() - new Date().getTimezoneOffset() * 6e4 - 8 * 36e5) / 864e5);
// Wikimedia ogranicza miniatury w niestandardowych rozmiarach (blad 429), wiec zaokraglamy do ich standardowych szerokosci
const THUMB = [120, 250, 330, 500, 960, 1280, 1920];
const commons = (f, w) => `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(safeDec(f))}?width=${THUMB.find((t) => t >= w) || 1920}`;
const safeDec = (f) => { try { return decodeURIComponent(f); } catch { return f; } };
const photoOf = (id, w = 900, shift = 0) => { const L = S.photos[id] || []; return L.length ? { ...L[(dayIdx() + shift) % L.length], src: commons(L[(dayIdx() + shift) % L.length].f, w) } : null; };
const HERO = [['rzym', 'Rzym'], ['santorini', 'Santorini'], ['paryz', 'Paryż'], ['barcelona', 'Barcelona'], ['alpy', 'Alpy'], ['chorwacja', 'Chorwacja']].map(([f, n]) => ({ src: `art/hero/${f}.jpg`, n }));
const heroNow = () => HERO[dayIdx() % HERO.length];
const BANDS = ['miasto', 'morze', 'gory'];
const IMG = (src, alt = '', cls = '', alt2 = '') => `<img class="${cls}" src="${esc(src)}" alt="${esc(alt)}" loading="lazy" ${alt2 ? `data-alt="${esc(alt2)}" onerror="if(this.dataset.alt){this.src=this.dataset.alt;this.dataset.alt=''}else this.remove()"` : 'onerror="this.remove()"'}>`;
const SV = (d, extra = '') => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${extra}>${d}</svg>`;
const I = {
  pin: SV('<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.500C5 14.800 12 21 12 21z" fill="currentColor"/><circle cx="12" cy="9.500" r="2.500" fill="#03122f" stroke="none"/>'),
  cal: SV('<rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 10h16M9 15l2 2 4-4"/>'),
  people: SV('<circle cx="9" cy="8" r="3.500" fill="currentColor"/><path d="M3 20c0-3.500 2.500-6 6-6s6 2.500 6 6z" fill="currentColor"/><circle cx="17" cy="9" r="2.500"/><path d="M17 14c2.500 0 4 2 4 5"/>'),
  filter: SV('<path d="M4 5h16l-6.500 7.500V19l-3 1.500v-8z"/>'),
  bed: SV('<path d="M3 18V7M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5"/><circle cx="7" cy="11" r="1.800"/>'),
  search: SV('<circle cx="11" cy="11" r="6.500"/><path d="M16 16l5 5"/>', 'stroke-width="2.600"'),
  plane: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.500 12c0-.9-.8-1.500-1.500-1.500h-5L10 2.500H8l2.500 8H6L4.500 8.500H3L4 12l-1 3.500h1.500L6 13.500h4.500l-2.500 8h2l5-8h5c.7 0 1.500-.6 1.500-1.500z"/></svg>',
  check: SV('<path d="M5 12.500l4.500 4.500L19 7.500"/>', 'stroke-width="3"'),
  map: SV('<path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2zM9 4v14M15 6v14"/>'),
  coin: SV('<ellipse cx="12" cy="6.500" rx="7" ry="3"/><path d="M5 6.500v5c0 1.700 3 3 7 3s7-1.300 7-3v-5M5 11.500v5c0 1.700 3 3 7 3s7-1.300 7-3v-5"/>'),
  doc: SV('<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>'),
  home: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3l9 8h-2.500v9.500h-5V15h-3v5.500h-5V11H3z"/></svg>',
  star: SV('<path d="M12 3.500l2.600 5.400 5.900.8-4.300 4.100 1 5.900-5.200-2.800-5.200 2.800 1-5.900L3.500 9.700l5.900-.8z"/>'),
  heart: SV('<path d="M12 20s-8-4.800-8-10.500A4.500 4.500 0 0 1 12 7a4.500 4.500 0 0 1 8 2.500C20 15.200 12 20 12 20z"/>'),
  user: SV('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.500-7 8-7s8 3 8 7"/>'),
  bag: SV('<rect x="3.500" y="7" width="17" height="13" rx="2.500"/><path d="M9 7V5.500A1.500 1.500 0 0 1 10.500 4h3A1.500 1.500 0 0 1 15 5.500V7M3.500 12.500h17M10.500 12.500v2h3v-2"/>'),
  bell: SV('<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 21h4"/>'),
  menu: SV('<path d="M4 6h16M4 12h16M4 18h16"/>', 'stroke-width="2.400"'),
  share: SV('<circle cx="6" cy="12" r="2.500"/><circle cx="18" cy="6" r="2.500"/><circle cx="18" cy="18" r="2.500"/><path d="M8 11l8-4M8 13l8 4"/>'),
  dots: SV('<circle cx="12" cy="5" r="1.300" fill="currentColor"/><circle cx="12" cy="12" r="1.300" fill="currentColor"/><circle cx="12" cy="19" r="1.300" fill="currentColor"/>'),
  bulb: SV('<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.500 11c.7.600 1 1.300 1 2h5c0-.7.300-1.400 1-2A6 6 0 0 0 12 3z"/>'),
  train: SV('<rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14M8 21l2-4M16 21l-2-4"/><circle cx="8.500" cy="14" r=".9" fill="currentColor"/><circle cx="15.500" cy="14" r=".9" fill="currentColor"/>'),
  walk: SV('<circle cx="13" cy="4.500" r="1.800" fill="currentColor"/><path d="M9 21l2-6-2-3 1-5 3 1 2 3h3M11 15l3 2 1 4M10 7l-3 3v3"/>'),
  fork: SV('<path d="M7 3v8M4 3v5a3 3 0 0 0 6 0V3M7 11v10M17 3c-2 1-3 4-3 8h3v10"/>'),
  car: SV('<path d="M4 16v-3l2-5h12l2 5v3zM4 16v2M20 16v2"/><circle cx="7.500" cy="13.500" r=".8" fill="currentColor"/><circle cx="16.500" cy="13.500" r=".8" fill="currentColor"/>'),
  sum: SV('<rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 10h16M9 15l2 2 4-4"/>'),
};
const tabbar = (act) => `<nav class="tabbar" aria-label="Główna nawigacja">${[['home', 'Start', I.home, viewHome], ['trips', 'Podróże', I.cal, viewTrips], ['insp', 'Inspiracje', I.star, viewInspire], ['fav', 'Ulubione', I.heart, viewFav], ['prof', 'Profil', I.user, viewProfile]].map(([k, l, ic]) => `<button data-nav="${k}" class="${act === k ? 'on' : ''}">${ic}<span>${l}</span></button>`).join('')}</nav>`;
const NAV = () => ({ home: viewHome, trips: viewTrips, insp: viewInspire, tours: viewTours, fav: viewFav, prof: viewProfile });
const bindNav = () => $$('[data-nav]').forEach((b) => { b.onclick = () => NAV()[b.dataset.nav](); });
const CN_ = { beach: 'plaża', city: 'zwiedzanie', ski: 'narty', nature: 'przyroda', party: 'imprezy', family: 'z rodziną', food: 'jedzenie', romance: 'we dwoje', lake: 'jeziora', spa: 'uzdrowisko i spa' };
const CN_PL = { beach: 'morze', city: 'miasto', ski: 'góry i narty', nature: 'przyroda', family: 'z rodziną', romance: 'we dwoje', lake: 'jeziora', spa: 'uzdrowisko i spa' };
function destLabel() {
  const t = S.q.dest;
  if (t.mode === 'city') { const n = t.ids.map((i) => S.dests.find((d) => d.id === i)?.name).filter(Boolean); return n.length ? n.join(', ') : 'Wybierz miejsce'; }
  if (t.mode === 'country') return t.countries.length ? t.countries.join(', ') + (t.style ? `, ${CN_[t.style]}` : '') : 'Wybierz kraj';
  const cn = isPL() ? CN_PL : CN_;
  if (t.mode === 'style') return `${isPL() ? '' : 'Styl: '}${cn[t.style] ? cn[t.style][0].toUpperCase() + cn[t.style].slice(1) : 'wybierz'}${isPL() && S.q.maxHours ? `, do ${S.q.maxHours} h jazdy` : ''}`;
  return (isPL() ? 'Cała Polska' : 'Gdziekolwiek') + (t.style ? `, ${cn[t.style]}` : '') + (isPL() && S.q.maxHours ? `, do ${S.q.maxHours} h jazdy` : '');
}
function whenLabel() {
  const w = S.q.when;
  if (w.mode === 'month') return `${MONTHS[w.month - 1][0].toUpperCase()}${MONTHS[w.month - 1].slice(1)} ${w.year}`;
  if (w.mode === 'range' && w.preset && w.preset !== 'own') return `${PRESETS[w.preset].l}, ${w.pyear}`;
  return w.from && w.to ? `${dateL(w.from)} – ${dateL(w.to)}` : 'Wybierz daty';
}
const paxLabel = () => { const n = S.q.pax.adults + S.q.pax.children; return `${n} ${n === 1 ? 'osoba' : n < 5 ? 'osoby' : 'osób'}`; };
const stayLabel = () => ({ balanced: 'Najlepszy stosunek', luxury: 'Wysoki (4★–5★)', cheap: 'Najniższa cena', center: 'Blisko centrum' }[S.q.stay.pref]);

/* ---------- Okno z ustawieniem jednego kroku ---------- */
function openStep(i, then) {
  S.modal = { then };
  S.step = i;
  document.body.insertAdjacentHTML('beforeend', '<div class="modal" id="modal"><div class="sheet" id="msheet"></div></div>');
  $('#modal').onclick = (e) => { if (e.target.id === 'modal') closeModal(); };
  STEPS[i]($('#msheet'));
}
function closeModal() {
  const m = S.modal; S.modal = null;
  $('#modal')?.remove();
  save('prefs', S.q);
  if (m?.then) m.then(); else goForm();
}

/* ---------- Start: kafelki ---------- */
const ZT = [['pl', 'art/e/polska.jpg', 'W Polsce', 'Autem, pociągiem albo samolotem'], ['eu', 'art/e/europa.jpg', 'Europa', 'Loty, noclegi i plan zwiedzania'], ['world', 'art/e/swiat.jpg', 'Poza Europą', 'Egipt, Tunezja, Maroko, Emiraty i więcej'], ['tours', 'art/e/biura.jpg', 'Z biurem podróży', 'Oferty biur i porównanie z wyjazdem samemu']];
function viewHome() {
  if (S.reloadLater) { S.reloadLater = false; freshReload(); }
  setBackdrop({ photo: heroNow()?.src, dim: true, strip: true });
  const soon = load('trips', []).find((t) => t.option.dep >= new Date().toISOString().slice(0, 10));
  const last = load('last', null);
  app.innerHTML = `<section class="home">
    <header class="hd"><img src="icons/logo-96.png" alt="" width="56" height="56"><div><strong>Globtroter</strong><span>Twój kompleksowy plan podróży</span></div>
      <button class="ico" id="bell" aria-label="Najbliższa podróż">${I.bell}${soon ? '<i></i>' : ''}</button><button class="ico" id="burger" aria-label="Menu">${I.menu}</button></header>
    <div class="headline"><h1>Dokąd <em>jedziemy?</em></h1><p>Dojazd · Noclegi · Plan zwiedzania · Gastronomia</p></div>
    <div class="ztiles">${ZT.map(([k, img, t, sub]) => `<button class="ztile" data-z="${k}"><img src="${img}" alt="" loading="lazy"><span><b>${t}</b><small>${sub}</small></span></button>`).join('')}</div>
    ${last && Date.now() - last.t < 6 * 36e5 ? '<button class="lastr" id="lastr">Wróć do ostatnich wyników</button>' : ''}
  </section>${tabbar('home')}`;
  $$('[data-z]').forEach((b) => { b.onclick = () => { const z = b.dataset.z; if (z === 'tours') return viewTours(); setZone(z); viewFly(); }; });
  $('#bell').onclick = () => (soon ? viewTrips() : toast('Nie masz jeszcze zaplanowanej podróży.'));
  $('#burger').onclick = viewProfile;
  const lr = $('#lastr'); if (lr) lr.onclick = () => { const l = load('last'); S.result = l.result; S.q = l.q; if (l.zone) S.zone = l.zone; viewResults(); };
  bindNav();
  app.scrollTop = 0;
}
/* ---------- Formularz jednej części: Polska, Europa albo poza Europą ---------- */
// Lotniska w zasięgu, tak samo jak w kroku „Skąd startujesz?”
function nearAir() {
  const q = S.q; if (!q.origin) return [];
  return S.airports.filter((a) => !['BY', 'RU', 'UA'].includes(a.cc)).map((a) => ({ ...a, d: km(q.origin.lat, q.origin.lon, a.lat, a.lon) }))
    .filter((a) => (a.cc === 'PL' && a.d < Math.max(q.radius, 700)) || (a.d < q.radius && a.large)).sort((a, b) => a.d - b.d);
}
const fromLabel = () => { const o = S.q.origin; if (!o) return 'Ustaw miejsce wyjazdu'; if (isPL()) return o.label; const A = nearAir(); return `${o.label}${A.length ? ` · lotniska ${A.slice(0, 3).map((a) => a.iata).join(', ')}${A.length > 3 ? ` i ${A.length - 3} więcej` : ''}` : ''}`; };
const PACE_L = { slow: 'spokojne tempo', normal: 'tempo normalne', fast: 'intensywnie' };
function settRows() {
  const q = S.q; const t = q.transport; const st = q.stay; const pl = q.plan || {}; const b = q.bags || {};
  const num = (v) => String(v).replace('.', ',');
  const stayS = `do ${zl(st.budget)}, ${stayLabel().toLowerCase()}, ocena ${st.minRating ? num(st.minRating) + '+' : 'dowolna'}${st.breakfast ? ', ze śniadaniem' : ''}`;
  const plan = `${PACE_L[pl.pace] || 'tempo normalne'}${pl.interests?.length ? `, ${pl.interests.length} ${pl.interests.length === 1 ? 'zainteresowanie' : 'zainteresowania'}` : ', bez preferencji'}${isPL() ? ', wycieczki autem do 120 km' : ''}`;
  if (isPL()) return [
    ['car', I.car, 'Auto', `${num(t.consumption)} l / 100 km, paliwo ${num(t.fuelPrice)} zł/l`, 4],
    ['lim', I.pin, 'Ile jazdy', q.maxHours ? `najwyżej ${q.maxHours} h w jedną stronę` : 'bez limitu godzin jazdy', 1],
    ['bed', I.bed, 'Nocleg', stayS, 5],
    ['map', I.map, 'Zwiedzanie', plan, 6]];
  return [
    ['fly', I.plane, 'Loty', `${q.direct ? 'tylko bez przesiadek' : 'z przesiadkami'}, ${b.cabin ? 'bagaż do kabiny' : 'mały plecak'}${b.checked ? ' i rejestrowany' : ''}, ${q.earliest ? 'wyloty od 7:00' : 'o każdej porze'}`, 3],
    ['acc', I.car, 'Dojazd na lotnisko', t.mode === 'public' ? 'komunikacją' : t.mode === 'dropoff' ? `ktoś podwiezie, ${num(t.consumption)} l` : `autem ${num(t.consumption)} l, parking ${t.parkingOverride != null ? zl(t.parkingOverride) + ' za tydzień' : 'według cennika'}`, 4],
    ['bed', I.bed, 'Nocleg', stayS, 5],
    ['map', I.map, 'Zwiedzanie', plan, 6]];
}
function viewFly() {
  const h = heroNow();
  setBackdrop({ photo: h?.src, dim: true, strip: true });
  S.q.dest.zone = S.zone;
  const ZH = { pl: 'Wyjazd <em>w Polsce</em>', eu: 'Wakacje <em>w Europie</em>', world: 'Wakacje <em>poza Europą</em>' }[S.zone];
  const field = (id, ic, lab, val, cls = '') => `<button class="fld ${cls}" id="${id}">${ic}<span><small>${lab}</small><b>${esc(val)}</b></span>${cls.includes('wide') ? SV('<path d="M9 5l7 7-7 7"/>', 'class="chev"') : ''}</button>`;
  const rows = settRows(); const open = !!S.setOpen;
  app.innerHTML = `<section class="home">
    <header class="hd"><button class="round" id="zb" aria-label="Wstecz">${ICON.back}</button><div><strong>${{ pl: 'W Polsce', eu: 'Europa', world: 'Poza Europą' }[S.zone]}</strong><span>Globtroter</span></div></header>
    <div class="headline zh"><h1>${ZH}</h1></div>
    <div class="form">
      ${field('f-from', I.home, 'Skąd?', fromLabel(), 'wide')}
      ${field('f-dest', I.pin, isPL() ? 'Dokąd jedziesz?' : 'Dokąd chcesz lecieć?', destLabel(), 'wide')}
      <div class="two">${field('f-when', I.cal, 'Kiedy?', whenLabel())}${field('f-pax', I.people, isPL() ? 'Kto jedzie?' : 'Kto leci?', paxLabel())}</div>
      <button class="cta" id="go">${I.search}Zaplanuj podróż</button>
      <label class="lab2" for="say">albo napisz, czego szukasz, a uzupełnię formularz</label>
      <div class="say small"><input id="say" maxlength="400" placeholder="${isPL() ? 'np. święta we dwoje w górach' : 'np. tydzień na plaży w lipcu, 2 osoby'}"><button id="sayb" aria-label="Uzupełnij formularz">${I.search}</button></div>
    </div>
    <div class="sett ${open ? 'open' : ''}">
      <button class="sett-h" id="seth" aria-expanded="${open}"><span><b>Twoje ustawienia</b><small>${open ? 'Dotknij wiersza, żeby zmienić' : rows.map((r) => r[2]).join(' · ')}</small></span>${SV('<path d="M6 9l6 6 6-6"/>', 'class="chev"')}</button>
      ${open ? rows.map(([k, ic, t, sub, i]) => `<button class="srow" data-step="${i}">${ic}<span><b>${t}</b><small>${esc(sub)}</small></span>${SV('<path d="M9 5l7 7-7 7"/>', 'class="chv"')}</button>`).join('') : ''}
    </div>
    <button class="ghost" id="f-more">${I.cal}Przejdź wszystko krok po kroku</button>
  </section>${tabbar('home')}`;
  $('#zb').onclick = viewHome;
  const say = async () => { const t = $('#say').value.trim(); if (!t) return; toast('Czytam…'); try { const did = await LV.askSentence(t); if (!did.length) return toast('Nie wyłapałem szczegółów. Wybierz je w formularzu.'); if (S.q.dest?.ids?.length) { const d0 = S.dests.find((x) => x.id === S.q.dest.ids[0]); if (d0 && !inZone(d0.cc)) { const keep = S.q.dest; setZone(zoneOf(d0.cc)); S.q.dest = { ...keep, zone: S.zone }; } } viewFly(); toast(`Uzupełnione: ${did.join(', ')}. Sprawdź i szukaj.`); } catch (e) { toast(e.message); } };
  $('#sayb').onclick = say; $('#say').onkeydown = (e) => { if (e.key === 'Enter') say(); };
  $('#f-from').onclick = () => openStep(0);
  $('#f-dest').onclick = () => openStep(1);
  $('#f-when').onclick = () => openStep(2);
  $('#f-pax').onclick = () => openStep(3);
  $('#seth').onclick = () => { const y = app.scrollTop; S.setOpen = !S.setOpen; viewFly(); app.scrollTop = y; };
  $$('[data-step]').forEach((b) => { b.onclick = () => openStep(+b.dataset.step); });
  $('#f-more').onclick = () => { S.step = 0; viewWizard(); };
  $('#go').onclick = () => {
    // Nowa osoba bez ustawionego startu przechodzi kreator krok po kroku
    if (!S.q.origin) { S.step = 0; return viewWizard(); }
    const t = S.q.dest;
    if ((t.mode === 'city' && !t.ids.length) || (t.mode === 'country' && !t.countries.length) || (t.mode === 'style' && !t.style)) return openStep(1, reviewSheet);
    reviewSheet();
  };
  bindNav();
  app.scrollTop = 0;
}
// Podsumowanie przed szukaniem: pomyłkę widać, zanim czekasz kilka minut
function reviewSheet() {
  const q = S.q; const n = q.pax.adults + q.pax.children;
  const R = [['Skąd', fromLabel(), 0], ['Dokąd', destLabel() + (isPL() ? '' : S.zone === 'world' ? ', poza Europą' : ', w Europie'), 1], ['Kiedy', whenLabel(), 2],
    ['Kto', `${q.pax.adults} ${q.pax.adults === 1 ? 'dorosły' : 'dorosłych'}${q.pax.children ? `, ${q.pax.children} ${q.pax.children === 1 ? 'dziecko' : 'dzieci'}` : ''}${isPL() ? '' : q.bags?.cabin ? ', bagaż do kabiny' : ', mały plecak'}`, 3]];
  settRows().forEach(([, , t, sub, i]) => R.push([t, sub, i]));
  document.body.insertAdjacentHTML('beforeend', `<div class="modal" id="modal"><div class="sheet rev"><h2 class="big" style="font-size:30px">Sprawdź, zanim zacznę</h2><p class="sub">Szukanie trwa zwykle 1–5 minut. Jeśli coś się nie zgadza, popraw to teraz.</p>
    ${R.map(([l, v, i]) => `<div class="kvr"><span>${l}</span><b>${esc(v)}</b><button data-ed="${i}">zmień</button></div>`).join('')}
    <div class="nav"><button class="btn" id="rgo">${I.search}Szukaj</button></div></div></div>`);
  const close = () => $('#modal')?.remove();
  $('#modal').onclick = (e) => { if (e.target.id === 'modal') close(); };
  $$('[data-ed]').forEach((b) => { b.onclick = () => { close(); openStep(+b.dataset.ed, () => { viewFly(); reviewSheet(); }); }; });
  $('#rgo').onclick = () => { close(); save('prefs', S.q); viewSearch(); };
}

const ageLabel = (dep) => { const d = Math.ceil((new Date(dep + 'T12:00') - Date.now()) / 864e5); return d > 1 ? `za ${d} dni` : d === 1 ? 'jutro' : d === 0 ? 'dziś' : 'minęła'; };
const pageTop = (t, sub = '') => `<div class="ptop"><h2>${esc(t)}</h2>${sub ? `<p>${esc(sub)}</p>` : ''}</div>`;
function viewTrips() {
  const T = load('trips', []); const today = new Date().toISOString().slice(0, 10);
  const act = T.map((t, i) => [t, i]).filter(([t]) => t.option.ret >= today).sort((a, b) => a[0].option.dep.localeCompare(b[0].option.dep));
  const old = T.map((t, i) => [t, i]).filter(([t]) => t.option.ret < today).sort((a, b) => b[0].option.dep.localeCompare(a[0].option.dep));
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const card = ([t, i], past) => { const p = photoOf(t.dest.id, 700); const sp = Object.values(t.live?.s?.exp || {}).filter((e) => !e.x).reduce((n, e) => n + e.pln, 0); return `<button class="pcard" data-trip="${i}">${p ? IMG(p.src, p.n) : ''}<div><h3>${esc(t.dest.name.replace(/\s*\(.*/, ''))}</h3><p>${dateL(t.option.dep)} – ${dateL(t.option.ret)}${past ? (sp ? `, wydane ${zl(sp)}` : '') : `, ${ageLabel(t.option.dep)}`}${t.live?.own === false ? ', wspólny' : ''}</p></div></button>`; };
  app.innerHTML = `<section class="tabpage">${pageTop('Moje podróże', T.length ? 'Działają bez internetu, a kopia jest na serwerze.' : '')}
    ${act.length ? act.map((x) => card(x)).join('') : `<div class="wcard emptyc"><img src="art/e/podroze.jpg" alt=""><h3>${T.length ? 'Brak nadchodzących wyjazdów' : 'Tu pojawią się Twoje wyjazdy'}</h3><p>Po wybraniu lotu i hotelu plan zapisze się tutaj.</p><div class="acts"><button class="btn" id="st">Zaplanuj podróż</button></div></div>`}
    <div class="linkset"><button class="btn line small lightb" id="nwt">Wakacje z biurem</button><button class="btn line small lightb" id="nw">Własny wyjazd</button></div>
    <h3 class="sec">Propozycje dla innych</h3>
    <button class="wcard prop-entry" id="pdr">${I.heart}<span><b>${propDraft().items.length ? `Propozycja w przygotowaniu: ${propDraft().items.length} ${propDraft().items.length === 1 ? 'opcja' : 'opcje'}` : 'Nowa propozycja wyjazdu'}</b><small>${propDraft().items.length ? 'Dodaj wiadomość i wyślij link' : 'W wynikach albo w planie dotknij „Dodaj do propozycji”'}</small></span></button>
    ${load('props', []).map((x) => `<button class="wcard prop-entry" data-ps="${esc(x.edit)}">${I.share || I.heart}<span><b>${esc(x.title)}</b><small>${x.n} ${x.n === 1 ? 'opcja' : 'opcje'}, wysłana ${dateL(new Date(x.t).toISOString().slice(0, 10))}</small></span></button>`).join('')}
    ${old.length ? `<h3 class="sec">Zakończone</h3>${old.map((x) => card(x, true)).join('')}` : ''}
  </section>${tabbar('trips')}`;
  $$('[data-trip]').forEach((b) => { b.onclick = () => { S.plan = load('trips', [])[+b.dataset.trip]; LV.applyDays(S.plan); S.tab = 'sum'; viewPlan(); LV.syncNow(S.plan, () => S.tab === 'sum' && viewPlan()).catch(() => {}); }; });
  const st = $('#st'); if (st) st.onclick = viewHome;
  $('#nw').onclick = () => LV.viewNew();
  $('#pdr').onclick = viewPropDraft;
  $$('[data-ps]').forEach((b) => { b.onclick = () => viewPropSent(b.dataset.ps); });
  $('#nwt').onclick = async () => { await data().catch(() => {}); LV.viewTour(); };
  bindNav(); app.scrollTop = 0;
}
// Biura podróży: jedna lista ofert z wielu biur. Rezerwacja zawsze na stronie biura.
const TP_SLUG = { ES: 'hiszpania', GR: 'grecja', TR: 'turcja', EG: 'egipt', BG: 'bulgaria', HR: 'chorwacja', IT: 'wlochy', PT: 'portugalia', CY: 'cypr', AL: 'albania', TN: 'tunezja', MA: 'maroko', MT: 'malta', ME: 'czarnogora' };
const TP_MON = ['styczen', 'luty', 'marzec', 'kwiecien', 'maj', 'czerwiec', 'lipiec', 'sierpien', 'wrzesien', 'pazdziernik', 'listopad', 'grudzien'];
const BOARDS = [['', 'Każde'], ['ai', 'All inclusive'], ['hb', 'Śniadania i kolacje'], ['bb', 'Śniadania']];
const boardOf = (b) => { const t = (b || '').toLowerCase(); return /all|ultra/.test(t) ? 'ai' : /obiadokol|kolac|hb|half|pełne|fb/.test(t) ? 'hb' : /śniad|bb|breakfast/.test(t) ? 'bb' : ''; };
const nightsL = (n) => `${n} ${n === 1 ? 'noc' : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? 'noce' : 'nocy'}`;
const starsL = (n) => (n ? '★'.repeat(Math.floor(n)) + (n % 1 ? '½' : '') : '');
function nearestOrigin(meta) {
  const o = S.q.origin; if (!o?.lat) return null;
  let best = null, bd = 1e9;
  for (const [c] of meta.origins) { const a = S.airports.find((x) => x.iata === c); if (!a) continue; const d = km(o.lat, o.lon, a.lat, a.lon); if (d < bd) { bd = d; best = c; } }
  return best;
}
async function viewTours() {
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<section class="tabpage">${pageTop('Biura podróży', 'Oferty wielu biur w jednym miejscu. Rezerwujesz na stronie biura.')}<div class="wcard"><p class="hint">Wczytuję listę biur…</p></div></section>${tabbar('tours')}`;
  bindNav();
  if (!S.tmeta) { try { await data(); S.tmeta = await api('/api/tours/meta'); } catch (e) { $('.tabpage .wcard').innerHTML = `<p>${esc(e.message)}</p><div class="acts"><button class="btn small" id="rt">Spróbuj ponownie</button></div>`; $('#rt').onclick = viewTours; return; } }
  const M = S.tmeta; const tq = S.tq || (S.tq = load('tq', null) || {});
  if (!tq.cc) tq.cc = M.countries.find(([c]) => c === 'ES') ? 'ES' : M.countries[0]?.[0];
  const mons = []; const d0 = new Date(); for (let i = 0; i < 18; i++) { const d = new Date(d0.getFullYear(), d0.getMonth() + i, 1); mons.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`); }
  if (!mons.includes(tq.ym)) tq.ym = S.q.when.mode === 'month' && mons.includes(`${S.q.when.year}-${String(S.q.when.month).padStart(2, '0')}`) ? `${S.q.when.year}-${String(S.q.when.month).padStart(2, '0')}` : mons[1];
  if (tq.origin === undefined) tq.origin = nearestOrigin(M);
  const monL = (ym) => `${MONTHS[+ym.slice(5) - 1][0].toUpperCase()}${MONTHS[+ym.slice(5) - 1].slice(1)} ${ym.slice(0, 4)}`;
  $('.tabpage').innerHTML = `${pageTop('Biura podróży', 'Oferty wielu biur w jednym miejscu. Rezerwujesz na stronie biura.')}
    <div class="wcard tform">
      <label>Kraj<select id="tcc">${M.countries.map(([c, n]) => `<option value="${c}" ${c === tq.cc ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
      <label>Wyjazd w miesiącu<select id="tym">${mons.map((m) => `<option value="${m}" ${m === tq.ym ? 'selected' : ''}>${monL(m)}</option>`).join('')}</select></label>
      <label>Wylot z<select id="tor"><option value="">Dowolne lotnisko</option>${M.origins.map(([c, n]) => `<option value="${c}" ${c === tq.origin ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
      <button class="btn" id="tgo">${I.search} Pokaż oferty</button>
      <p class="hint">Sprawdzam ${M.ops.length} biur: ${M.ops.map((o) => esc(o.name)).join(', ')}.</p>
      <button class="btn line small" id="town">Mam już wykupione wakacje: ułóż plan</button>
    </div>
    <div id="tres">${S.tres && S.tres.key === JSON.stringify([tq.cc, tq.ym, tq.origin]) ? '' : `<div class="wcard emptyc"><img src="art/e/biura.jpg" alt="" onerror="this.remove()"><h3>Wybierz kraj i miesiąc</h3><p>Pokażę oferty wszystkich biur razem, od najtańszej. Każda prowadzi prosto do tej oferty na stronie biura.</p></div>`}</div>
    <div id="tmore"></div>`;
  const read = () => { tq.cc = $('#tcc').value; tq.ym = $('#tym').value; tq.origin = $('#tor').value || null; save('tq', tq); };
  ['#tcc', '#tym', '#tor'].forEach((k) => { $(k).onchange = read; });
  $('#tgo').onclick = () => { read(); toursSearch(); };
  $('#town').onclick = async () => { await data().catch(() => {}); LV.viewTour(); };
  if (S.tres && S.tres.key === JSON.stringify([tq.cc, tq.ym, tq.origin])) drawTours(); else drawOthers();
  app.scrollTop = 0;
}
async function toursSearch() {
  const tq = S.tq; const key = JSON.stringify([tq.cc, tq.ym, tq.origin]); const my = Symbol();
  S.tres = { key, offers: [], ops: {}, state: 'running', show: 40, sort: S.tres?.sort || 'price', board: S.tres?.board || '', stars: S.tres?.stars || 0, len: S.tres?.len || '', tok: my };
  drawTours();
  try {
    const { id } = await api('/api/tours', { cc: tq.cc, ym: tq.ym, origin: tq.origin });
    let n = 0;
    for (let i = 0; i < 400; i++) {
      if (S.tres?.tok !== my) return;
      const j = await api(`/api/tours/job?id=${id}&n=${n}`);
      if (S.tres?.tok !== my) return;
      n = j.n; S.tres.offers.push(...j.offers); S.tres.ops = j.ops; S.tres.state = j.state;
      if ($('#tres')) drawTours();
      if (j.state === 'done') return;
      await new Promise((r) => setTimeout(r, 2500));
    }
  } catch (e) { if (S.tres?.tok === my) { S.tres.state = 'error'; S.tres.err = e.message; if ($('#tres')) drawTours(); } }
}
function drawTours() {
  const R = S.tres; const el = $('#tres'); if (!el || !R) return;
  const M = S.tmeta; const name = (op) => M.ops.find((o) => o.id === op)?.name || op;
  const NF = { '': () => true, s: (n) => n && n <= 5, w: (n) => n >= 6 && n <= 8, l: (n) => n >= 9 };
  let L = R.offers.filter((x) => (!R.board || boardOf(x.board) === R.board) && (!R.stars || (x.stars || 0) >= R.stars) && NF[R.len || ''](x.nights));
  const by = { price: (a, b) => a.ppp - b.ppp, stars: (a, b) => (b.stars || 0) - (a.stars || 0) || a.ppp - b.ppp, date: (a, b) => a.dep.localeCompare(b.dep) || a.ppp - b.ppp };
  L.sort(by[R.sort]);
  const ops = Object.entries(R.ops).filter(([, s]) => s.state !== 'none');
  const opLine = ops.map(([op, s]) => `<span class="top ${s.state}">${esc(s.name)}${s.state === 'ok' ? ` <b>${s.count}</b>` : s.state === 'err' ? ' ✕' : s.state === 'run' || s.state === 'wait' ? ' …' : ''}</span>`).join('');
  const busy = R.state === 'running';
  const card = (x) => `<div class="tcard"><div class="th"><div><h3>${esc(x.name)}</h3><p class="ts">${starsL(x.stars)} ${esc(x.place || '')}</p></div><span class="tbo">${esc(name(x.op))}</span></div>
    <div class="tg"><span>${I.cal}${dateL(x.dep)}${x.ret ? ` – ${dateL(x.ret)}` : ''}${x.nights ? `, ${nightsL(x.nights)}` : ''}</span>${x.board ? `<span>${I.fork}${esc(x.board)}</span>` : ''}${x.from ? (/^[A-Z]{3}$/.test(x.from) ? `<span>${I.plane}wylot: ${esc(S.tmeta.origins.find(([c]) => c === x.from)?.[1] || S.airports.find((a) => a.iata === x.from)?.city || x.from)}</span>` : `<span>${I.car}wyjazd: ${esc(x.from)}</span>`) : ''}${x.kind && x.kind !== 'wypoczynek' ? `<span>${I.map}${esc(x.kind)}</span>` : ''}${x.rating ? `<span>${I.star}ocena ${String(x.rating).replace('.', ',')}/10</span>` : ''}</div>
    <div class="tp"><div><b>${zl(x.ppp)}</b> <small>za osobę${x.approx ? ', orientacyjnie' : ''}</small>${x.total && x.adults ? `<p class="hint">${zl(x.total)} za ${x.adults} ${osob(x.adults)}</p>` : ''}</div><a class="btn small" href="${url(x.url)}" target="_blank" rel="noopener">Zobacz w biurze</a></div><div class="tacts"><button class="sm tbuy" data-cmp="${R.offers.indexOf(x)}">Ile wyjdzie samemu?</button><button class="sm tbuy" data-buy="${R.offers.indexOf(x)}">Kupiłem: ułóż plan</button></div><div class="tcmp" id="cmp${R.offers.indexOf(x)}">${cmpHtml(x)}</div></div>`;
  el.innerHTML = `<div class="wcard tbar"><div class="tops">${opLine}</div>
    ${busy ? `<p class="hint"><span class="tspin"></span> Przeglądam strony biur. Pierwsze wyszukiwanie może potrwać do dwóch minut, potem wyniki są od razu.</p>` : ''}
    ${R.state === 'error' ? `<p class="hint">${esc(R.err)}</p>` : ''}
    <div class="seg" id="tsort">${[['price', 'Najtańsze'], ['stars', 'Standard'], ['date', 'Termin']].map(([k, l]) => `<button data-ts="${k}" aria-pressed="${R.sort === k}">${l}</button>`).join('')}</div>
    <div class="pills dark">${BOARDS.map(([k, l]) => `<button data-tb="${k}" class="${R.board === k ? 'on' : ''}">${l}</button>`).join('')}${[[0, 'Każdy hotel'], [3, '3★ i więcej'], [4, '4★ i więcej'], [5, '5★']].map(([k, l]) => `<button data-tst="${k}" class="${R.stars === k ? 'on' : ''}">${l}</button>`).join('')}</div>
    <div class="pills dark">${[['', 'Każda długość'], ['w', 'Tydzień'], ['l', 'Dłużej'], ['s', 'Krótko, do 5 nocy']].map(([k, l]) => `<button data-tl="${k}" class="${(R.len || '') === k ? 'on' : ''}">${l}</button>`).join('')}</div>
    <p class="hint">${L.length ? `${L.length} ofert${R.offers.length !== L.length ? ` z ${R.offers.length}` : ''}.` : busy ? '' : 'Brak ofert dla tych ustawień.'} Ceny ze stron biur z chwili odczytu, za osobę przy dwóch dorosłych. Ostateczna cena jest zawsze u biura.</p></div>
    ${!L.length && !busy ? `<div class="wcard emptyc"><img src="art/e/brak.jpg" alt="" onerror="this.remove()"><h3>Nic nie znalazłem</h3><p>Zmień miesiąc, lotnisko wylotu albo filtry. Możesz też sprawdzić porównywarki niżej.</p></div>` : ''}
    ${L.slice(0, R.show).map(card).join('')}
    ${L.length > R.show ? `<button class="btn line small lightb" id="tsm">Pokaż kolejne (${L.length - R.show})</button>` : ''}
    ${ops.filter(([, s]) => s.state === 'ok' && s.url && (s.complete === false || (s.total && s.total > s.count))).map(([, s]) => `<a class="btn line small lightb" href="${url(s.url)}" target="_blank" rel="noopener">Wszystkie oferty ${esc(s.name)}${s.total ? ` (${s.total})` : ''}</a>`).join('')}`;
  $$('[data-ts]').forEach((b) => { b.onclick = () => { R.sort = b.dataset.ts; drawTours(); }; });
  $$('[data-tb]').forEach((b) => { b.onclick = () => { R.board = b.dataset.tb; R.show = 40; drawTours(); }; });
  $$('[data-tst]').forEach((b) => { b.onclick = () => { R.stars = +b.dataset.tst; R.show = 40; drawTours(); }; });
  $$('[data-tl]').forEach((b) => { b.onclick = () => { R.len = b.dataset.tl; R.show = 40; drawTours(); }; });
  const sm = $('#tsm'); if (sm) sm.onclick = () => { R.show += 40; drawTours(); };
  $$('[data-cmp]').forEach((b) => { b.onclick = () => compareOffer(R.offers[+b.dataset.cmp], +b.dataset.cmp); });
  $$('[data-buy]').forEach((b) => { b.onclick = () => {
    const x = R.offers[+b.dataset.buy]; const bo = boardOf(x.board) || (/bez/i.test(x.board || '') ? 'ro' : 'ai');
    S.tourF = null;
    LV.viewTour({ agency: S.tmeta.ops.find((o) => o.id === x.op)?.name || '', hq: `${x.name}, ${(x.place || '').split(',').pop().trim()}`, od: x.dep, bd: x.ret || '', of: /^[A-Z]{3}$/.test(x.from || '') ? x.from : '', bto: /^[A-Z]{3}$/.test(x.from || '') ? x.from : '', board: bo, price: x.total ? String(x.total) : '', url: x.url });
  }; });
  drawOthers();
}
function cmpHtml(x) {
  const c = x._cmp; if (!c) return '';
  if (c.state === 'run') return `<p class="hint"><span class="tspin"></span> ${esc(c.step || 'Sprawdzam')}… To trwa zwykle do minuty.</p>`;
  if (c.state === 'err') return `<p class="hint">${esc(c.error)}</p>`;
  const r = c.res; const f = r.flight; const h = r.hotel;
  const stops = (n) => (n ? `${n} ${n === 1 ? 'przesiadka' : 'przesiadki'}` : 'bez przesiadek');
  return `<div class="cmpbox">
    ${f ? `<div class="kv"><span>Lot ${esc(f.from)} ↔ ${esc(f.to)}, ${esc(f.airlines.join(', '))}<br><small>tam ${stops(f.stops)}, powrót ${stops(f.backStops)}</small></span><a href="${url(f.url)}" target="_blank" rel="noopener"><b>${zl(f.total)}</b></a></div>` : ''}
    ${h ? `<div class="kv"><span>Ten hotel w Google<br><small>${esc(h.name)}</small></span><a href="${url(h.url)}" target="_blank" rel="noopener"><b>${zl(h.total)}</b></a></div>` : ''}
    ${r.own ? `<div class="kv"><span><b>Samemu razem</b><br><small>za ${x.adults || 2} ${osob(x.adults || 2)}</small></span><b>${zl(r.own)}</b></div>` : ''}
    ${r.own && r.agency ? `<p class="cmpv ${r.diff > 0 ? 'cheap' : 'dear'}">${r.diff > 0 ? `Samemu taniej o ${zl(r.diff)}` : r.diff < 0 ? `Z biurem taniej o ${zl(-r.diff)}` : 'Wychodzi tyle samo'}</p>` : ''}
    ${r.notes.map((n) => `<p class="hint">${esc(n)}</p>`).join('')}</div>`;
}
async function compareOffer(x, i) {
  if (x._cmp && x._cmp.state !== 'err') return;
  x._cmp = { state: 'run', step: 'Start' }; const el = () => $(`#cmp${i}`); if (el()) el().innerHTML = cmpHtml(x);
  try {
    const { id } = await api('/api/tours/compare', { op: x.op, name: x.name, place: x.place, dep: x.dep, ret: x.ret, from: x.from, adults: x.adults || 2, total: x.total, board: x.board });
    for (let k = 0; k < 60; k++) {
      await new Promise((r) => setTimeout(r, 3000));
      const s = await api(`/api/tours/compare?id=${id}`); x._cmp = s; if (el()) el().innerHTML = cmpHtml(x);
      if (s.state !== 'run') return;
    }
    x._cmp = { state: 'err', error: 'Porównanie trwa za długo. Spróbuj ponownie.' };
  } catch (e) { x._cmp = { state: 'err', error: e.message }; }
  if (el()) el().innerHTML = cmpHtml(x);
}
function drawOthers() {
  const el = $('#tmore'); if (!el) return; const tq = S.tq; const m = +tq.ym.slice(5);
  const tp = TP_SLUG[tq.cc] ? `https://www.travelplanet.pl/wakacje/${TP_SLUG[tq.cc]}-${TP_MON[m - 1]}/` : 'https://www.travelplanet.pl/';
  const links = [['Travelplanet.pl', tp, 'porównuje oferty wielu biur'], ['Wakacje.pl', TP_SLUG[tq.cc] ? `https://www.wakacje.pl/wczasy/${TP_SLUG[tq.cc]}/` : 'https://www.wakacje.pl/', 'porównuje oferty wielu biur'], ['Coral Travel', 'https://www.coraltravel.pl/', ''], ['Anex Tour', 'https://anextour.com.pl/', ''], ['Join UP!', 'https://joinup.pl/', '']];
  el.innerHTML = `<div class="wcard"><h3>Pozostałe biura</h3><p class="hint">Tych stron nie mogę czytać automatycznie, więc otwórz je bezpośrednio. Porównywarki pokazują też oferty biur spoza listy wyżej.</p>
    <div class="linkset">${links.map(([n, u, d]) => `<a class="btn line small" href="${url(u)}" target="_blank" rel="noopener" title="${esc(d)}">${esc(n)}</a>`).join('')}</div></div>`;
}
const favs = () => load('fav', []);
function toggleFav(id) { const f = favs(); save('fav', f.includes(id) ? f.filter((x) => x !== id) : [...f, id]); }
const fitOf = (d, m, st) => { const c = d.climate; if (!c) return 0; const t = c.tmax[m - 1]; const s = c.sea ? c.sea[m - 1] : null; if (st === 'beach') return s == null ? 0 : Math.min(1, Math.max(0, (t - 16) / 8)) * 0.6 + Math.min(1, Math.max(0, (s - 15) / 7)) * 0.4; if (st === 'ski') return Math.min(1, Math.max(0, (9 - t) / 7)); return 1 - Math.min(1, Math.abs(t - 22) / 16); };
function destCard(d, m) {
  const p = photoOf(d.id, 700); const p2 = photoOf(d.id, 700, 1); const c = d.climate;
  return `<div class="pcard" data-dest="${d.id}" role="button" tabindex="0">${p ? IMG(p.src, p.n, '', p2 && p2.src !== p.src ? p2.src : '') : ''}<button class="heart ${favs().includes(d.id) ? 'on' : ''}" data-h2="${d.id}" aria-label="Ulubione">${I.heart}</button><div><h3>${esc(d.name.replace(/\s*\(.*/, ''))}</h3><p>${c ? `${Math.round(c.tmax[m - 1])}°C w dzień${c.sea ? `, morze ${Math.round(c.sea[m - 1])}°C` : ''}` : ''}</p></div></div>`;
}
function bindDest() {
  $$('[data-h2]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); toggleFav(b.dataset.h2); b.classList.toggle('on'); }; });
  $$('[data-dest]').forEach((b) => { b.onclick = () => openDest(b.dataset.dest); });
}
function viewInspire() {
  const m = S.q.when.mode === 'month' ? S.q.when.month : new Date().getMonth() + 1;
  S.ins = S.ins || 'city'; S.insMode = S.insMode || 'month';
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  if (S.insZone === undefined) S.insZone = S.zone || '';
  const seg = `<div class="seg insseg">${[['month', 'Na ten miesiąc'], ['guide', 'Przewodnik']].map(([k, l]) => `<button data-im="${k}" aria-pressed="${S.insMode === k}">${l}</button>`).join('')}</div>
   <div class="pills">${[['', 'Wszędzie'], ['pl', 'Polska'], ['eu', 'Europa'], ['world', 'Poza Europą']].map(([k, l]) => `<button data-iz="${k}" class="${S.insZone === k ? 'on' : ''}">${l}</button>`).join('')}</div>`;
  if (S.insMode === 'guide') { guideList(seg); return; }
  const IP = S.insZone === 'pl' ? [['city', 'Miasta'], ['beach', 'Morze'], ['ski', 'Góry'], ['lake', 'Jeziora'], ['spa', 'Uzdrowiska'], ['nature', 'Przyroda']] : [['city', 'Zwiedzanie'], ['beach', 'Plaża'], ['ski', 'Narty'], ['nature', 'Przyroda'], ['food', 'Jedzenie']];
  if (!IP.some(([k]) => k === S.ins)) S.ins = 'city';
  const L = S.dests.filter((d) => !S.insZone || inZone(d.cc, S.insZone)).map((d) => [S.insZone === 'pl' ? (d.links || 0) / 1000 : fitOf(d, m, S.ins), d]).filter(([, d]) => S.ins === 'city' ? d.tags.includes('city') : d.tags.includes(S.ins)).sort((a, b) => b[0] - a[0]).slice(0, 12).map(([, d]) => d);
  app.innerHTML = `<section class="tabpage">${pageTop('Inspiracje', `Najlepsze miejsca na ${MONTHS[m - 1]}. Zdjęcia zmieniają się codziennie o 8:00.`)}${seg}
   <div class="pills">${IP.map(([k, l]) => `<button data-i="${k}" class="${S.ins === k ? 'on' : ''}">${l}</button>`).join('')}</div>
   <div class="grid">${L.map((d) => destCard(d, m)).join('')}</div></section>${tabbar('insp')}`;
  $$('[data-i]').forEach((b) => { b.onclick = () => { S.ins = b.dataset.i; viewInspire(); }; });
  bindIns(); bindDest(); bindNav(); app.scrollTop = 0;
}
function bindIns() { $$('[data-im]').forEach((b) => { b.onclick = () => { S.insMode = b.dataset.im; viewInspire(); }; }); $$('[data-iz]').forEach((b) => { b.onclick = () => { S.insZone = b.dataset.iz; viewInspire(); }; }); }
async function countriesInfo() { return S.cinfo ||= await (await fetch('data/countries.json')).json().catch(() => ({})); }
const normQ = (s) => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
async function guideList(seg) {
  const C = await countriesInfo().catch(() => ({}));
  const cn = (cc) => C[cc]?.name || cc;
  const draw = () => {
    const q = normQ(S.gq || '');
    const L = S.dests.filter((d) => !S.insZone || inZone(d.cc, S.insZone)).filter((d) => !q || normQ(d.name).includes(q) || normQ(d.en || '').includes(q) || normQ(cn(d.cc)).includes(q));
    const by = {}; L.forEach((d) => { (by[d.cc] ||= []).push(d); });
    const groups = Object.entries(by).sort((a, b) => cn(a[0]).localeCompare(cn(b[0]), 'pl'));
    $('#gl').innerHTML = groups.length ? groups.map(([cc, ds]) => `<h3 class="gh">${esc(cn(cc))}</h3><div class="glist">${ds.sort((a, b) => a.name.localeCompare(b.name, 'pl')).map((d) => { const p = photoOf(d.id, 240); const p2 = photoOf(d.id, 240, 1); return `<button class="gitem" data-g="${d.id}">${p ? IMG(p.src, '', '', p2 && p2.src !== p.src ? p2.src : '') : `<span class="gph">${I.pin}</span>`}<span><b>${esc(d.name)}</b><small>${d.tags.includes('beach') ? 'plaża' : ''}${d.tags.includes('city') ? `${d.tags.includes('beach') ? ', ' : ''}zwiedzanie` : ''}${d.tags.includes('ski') ? 'narty' : ''}</small></span></button>`; }).join('')}</div>`).join('') : '<p class="hint">Nic nie pasuje. Spróbuj inną nazwę.</p>';
    $$('[data-g]').forEach((b) => { b.onclick = () => viewGuide(b.dataset.g); });
  };
  app.innerHTML = `<section class="tabpage">${pageTop('Inspiracje', `Przewodnik po ${S.dests.length} miejscach. Wybierz miejsce, aby zobaczyć atrakcje, pogodę i informacje praktyczne.`)}${seg}
    <div class="wcard"><input id="gq" type="search" placeholder="Szukaj miejsca albo kraju" value="${esc(S.gq || '')}" autocomplete="off"></div><div id="gl"></div></section>${tabbar('insp')}`;
  $('#gq').oninput = (e) => { S.gq = e.target.value; draw(); };
  draw(); bindIns(); bindNav(); app.scrollTop = S.gScroll || 0; S.gScroll = 0;
}
const GKIND = [['', 'Wszystko'], ['sight', 'Zabytki'], ['museum', 'Muzea'], ['church', 'Świątynie'], ['nature', 'Przyroda'], ['beach', 'Plaże'], ['park', 'Parki i ogrody']];
const KLAB = { museum: 'Muzeum', church: 'Świątynia', palace: 'Pałac', castle: 'Zamek', monument: 'Pomnik', square: 'Plac', park: 'Park', sight: 'Zabytek', ruins: 'Ruiny', bridge: 'Most', beach: 'Plaża', zoo: 'Zoo', street: 'Ulica', nature: 'Przyroda', theatre: 'Teatr', food: 'Targ' };
const kindGroup = (t) => ({ palace: 'sight', castle: 'sight', monument: 'sight', square: 'sight', ruins: 'sight', bridge: 'sight', street: 'sight', theatre: 'sight', food: 'sight', zoo: 'park' }[t] || t);
async function viewGuide(id) {
  const d = S.dests.find((x) => x.id === id); if (!d) return;
  S.gScroll = app.scrollTop;
  const back = () => { S.insMode = 'guide'; viewInspire(); };
  const p = photoOf(d.id, 1000);
  setBackdrop({ photo: p?.src || heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${esc(d.name)}</h2></div><section class="page"><div class="wcard"><p class="hint"><span class="tspin"></span> Wczytuję przewodnik…</p></div></section>`;
  $('#b').onclick = back;
  let G = { a: [] }, F = null, C = {};
  try { [G, F, C] = await Promise.all([fetch(`data/guide/${id}.json`).then((r) => r.json()), fetch(`data/food/${id}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null), countriesInfo().catch(() => ({}))]); } catch { $('.page').innerHTML = '<div class="wcard"><p>Przewodnik wymaga internetu przy pierwszym otwarciu.</p></div>'; return; }
  const ci = C[d.cc]; const c = d.climate; const A = G.a || []; const R = (F?.r || []).slice(0, 30);
  S.gk = S.gk || ''; S.gshow = 30;
  const mon = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip', 'sie', 'wrz', 'paź', 'lis', 'gru'];
  const climate = c ? `<div class="wcard"><h3>Pogoda w ciągu roku</h3><div class="clim">${mon.map((n, i) => `<div><small>${n}</small><b>${Math.round(c.tmax[i])}°</b><small>${Math.round(c.tmin[i])}°</small>${c.sea ? `<small class="sea">${Math.round(c.sea[i])}°</small>` : ''}</div>`).join('')}</div><p class="hint">Średnio w dzień i w nocy${c.sea ? ', niżej morze' : ''}. ${/NASA/.test(c.station || '') ? 'Dane: NASA POWER' : `Stacja pogodowa: ${esc(c.station || '')}`}.</p></div>` : '';
  const air = (d.air || []).map((a) => S.airports.find((x) => x.iata === a)).filter(Boolean);
  const prac = ci ? `<div class="wcard"><h3>Informacje praktyczne</h3>
    <div class="kv"><span>Dokumenty</span><b>${esc(ci.docs)}</b></div>
    <div class="kv"><span>Waluta</span><b>${esc(ci.currencyName)} (${esc(ci.currency)})</b></div>
    <div class="kv"><span>Gniazdka</span><b>${esc(ci.plugs)}</b></div><p class="hint">${esc(ci.plugNote)}</p>
    <div class="kv"><span>Język</span><b>${esc(ci.language)}</b></div>
    <div class="kv"><span>Numer alarmowy</span><b>${esc(ci.emergency)}</b></div>
    ${air.length ? `<div class="kv"><span>Lotniska</span><b>${air.map((a) => `${esc(a.city || a.name)} (${a.iata})`).join(', ')}</b></div>` : ''}
    ${ci.ekuz ? '<p class="hint">Karta EKUZ działa w tym kraju.</p>' : ''}
    <a class="btn line small" href="${url(ci.msz)}" target="_blank" rel="noopener">Ostrzeżenia i wjazd: strona MSZ</a></div>` : '';
  const draw = () => {
    const L = A.filter((x) => !S.gk || kindGroup(x.t) === S.gk);
    const kinds = GKIND.filter(([k]) => !k || A.some((x) => kindGroup(x.t) === k));
    const card = (x, i) => `<details class="gatt"><summary>${x.img ? IMG(commons(x.img, 200), '') : `<img src="${artOf(x.t)}" alt="" loading="lazy">`}<span><b>${esc(x.n)}</b><small>${esc(KLAB[x.t] || 'Zabytek')}${x.d ? '' : x.de ? ' · opis po angielsku' : ''}</small></span></summary>
      <div class="gbody">${x.img ? IMG(commons(x.img, 800), x.n, 'gimg') : ''}${x.d ? `<p>${esc(x.d)}</p>` : x.de ? `<p class="mute">${esc(x.de)}</p><p class="hint">Opis po angielsku, polskiego jeszcze nie mamy.</p>` : '<p class="hint">Opisu jeszcze nie mamy.</p>'}
      ${x.h ? `<p class="hint">Godziny otwarcia: ${esc(x.h)}. Sprawdź przed wizytą.</p>` : ''}
      <div class="linkset"><a class="btn line small" href="https://www.google.com/maps/search/?api=1&query=${x.lat},${x.lon}" target="_blank" rel="noopener">Mapa i dojazd</a>${x.web ? `<a class="btn line small" href="${url(x.web)}" target="_blank" rel="noopener">Strona miejsca</a>` : ''}${x.src ? `<a class="btn line small" href="${url(x.src)}" target="_blank" rel="noopener">Źródło opisu</a>` : ''}</div></div></details>`;
    $('#ga').innerHTML = `<div class="pills dark">${kinds.map(([k, l]) => `<button data-gk="${k}" class="${S.gk === k ? 'on' : ''}">${l}</button>`).join('')}</div>
      ${L.slice(0, S.gshow).map(card).join('')}${L.length > S.gshow ? `<button class="btn line small" id="gm">Pokaż kolejne (${L.length - S.gshow})</button>` : ''}`;
    $$('[data-gk]').forEach((b) => { b.onclick = () => { S.gk = b.dataset.gk; S.gshow = 30; draw(); }; });
    const gm = $('#gm'); if (gm) gm.onclick = () => { S.gshow += 30; draw(); };
  };
  const fv = favs().includes(d.id);
  $('.page').innerHTML = `${p ? `<div class="ghero">${IMG(p.src, d.name)}</div>` : ''}
    <div class="wcard"><h3>${esc(d.name)}${ci ? `, ${esc(ci.name)}` : ''}</h3>${d.desc ? `<p>${esc(d.desc)}</p>` : ''}
      <div class="linkset"><button class="btn small" id="gfl">${d.cc === 'PL' ? `${I.car} Zaplanuj wyjazd tutaj` : `${I.plane} Szukaj lotów tutaj`}</button><button class="btn line small" id="gto">Oferty biur</button><button class="btn line small" id="gtw">Wakacje z biurem</button><button class="btn line small" id="gfv">${I.heart} ${fv ? 'W ulubionych' : 'Do ulubionych'}</button></div></div>
    ${A.length ? `<div class="wcard"><h3>Atrakcje (${A.length})</h3><div class="dmap" id="gmap"></div><div id="ga"></div></div>` : '<div class="wcard"><p class="hint">Atrakcje dla tego miejsca jeszcze się zbierają.</p></div>'}
    ${R.length ? `<div class="wcard"><h3>Restauracje</h3>${R.map((r) => `<div class="kv"><span>${esc(r.n)}${r.c ? `<br><small>${esc(r.c.replace(/_/g, ' ').replace(/;/g, ', '))}</small>` : ''}</span><a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${r.n}, ${d.en || d.name}`)}" target="_blank" rel="noopener">mapa</a></div>`).join('')}<p class="hint">Restauracje z OpenStreetMap. Godziny i opinie sprawdź w mapach.</p></div>` : ''}
    ${climate}${prac}`;
  if (A.length) { draw(); drawGuideMap($('#gmap'), A.slice(0, 60)); }
  $('#gfl').onclick = () => openDest(d.id);
  $('#gto').onclick = () => { S.tq = { ...(S.tq || {}), cc: d.cc }; save('tq', S.tq); S.tres = null; viewTours(); };
  $('#gtw').onclick = async () => { await data().catch(() => {}); LV.viewTour({ hq: '', hotel: null }); };
  $('#gfv').onclick = () => { toggleFav(d.id); viewGuide(id); };
  app.scrollTop = 0;
}
async function drawGuideMap(el, pts) {
  try { await leaflet(); } catch { el.remove(); return; }
  if (!el.isConnected) return;
  const L = window.L; const m = L.map(el, { zoomControl: true, scrollWheelZoom: false, tap: false });
  m.attributionControl.setPrefix('');
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Esri' }).addTo(m);
  pts.forEach((p) => L.circleMarker([p.lat, p.lon], { radius: 6, color: '#fff', weight: 2, fillColor: '#e3b24a', fillOpacity: 1 }).bindTooltip(p.n).addTo(m));
  m.fitBounds(L.latLngBounds(pts.map((p) => [p.lat, p.lon])).pad(0.1), { maxZoom: 14 });
}
function viewFav() {
  const m = new Date().getMonth() + 1; const L = favs().map((i) => S.dests.find((d) => d.id === i)).filter(Boolean);
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<section class="tabpage">${pageTop('Ulubione')}${L.length ? `<div class="grid">${L.map((d) => destCard(d, m)).join('')}</div>` : '<div class="wcard emptyc"><img src="art/e/ulubione.jpg" alt=""><h3>Nic tu jeszcze nie ma</h3><p>Dotknij serca przy miejscu w Inspiracjach.</p></div>'}</section>${tabbar('fav')}`;
  bindDest(); bindNav(); app.scrollTop = 0;
}
function viewProfile() {
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const q = S.q;
  const row = (id, l, v) => `<button class="kvb" id="${id}"><span>${l}</span><b>${esc(v)}</b></button>`;
  app.innerHTML = `<section class="tabpage">${pageTop('Profil')}
   <div class="wcard"><h3>Moje ustawienia</h3>
   ${row('p0', 'Miejsce wyjazdu', q.origin?.label || 'nie ustawiono')}${row('p3', 'Osoby i bagaż', paxLabel())}
   ${row('p4', 'Dojazd na lotnisko', { car: 'Autem', dropoff: 'Podwiezie mnie', public: 'Komunikacją' }[q.transport.mode])}${row('p5', 'Nocleg', stayLabel())}${row('p6', 'Zwiedzanie i upodobania', `${{ slow: 'Spokojnie', normal: 'Normalnie', fast: 'Intensywnie' }[q.plan?.pace || 'normal']}${q.plan?.interests?.length || q.plan?.food?.length ? '' : ', bez preferencji'}`)}</div>
   ${LV.pushHtml()}<div id="wl"></div>
   <div class="wcard"><h3>Kopia na telefonie</h3><p class="mute">Plik ze wszystkimi wyjazdami. Przyda się przy zmianie telefonu albo awarii serwera. Trzymaj go u siebie, bo są w nim Twoje dane.</p><div class="acts"><button class="btn line small" id="xp">Pobierz kopię</button><label class="btn line small">Wczytaj kopię<input id="xi" type="file" accept="application/json,.json" hidden></label></div></div>
   <div class="wcard"><h3>Skąd są dane</h3><p class="mute">Loty: Google i Ryanair. Część hoteli: Google. Hotele i ceny: Xotelo. Dojazd: OSRM i Transitous. Klimat: Meteostat i Open-Meteo. Atrakcje i zdjęcia: Wikidata i Wikimedia Commons. Opisy: Wikipedia. Restauracje: OpenStreetMap. Mapa lotnicza: Esri. Kursy: NBP.</p></div>
   <p class="foot">Globtroter ${VERSION}. Aplikacja niekomercyjna.</p></section>${tabbar('prof')}`;
  [['p0', 0], ['p3', 3], ['p4', 4], ['p5', 5], ['p6', 6]].forEach(([id, i]) => { $('#' + id).onclick = () => openStep(i, viewProfile); });
  LV.bindPush(viewProfile); LV.watchDraw($('#wl'));
  $('#xp').onclick = LV.exportAll;
  $('#xi').onchange = async (e) => { try { toast(`Dodano wyjazdów: ${await LV.importAll(e.target.files[0])}.`); } catch (er) { toast(er.message); } };
  bindNav(); app.scrollTop = 0;
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
  setBackdrop({ photo: heroNow()?.src, dim: true });
}
function viewWizard() {
  backdropForStep();
  app.innerHTML = `<section class="wiz">${wizTop()}<div class="sheet" id="sheet"></div></section>`;
  $('#back').onclick = () => { if (S.step > 0) { S.step--; viewWizard(); } else goForm(); };
  STEPS[S.step]($('#sheet'));
  app.scrollTop = 0;
}
const navBtns = (label = 'Dalej', ok = true) => `<div class="nav"><button class="btn" id="next" ${ok ? '' : 'disabled'}>${S.modal ? 'Gotowe' : label}</button></div>`;
const next = () => { save('prefs', { ...S.q, origin: S.q.origin }); if (S.modal) return closeModal(); S.step++; viewWizard(); };

function stepFrom(el) {
  const q = S.q;
  const draw = () => {
    const near = q.origin ? S.airports.filter((a) => !['BY', 'RU', 'UA'].includes(a.cc)).map((a) => ({ ...a, d: km(q.origin.lat, q.origin.lon, a.lat, a.lon) }))
      .filter((a) => (a.cc === 'PL' && a.d < Math.max(q.radius, 700)) || (a.d < q.radius && a.large)).sort((a, b) => a.d - b.d).slice(0, 16) : [];
    el.innerHTML = `<h1>Skąd startujesz?</h1><p class="sub">${isPL() ? 'Od tego miejsca policzymy trasę autem, pociąg i najbliższe lotniska.' : 'Porównamy wszystkie lotniska w zasięgu, razem z dojazdem i parkingiem.'}</p>
    <div class="field"><button class="btn line" id="gps">Użyj mojej lokalizacji</button></div>
    <div class="field"><label for="city">albo wpisz miasto</label><input id="city" type="search" autocomplete="off" placeholder="np. Lublin" value="${esc(q.origin?.label || '')}"><div class="list" id="hits"></div></div>
    ${q.origin && !isPL() ? `<div class="field"><span class="lab">Zasięg lotnisk</span><div class="seg" id="rad">${[[300, '300 km'], [450, '450 km'], [700, '700 km']].map(([v, l]) => `<button data-v="${v}" aria-pressed="${q.radius === v}">${l}</button>`).join('')}</div>
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

const STYLES_PL = [['beach', 'Morze'], ['ski', 'Góry i narty'], ['lake', 'Jeziora'], ['spa', 'Uzdrowisko i spa'], ['city', 'Miasto'], ['nature', 'Przyroda'], ['romance', 'We dwoje'], ['family', 'Z rodziną']];
function stepWhere(el) {
  const t = S.q.dest;
  const countries = [...new Map(ZD().map((d) => [d.cc, d])).keys()];
  const CN = { IT: 'Włochy', ES: 'Hiszpania', PT: 'Portugalia', FR: 'Francja', GB: 'Wielka Brytania', IE: 'Irlandia', IS: 'Islandia', NL: 'Holandia', BE: 'Belgia', DE: 'Niemcy', CH: 'Szwajcaria', AT: 'Austria', CZ: 'Czechy', HU: 'Węgry', SK: 'Słowacja', SI: 'Słowenia', HR: 'Chorwacja', ME: 'Czarnogóra', BA: 'Bośnia', RS: 'Serbia', AL: 'Albania', MK: 'Macedonia', GR: 'Grecja', CY: 'Cypr', MT: 'Malta', TR: 'Turcja', BG: 'Bułgaria', RO: 'Rumunia', MD: 'Mołdawia', NO: 'Norwegia', SE: 'Szwecja', DK: 'Dania', FI: 'Finlandia', EE: 'Estonia', LV: 'Łotwa', LT: 'Litwa', PL: 'Polska', GE: 'Gruzja', MA: 'Maroko', EG: 'Egipt', TN: 'Tunezja', AE: 'Emiraty Arabskie', JO: 'Jordania', CV: 'Zielony Przylądek' };
  const TP = { beach: 'split', city: 'rzym', ski: 'zermatt', nature: 'madera-funchal', party: 'ibiza', family: 'palma-de-mallorca', food: 'bolonia', romance: 'wenecja' };
  const tiles = () => `<div class="tiles">${(isPL() ? STYLES_PL : STYLES).map(([k, l]) => { return `<button class="tile" data-style="${k}" aria-pressed="${t.style === k}">${IMG(`art/style/${k}.jpg`, '')}<b>${l}</b></button>`; }).join('')}</div>`;
  const draw = () => {
    let body = '';
    if (t.mode === 'city') body = `<div class="field"><label for="p">Miejsce</label><input id="p" type="search" autocomplete="off" placeholder="${isPL() ? 'np. Sopot' : 'np. Barcelona'}"><div class="list" id="hits"></div><div class="chips" id="sel" style="margin-top:10px">${t.ids.map((i) => `<button class="chip" aria-pressed="true" data-rm="${i}">${esc(S.dests.find((d) => d.id === i)?.name)} ×</button>`).join('')}</div><p class="hint">Możesz dodać kilka miejsc i porównać.</p></div>`;
    if (t.mode === 'country') body = `<div class="field"><span class="lab">Kraj</span><div class="chips">${countries.map((c) => `<button class="chip" data-c="${c}" aria-pressed="${t.countries.includes(c)}">${CN[c] || c}</button>`).join('')}</div></div><div class="field"><span class="lab">Po co jedziesz? (opcjonalnie)</span>${tiles()}</div>`;
    if (t.mode === 'style') body = `<div class="field">${tiles()}</div>`;
    if (t.mode === 'anywhere') body = isPL() ? `<div class="field"><p>Sprawdzimy najciekawsze miejsca w Polsce w Twoim zasięgu i porównamy koszt dojazdu i noclegu.</p></div><div class="field"><span class="lab">Klimat wyjazdu (opcjonalnie)</span>${tiles()}</div>` : `<div class="field"><p>Sprawdzimy kilkanaście najlepszych miejsc na ten termin i pokażemy, gdzie polecisz najtaniej.</p></div><div class="field"><span class="lab">Klimat wyjazdu (opcjonalnie)</span>${tiles()}</div>`;
    const hrs = isPL() && t.mode !== 'city' ? `<div class="field"><span class="lab">Ile najwyżej jazdy autem w jedną stronę?</span><div class="seg" id="mh">${[[2, '2 h'], [3, '3 h'], [4, '4 h'], [6, '6 h'], [0, 'Bez limitu']].map(([v, l]) => `<button data-h="${v}" aria-pressed="${(S.q.maxHours || 0) === v}">${l}</button>`).join('')}</div></div>` : '';
    el.innerHTML = `<h1>Dokąd?</h1><p class="sub">${isPL() ? 'Znasz cel albo tylko wiesz, czego szukasz.' : 'Znasz cel albo tylko wiesz, na co masz ochotę.'}</p>
      <div class="field seg" id="md">${(isPL() ? [['city', 'Miejsce'], ['style', 'Styl'], ['anywhere', 'Cała Polska']] : [['city', 'Miejsce'], ['country', 'Kraj'], ['style', 'Styl'], ['anywhere', 'Gdziekolwiek']]).map(([k, l]) => `<button data-m="${k}" aria-pressed="${t.mode === k}">${l}</button>`).join('')}</div>${body}${hrs}
      ${navBtns('Dalej', valid())}`;
    $$('#md button').forEach((b) => { b.onclick = () => { t.mode = b.dataset.m; if (t.mode === 'city') t.style = t.style || null; draw(); }; });
    $$('[data-style]').forEach((b) => { b.onclick = () => { t.style = t.style === b.dataset.style && t.mode !== 'style' ? null : b.dataset.style; backdropForStep(); draw(); }; });
    $$('[data-c]').forEach((b) => { b.onclick = () => { const c = b.dataset.c; t.countries = t.countries.includes(c) ? t.countries.filter((x) => x !== c) : [...t.countries, c].slice(-3); draw(); }; });
    $$('[data-rm]').forEach((b) => { b.onclick = () => { t.ids = t.ids.filter((i) => i !== b.dataset.rm); draw(); }; });
    $$('#mh button').forEach((b) => { b.onclick = () => { S.q.maxHours = +b.dataset.h; draw(); }; });
    const p = $('#p');
    if (p) p.oninput = () => {
      const v = p.value.trim().toLowerCase();
      const hits = v.length < 2 ? [] : ZD().filter((d) => normQ(d.name).includes(normQ(v)) || normQ(d.en).includes(normQ(v))).slice(0, 6);
      $('#hits').innerHTML = hits.map((d) => `<button class="row" data-add="${d.id}"><span>${esc(d.name)}<small>${esc(isPL() ? (d.desc || '') : d.air.join(', '))}</small></span></button>`).join('') || (v.length > 1 ? '<p class="hint">Tego miejsca nie ma jeszcze w bazie. Wybierz najbliższe większe miasto.</p>' : '');
      $$('[data-add]').forEach((b) => { b.onclick = () => { if (!t.ids.includes(b.dataset.add)) t.ids = [...t.ids, b.dataset.add].slice(-6); draw(); }; });
    };
    $('#next').onclick = next;
  };
  if (isPL() && t.mode === 'country') t.mode = 'style';
  const valid = () => (t.mode === 'city' ? t.ids.length > 0 : t.mode === 'country' ? t.countries.length > 0 : t.mode === 'style' ? !!t.style : true);
  draw();
}

function stepWhen(el) {
  const w = S.q.when;
  const list = [];
  for (let i = 0; i < 12; i++) { const d = new Date(now.getFullYear(), now.getMonth() + i, 1); list.push([d.getFullYear(), d.getMonth() + 1]); }
  w.pyear ||= now.getMonth() >= 9 ? now.getFullYear() + 1 : now.getFullYear();
  w.days ||= [];
  if (w.mode === 'range' && !w.preset) w.preset = w.from && w.to ? 'own' : '';
  const pad = (n) => String(n).padStart(2, '0');
  const lastDay = (y, m) => new Date(y, m, 0).getDate();
  const live = (k, y) => new Date(y, PRESETS[k].b, 0) >= now;
  const pick = (k) => { const p = PRESETS[k]; w.preset = k; w.spill = true; w.from = `${w.pyear}-${pad(p.a)}-01`; w.to = `${w.pyear}-${pad(p.b)}-${pad(lastDay(w.pyear, p.b))}`; };
  const draw = () => {
    const today = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
    const own = w.mode === 'dates' || w.preset === 'own';
    el.innerHTML = `<h1>Kiedy?</h1><p class="sub">Im szerszy termin, tym większa szansa na okazję.</p>
    <div class="field seg" id="md">${[['month', 'Miesiąc'], ['range', 'Zakres'], ['dates', 'Dokładnie']].map(([k, l]) => `<button data-m="${k}" aria-pressed="${w.mode === k}">${l}</button>`).join('')}</div>
    ${w.mode === 'month' ? `<div class="field chips">${list.map(([y, m]) => `<button class="chip" data-y="${y}" data-m2="${m}" aria-pressed="${w.year === y && w.month === m}">${MONTHS[m - 1]}${y !== now.getFullYear() ? ' ' + y : ''}</button>`).join('')}</div><p class="sub" style="font-size:14px">Wylot i powrót w tym miesiącu.</p>` : ''}
    ${w.mode === 'range' ? `<div class="field seg" id="yr">${[now.getFullYear(), now.getFullYear() + 1].map((y) => `<button data-yr="${y}" aria-pressed="${w.pyear === y}">${y}</button>`).join('')}</div>
    <div class="field chips">${Object.keys(PRESETS).filter((k) => live(k, w.pyear)).map((k) => `<button class="chip" data-p="${k}" aria-pressed="${w.preset === k}">${PRESETS[k].l}</button>`).join('')}<button class="chip" data-p="own" aria-pressed="${w.preset === 'own'}">Własne daty</button></div>
    ${w.preset && w.preset !== 'own' ? `<p class="sub" style="font-size:14px">Wylot w tym okresie, powrót może wypaść tuż po nim. Pokażę ceny w każdym miesiącu. Długi okres to kilka minut szukania, możesz w tym czasie wyjść z aplikacji.</p>` : ''}` : ''}
    ${own ? `<div class="field grid2"><div><label class="lab" for="f">${w.mode === 'dates' ? 'Wylot' : 'Najwcześniej'}</label><input id="f" type="date" min="${today}" value="${esc(w.from)}"></div><div><label class="lab" for="t">${w.mode === 'dates' ? 'Powrót' : 'Najpóźniej'}</label><input id="t" type="date" min="${today}" value="${esc(w.to)}"></div></div>` : ''}
    ${w.mode !== 'dates' ? `<div class="field"><span class="lab">Ile nocy? Możesz wybrać do trzech</span><div class="chips">${[2, 3, 4, 5, 7, 10, 14].map((n) => `<button class="chip" data-n="${n}" aria-pressed="${w.nights.includes(n)}">${n}</button>`).join('')}</div></div>
    <div class="field"><span class="lab">Wylot tylko w te dni (nieobowiązkowe)</span><div class="chips">${DAYS.map((d, i) => `<button class="chip" data-wd="${i}" aria-pressed="${w.days.includes(i)}">${d}</button>`).join('')}</div></div>` : ''}
    ${navBtns('Dalej', ok())}`;
    $$('#md button').forEach((b) => { b.onclick = () => { w.mode = b.dataset.m; if (w.mode === 'range' && !w.preset) w.preset = ''; draw(); }; });
    $$('[data-m2]').forEach((b) => { b.onclick = () => { w.year = +b.dataset.y; w.month = +b.dataset.m2; draw(); }; });
    $$('[data-yr]').forEach((b) => { b.onclick = () => { w.pyear = +b.dataset.yr; if (w.preset && w.preset !== 'own') { if (live(w.preset, w.pyear)) pick(w.preset); else w.preset = ''; } draw(); }; });
    $$('[data-p]').forEach((b) => { b.onclick = () => { if (b.dataset.p === 'own') { w.preset = 'own'; w.spill = false; } else pick(b.dataset.p); draw(); }; });
    $$('[data-wd]').forEach((b) => { b.onclick = () => { const i = +b.dataset.wd; w.days = w.days.includes(i) ? w.days.filter((x) => x !== i) : [...w.days, i]; draw(); }; });
    $$('[data-n]').forEach((b) => { b.onclick = () => { const n = +b.dataset.n; w.nights = w.nights.includes(n) ? (w.nights.length > 1 ? w.nights.filter((x) => x !== n) : w.nights) : [...w.nights, n].slice(-3).sort((a, c) => a - c); draw(); }; });
    ['f', 't'].forEach((i) => { const x = $('#' + i); if (x) x.onchange = () => { w[i === 'f' ? 'from' : 'to'] = x.value; draw(); }; });
    $('#next').onclick = next;
  };
  const ok = () => w.mode === 'month' || (w.mode === 'range' ? !!w.preset && !!(w.from && w.to && w.to > w.from) : !!(w.from && w.to && w.to > w.from));
  if (!list.some(([y, m]) => y === w.year && m === w.month)) { [w.year, w.month] = list[1]; }
  draw();
}

function stepWho(el) {
  const p = S.q.pax; const b = S.q.bags;
  const draw = () => {
    const stp = (k, l, min, max, o) => `<div class="stepper"><span>${l}</span><div><button data-k="${k}" data-d="-1" aria-label="Mniej" ${o[k] <= min ? 'disabled' : ''}>−</button><output>${o[k]}</output><button data-k="${k}" data-d="1" aria-label="Więcej" ${o[k] >= max ? 'disabled' : ''}>+</button></div></div>`;
    if (isPL()) {
      el.innerHTML = `<h1>Kto jedzie?</h1><p class="sub">Nocleg, bilety i koszty liczymy dla całej grupy.</p><div class="field">${stp('adults', 'Dorośli', 1, 8, p)}${stp('children', 'Dzieci (2–11 lat)', 0, 6, p)}</div>${navBtns()}`;
      $$('[data-k]').forEach((x) => { x.onclick = () => { p[x.dataset.k] += +x.dataset.d; draw(); }; });
      $('#next').onclick = next; return;
    }
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
  if (isPL()) {
    el.innerHTML = `<h1>Twoje auto</h1><p class="sub">Koszt jazdy liczymy z Twojego spalania i ceny paliwa. Pociąg i samolot porównamy obok.</p>
    <div class="field grid2"><div><label class="lab" for="l">Spalanie l/100 km</label><input id="l" type="number" inputmode="decimal" step="0.1" min="2" max="30" value="${t.consumption}"></div><div><label class="lab" for="fp">Paliwo zł/l</label><input id="fp" type="number" inputmode="decimal" step="0.01" min="1" max="15" value="${t.fuelPrice}"></div></div>
    <p class="hint">Cenę paliwa wpisz taką, jaką płacisz teraz na stacji. Opłaty za płatne odcinki A1, A2 i A4 doliczamy sami.</p>${navBtns()}`;
    ['l', 'fp'].forEach((id) => { const x = $('#' + id); const [k, mn, mx] = id === 'l' ? ['consumption', 2, 30] : ['fuelPrice', 1, 15]; x.onchange = () => { const v = parseFloat(x.value.replace(',', '.')); if (Number.isFinite(v) && v >= mn && v <= mx) t[k] = v; else { toast('Wpisz wartość od ' + mn + ' do ' + mx); x.value = t[k]; } }; });
    $('#next').onclick = next;
    return;
  }
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
  const p = (S.q.plan ||= { pace: 'normal', interests: [] }); p.food ||= [];
  const FOOD = [['italian', 'Włoska'], ['pizza', 'Pizza'], ['seafood', 'Ryby i owoce morza'], ['regional', 'Regionalna'], ['tapas', 'Tapas'], ['vegetarian', 'Wegetariańska'], ['asian', 'Azjatycka'], ['burger', 'Burgery']];
  const INT = [['museum', 'Muzea'], ['church', 'Świątynie'], ['castle', 'Zamki'], ['palace', 'Pałace'], ['ruins', 'Starożytność'], ['park', 'Parki'], ['beach', 'Plaże'], ['nature', 'Przyroda'], ['sight', 'Zabytki']];
  const draw = () => {
    el.innerHTML = `<h1>Jak zwiedzasz?</h1><p class="sub">Według tego ułożymy dni na miejscu.</p>
    <div class="field"><span class="lab">Tempo</span><div class="seg" id="pc">${[['slow', 'Spokojnie'], ['normal', 'Normalnie'], ['fast', 'Intensywnie']].map(([k, l]) => `<button data-k="${k}" aria-pressed="${p.pace === k}">${l}</button>`).join('')}</div></div>
    <div class="field"><span class="lab">Co lubisz najbardziej</span><div class="chips"><button class="chip" id="nop" aria-pressed="${!p.interests.length && !p.food.length}">Bez preferencji</button>${INT.map(([k, l]) => `<button class="chip" data-i="${k}" aria-pressed="${p.interests.includes(k)}">${l}</button>`).join('')}</div></div>
    <div class="field"><span class="lab">Co lubisz jeść (nieobowiązkowe)</span><div class="chips">${FOOD.map(([k, l]) => `<button class="chip" data-fd="${k}" aria-pressed="${p.food.includes(k)}">${l}</button>`).join('')}</div></div>
    ${navBtns('Szukaj najlepszych opcji')}`;
    $$('#pc button').forEach((b) => { b.onclick = () => { p.pace = b.dataset.k; draw(); }; });
    $$('[data-i]').forEach((b) => { b.onclick = () => { const k = b.dataset.i; p.interests = p.interests.includes(k) ? p.interests.filter((x) => x !== k) : [...p.interests, k]; draw(); }; });
    $('#nop').onclick = () => { p.interests = []; p.food = []; draw(); };
    $$('[data-fd]').forEach((b) => { b.onclick = () => { const k = b.dataset.fd; p.food = p.food.includes(k) ? p.food.filter((x) => x !== k) : [...p.food, k]; draw(); }; });
    $('#next').onclick = () => { save('prefs', S.q); if (S.modal) closeModal(); else viewSearch(); };
  };
  draw();
}

/* ---------- Szukanie: tablica odlotów ---------- */
async function viewSearch(resumeId) {
  if (typeof resumeId !== 'string') resumeId = null;
  setBackdrop({ photo: 'art/e/ladowanie.jpg', dim: true });
  const W = window.innerWidth < 380 ? 14 : 16;
  app.innerHTML = `<section class="board-wrap"><h1 class="board-title">Szukamy</h1><div class="board" id="bd"></div>
    <div class="bar"><i id="pr"></i></div><p class="board-label" id="lb" role="status">Przygotowuję trasy</p><p class="board-label" style="font-weight:400;font-size:14px">Zwykle 1–5 minut, bo sprawdzamy ceny na żywo. Możesz zamknąć aplikację, wyniki tu poczekają.</p>
    <div class="acts" style="justify-content:center;margin-top:18px"><button class="btn line lightb" id="cx">Przerwij</button><button class="btn line lightb" id="ed">Popraw wyszukiwanie</button></div></section>`;
  let off = false; let ticker = 0;
  const quit = (fn) => { off = true; stop(); save('job', null); fn(); };
  $('#cx').onclick = () => quit(viewHome);
  $('#ed').onclick = () => quit(() => { S.step = 0; viewWizard(); });
  const rows = [flapRow(W), flapRow(W), flapRow(W), flapRow(W)];
  rows.forEach((r) => $('#bd').append(r.el));
  const names = ZD().filter((d) => matches(d)).sort(() => Math.random() - 0.5).map((d) => d.name.toUpperCase());
  if (names.length < 5) names.push(...(isPL() ? ['TRASA AUTEM', 'POCIĄGI', 'LOTY KRAJOWE', 'NOCLEGI'] : ['NAJTAŃSZE DATY', 'WSZYSTKIE LOTNISKA', 'NOCLEGI', 'DOJAZD']));
  const t = () => rows.forEach((r, i) => r.set((names[(i + Math.floor(Date.now() / 3200)) % Math.max(1, names.length)] || 'EUROPA').replace(/\(.*/, '').trim()));
  t(); ticker = setInterval(t, 3200);
  function stop() { clearInterval(ticker); }
  try {
    const pl = isPL(); S.q.dest.zone = S.zone;
    const id = resumeId || (await api(pl ? '/api/pl/search' : '/api/search', { ...S.q, maxHours: pl ? S.q.maxHours || 0 : undefined })).id;
    if (off) return;
    save('job', { id, q: S.q, t: Date.now(), zone: S.zone });
    for (;;) {
      await new Promise((r) => setTimeout(r, 1300));
      if (off) return;
      // Telefon gubi zasięg albo serwer się restartuje: kilka cichych prób, zanim pokażemy błąd
      let j = null;
      for (let t = 0; !j; t++) {
        try { j = await api((isPL() ? '/api/pl/job?id=' : '/api/job?id=') + id); }
        catch (er) { if (t >= 7 || !/połączenia/.test(er.message)) throw er; if ($('#lb')) $('#lb').textContent = 'Słabe połączenie, ponawiam…'; await new Promise((r) => setTimeout(r, 4000)); if (off) return; }
      }
      if (off) return;
      const bar = $('#pr'); const lb = $('#lb');
      if (!bar) { stop(); return; }
      bar.style.width = j.progress * 100 + '%'; lb.textContent = j.label;
      if (j.state === 'done') { stop(); S.result = j.result; S.resultAt = Date.now(); save('job', null); save('last', { result: j.result, q: S.q, t: Date.now(), zone: S.zone }); return viewResults(); }
      if (j.state === 'error') { save('job', null); throw new Error(j.error); }
    }
  } catch (e) {
    stop();
    if (off) return;
    app.innerHTML = `<section class="board-wrap"><div class="card"><div class="in"><h2 class="big">Nie mamy pewnych wyników</h2><p style="margin-top:8px">${esc(e.message)}</p><div class="acts"><button class="btn" id="r">Spróbuj ponownie</button><button class="btn line" id="b">Zmień wyszukiwanie</button></div></div></div></section>`;
    $('#r').onclick = () => viewSearch(); $('#b').onclick = () => { S.step = 0; viewWizard(); };
  }
}
function matches(d) {
  const t = S.q.dest;
  if (!t) return false;
  if (t.mode === 'city') return t.ids.includes(d.id);
  if (t.mode === 'country') return t.countries.includes(d.cc);
  return !t.style || d.tags.includes(t.style);
}

/* ---------- Wyniki ---------- */
function posterOf(o, h = '') {
  const d = o.dest; const p = photoOf(d.id, 900);
  return `<div class="poster">${scene(sceneOf(d))}${p ? IMG(p.src, p.n, 'ph') : ''}<span class="shade"></span>${h}<h3>${esc(d.name.replace(/\s*\(.*/, ''))}</h3></div>`;
}
function viewResults() {
  const R = S.result;
  if (R.kind === 'pl') return viewPLResults();
  const opts = (R.options || []).filter((o) => o.insight !== undefined || o.compare || true);
  const best = new Map();
  opts.forEach((o) => { if (!best.has(o.dest.id)) best.set(o.dest.id, o); });
  const top = R.months && best.size === 1 ? opts.slice(0, 5) : [...best.values()];
  if (top[0]) setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const ago = R.at ? new Date(R.at * 1000).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' }) : '';
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${top.length ? 'Najlepsze opcje' : 'Brak wyników'}</h2></div>
  <section class="page">
  ${(R.notes || []).map((n) => `<div class="note"><b>${esc(n.text)}</b>${n.alternatives?.length ? `<p class="mute">Ciepło jest wtedy tutaj: ${n.alternatives.map((a) => `${esc(a.name)}${a.fit?.tmax != null ? ` (${Math.round(a.fit.tmax)}°C)` : ''}`).join(', ')}.</p><div class="chips" style="margin-top:8px">${n.alternatives.map((a) => `<button class="chip" data-alt="${a.id}">${esc(a.name)}</button>`).join('')}</div>` : ''}</div>`).join('')}
  ${R.partial ? '<div class="note"><b>Część zapytań nie przeszła.</b><p class="mute">Mogą istnieć tańsze opcje, których nie widzimy. Pokazujemy tylko to, co udało się sprawdzić.</p></div>' : ''}
  ${!top.length ? `<div class="note info"><b>Na ten termin nie ma lotów z Twoich lotnisk.</b><p class="mute">Spróbuj szerszego terminu albo większego zasięgu lotnisk.</p></div>` : ''}
  ${monthsHtml(R)}
  ${top.map((o, i) => `<article class="card"><button data-o="${o.id}" style="display:block;width:100%;text-align:left">${posterOf(o, `<span class="pr">${zl(o.hotelEst ? o.perPersonAll : o.perPerson)}<small style="font:600 12px var(--body)"> /os. ${o.hotelEst ? 'z noclegiem' : 'bez noclegu'}</small></span>`)}
    <div class="in"><p><b>${dateL(o.dep)} – ${dateL(o.ret)}</b>, ${o.nights} nocy, z ${esc(o.fromGen)}</p>
    <p class="mute">${o.climate?.score != null ? esc(o.climate.why) + '. ' : ''}</p><p>${o.hotelEst ? `<b>Razem około ${zl(o.totalWithHotel)}</b> dla ${o.pax.adults + o.pax.children} ${osobD(o.pax.adults + o.pax.children)}: loty i dojazd ${zl(o.total)}, nocleg około ${zl(o.hotelEst.total)}.` : `<b>Loty i dojazd ${zl(o.total)}.</b> Tej ceny brakuje noclegu: nie udało się teraz pobrać cen hoteli.`}</p>
    ${o.insight ? `<p class="warn" style="color:var(--deep)">${esc(o.insight)}</p>` : ''}</div></button></article>`).join('')}
  <p class="foot">Ceny sprawdzone dziś o ${esc(ago)}. Linie zmieniają je często, ostateczną zobaczysz przy zakupie.</p></section>`;
  $('#b').onclick = () => { S.step = STEPS.length - 1; viewWizard(); };
  $$('[data-o]').forEach((b) => { b.onclick = () => { S.option = opts.find((o) => o.id === b.dataset.o); viewOption(); }; });
  $$('[data-ym]').forEach((b) => { b.onclick = () => openMonth(b.dataset.ym); });
  $$('[data-alt]').forEach((b) => { b.onclick = () => { S.q.dest = { mode: 'city', ids: [b.dataset.alt], countries: [], style: 'beach' }; viewSearch(); }; });
  app.scrollTop = 0;
}
/* ---------- Propozycja wyjazdu: kilka opcji do wyboru wysłanych jednym linkiem ---------- */
const PROPMAX = 8;
const propDraft = () => load('prop', { title: '', msg: '', hide: false, items: [] });
// Mniej danych w linku: bez kalendarza cen i zbędnych pól
const slimOpt = (o) => { const { calendar, alts, cal, ...r } = o; return JSON.parse(JSON.stringify(r)); };
const slimPlan = (p) => { const x = JSON.parse(JSON.stringify(p)); delete x.live; delete x.s; (x.days || []).forEach((d) => (d.stops || []).forEach((st) => { delete st.infoEn; })); return x; };
async function propAdd(o, plan) {
  const D = propDraft();
  if (D.items.length >= PROPMAX) return toast(`Propozycja może mieć najwyżej ${PROPMAX} opcji.`);
  const key = `${o.dest.id}|${o.dep}|${o.ret}|${plan ? 'p' : o.plMode || o.from || ''}`;
  if (D.items.some((i) => i.key === key)) return toast('Ta opcja jest już w propozycji.');
  let guide = null;
  if (!plan) {
    try {
      const g = await fetch(`data/guide/${o.dest.id}.json`).then((r) => r.json());
      guide = (g.a || []).filter((a) => a.d).slice(0, 6).map((a) => ({ ...a, d: a.d.replace(/\s*\([^()]*?\)/g, '').replace(/\s+([,.;])/g, '$1') })).map((a) => ({ n: a.n, d: a.d.length > 170 ? a.d.slice(0, a.d.lastIndexOf(' ', 165)) + '…' : a.d, img: a.img }));
    } catch { /* bez przewodnika */ }
  }
  D.items.push({ id: Math.random().toString(36).slice(2, 9), key, option: slimOpt({ ...o, plMode: o.plMode }), plan: plan ? slimPlan(plan) : null, guide, at: new Date().toISOString().slice(0, 10) });
  save('prop', D);
  toast(`Dodano do propozycji (${D.items.length}). Otworzysz ją w zakładce Podróże.`);
}
const propBtn = (id = 'padd') => `<button class="btn line small" id="${id}">${I.heart} Dodaj do propozycji</button>`;
function propWhen(o) { return `${dateL(o.dep)} – ${dateL(o.ret)}, ${nightsL(o.nights || Math.round((new Date(o.ret) - new Date(o.dep)) / 864e5))}`; }
function propHow(o) {
  if (o.flight?.out) { const L = o.flight.out.legs; const B = o.flight.back.legs; return `${I.plane} Lot ${esc(o.from)} → ${esc(o.to)}: ${dateL(L[0].dep)} ${timeL(L[0].dep)}, powrót ${dateL(B[0].dep)} ${timeL(B[0].dep)}${L.length > 1 ? `, ${L.length - 1} przesiadka` : ', bez przesiadek'}`; }
  if (o.plMode === 'plane' && o.plane) return `${I.plane} Lot ${esc(o.plane.from)} → ${esc(o.plane.to)}, ${dateL(o.plane.dep)} ${timeL(o.plane.dep)}`;
  if (o.plMode === 'train' && o.train) return `${I.train} Pociągiem, około ${dur(o.train.min)}`;
  if (o.car) return `${I.car} Autem, ${o.car.km} km, około ${dur(o.car.min)}`;
  return o.modeName ? esc(o.modeName) : '';
}
function propPrice(it) { const o = it.option; const p = it.plan; const v = p?.total ?? o.total; return v ? zl(v) : ''; }
function propCard(it, votes, role) {
  const o = it.option; const p = it.plan; const v = votes?.[it.id] || {};
  const m = p?.climate || o.climate?.month;
  const days = p?.days?.length ? `<details class="pdays"><summary>Plan dzień po dniu (${p.days.length})</summary>${p.days.map((d, i) => `<div class="pday"><em>Dzień ${i + 1} – ${shortD(d.date)}</em><b>${esc(dayTitle(d, i, p))}</b><small>${esc(daySub(d, p))}</small></div>`).join('')}</details>` : '';
  const sights = !p && it.guide?.length ? `<details class="pdays"><summary>Co warto zobaczyć</summary>${it.guide.map((a) => `<div class="pday"><b>${esc(a.n)}</b><small>${esc(a.d)}</small></div>`).join('')}</details>` : '';
  const price = propPrice(it);
  return `<article class="card propc" data-it="${it.id}">${posterOf(o, price ? `<span class="pr">${price}</span>` : '')}
   <div class="in"><p class="mute">${propWhen(o)}${o.pax ? `, ${o.pax.adults + o.pax.children} ${osob(o.pax.adults + o.pax.children)}` : ''}</p>
   <p class="pline">${propHow(o)}</p>
   <p class="pline">${I.bed} ${p?.hotel?.name && p.hotel.name !== 'Nocleg do wyboru' ? esc(p.hotel.name) : 'Nocleg do wybrania razem'}${p?.hotel?.rating ? `, ${String(p.hotel.rating).replace('.', ',')}/5` : ''}</p>
   ${m?.tmax != null ? `<p class="pline">${I.star} Średnio ${Math.round(m.tmin)}–${Math.round(m.tmax)}°C${m.sea != null && m.tmax >= 18 && (o.dest.tags || []).includes('beach') ? `, morze ${Math.round(m.sea)}°C` : ''}</p>` : ''}
   ${price ? `<p class="mute small">Cena ${p ? 'całego wyjazdu (szacunek)' : 'dojazdu i noclegu'} z ${dateL(it.at || '')}. Ceny mogą się zmienić.</p>` : ''}
   ${days}${sights}
   ${role === 'view' ? `<div class="pvote"><button class="pheart ${v.heart ? 'on' : ''}" data-h="${it.id}" aria-pressed="${!!v.heart}">${I.heart}<span>${v.heart ? 'Podoba mi się' : 'Daj serce'}</span></button>
     <textarea data-c="${it.id}" maxlength="600" rows="2" placeholder="Komentarz, np. tak, ale bez muzeów">${esc(v.comment || '')}</textarea><button class="btn line small" data-cs="${it.id}">Wyślij komentarz</button></div>`
    : (v.heart || v.comment ? `<div class="pvote own">${v.heart ? `<p><b>${I.heart} Ma serce</b></p>` : ''}${v.comment ? `<p>„${esc(v.comment)}”</p>` : ''}</div>` : '')}
   ${role === 'edit' ? `<div class="acts"><button class="btn small" data-mk="${it.id}">Zrób z tego podróż</button></div>` : ''}
   </div></article>`;
}
function viewPropDraft() {
  const D = propDraft();
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Propozycja wyjazdu</h2></div>
  <section class="page">
   <div class="wcard"><h3>Komu i po co</h3>
    <label class="lab" for="pt">Tytuł</label><input id="pt" maxlength="80" value="${esc(D.title)}" placeholder="np. Wyjazd na święta">
    <label class="lab" for="pm" style="margin-top:10px;display:block">Wiadomość od Ciebie</label><textarea id="pm" maxlength="1200" rows="3" placeholder="Napisz kilka słów. Zobaczy je na górze strony.">${esc(D.msg)}</textarea>
    <label class="tgl"><input type="checkbox" id="ph" ${D.hide ? 'checked' : ''}><span>Ukryj ceny</span></label>
   </div>
   <div class="wcard"><h3>Opcje (${D.items.length} z ${PROPMAX})</h3>
    ${D.items.length ? D.items.map((it, i) => `<div class="prow"><span><b>${esc(it.option.dest.name)}</b><small>${propWhen(it.option)}${it.plan ? ', gotowy plan' : ''}${propPrice(it) ? `, ${propPrice(it)}` : ''}</small></span>${i ? `<button class="round sm" data-up="${i}" aria-label="Wyżej">↑</button>` : ''}<button class="round sm" data-rm="${i}" aria-label="Usuń">✕</button></div>`).join('')
    : '<p class="mute">Na razie pusto. W wynikach wyszukiwania albo w gotowym planie dotknij „Dodaj do propozycji”.</p>'}
   </div>
   <div class="acts"><button class="btn" id="pgo" ${D.items.length ? '' : 'disabled'}>Utwórz link do wysłania</button></div>
   ${D.items.length ? '<p class="hint">Dostanie ładną stronę do obejrzenia w telefonie, bez instalowania aplikacji. Przy każdej opcji może dać serce i komentarz, a Ty dostaniesz powiadomienie.</p>' : ''}
  </section>`;
  const keep = () => { D.title = $('#pt').value.trim(); D.msg = $('#pm').value.trim(); D.hide = $('#ph').checked; save('prop', D); };
  ['pt', 'pm', 'ph'].forEach((id) => { $('#' + id).onchange = keep; });
  $('#b').onclick = () => { keep(); viewTrips(); };
  $$('[data-rm]').forEach((b) => { b.onclick = () => { keep(); D.items.splice(+b.dataset.rm, 1); save('prop', D); viewPropDraft(); }; });
  $$('[data-up]').forEach((b) => { b.onclick = () => { keep(); const i = +b.dataset.up; [D.items[i - 1], D.items[i]] = [D.items[i], D.items[i - 1]]; save('prop', D); viewPropDraft(); }; });
  $('#pgo').onclick = async () => {
    keep(); const btn = $('#pgo'); btn.disabled = true; btn.textContent = 'Tworzę link…';
    try {
      const r = await api('/api/prop/new', { data: { title: D.title || 'Propozycja wyjazdu', msg: D.msg, hide: D.hide, items: D.items }, device: LV.device() });
      const L = load('props', []); L.unshift({ edit: r.edit, view: r.view, title: D.title || 'Propozycja wyjazdu', n: D.items.length, t: Date.now() }); save('props', L);
      save('prop', { title: '', msg: '', hide: false, items: [] });
      viewPropSent(r.edit, true);
    } catch (e) { toast(e.message); btn.disabled = false; btn.textContent = 'Utwórz link do wysłania'; }
  };
  app.scrollTop = 0;
}
const propUrl = (k) => `${location.origin}${location.pathname}#p=${k}`;
async function viewPropSent(edit, fresh) {
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Propozycja</h2></div><section class="page"><p class="mute" style="color:#fff">Wczytuję…</p></section>`;
  $('#b').onclick = viewTrips;
  let r; try { r = await api('/api/prop?k=' + encodeURIComponent(edit)); } catch (e) { app.querySelector('.page').innerHTML = `<div class="note"><b>${esc(e.message)}</b></div>`; return; }
  const link = propUrl(r.view); const D = r.data; const hearts = Object.values(r.votes).filter((v) => v.heart).length;
  app.querySelector('.page').innerHTML = `
   <div class="wcard"><h3>${esc(D.title)}</h3>
    ${fresh ? '<p><b>Link gotowy.</b> Wyślij go SMS-em albo w komunikatorze.</p>' : `<p class="mute">${r.off ? 'Link jest wyłączony.' : hearts ? `Serca: ${hearts} z ${D.items.length}.` : 'Jeszcze bez odpowiedzi.'}</p>`}
    <input readonly value="${esc(link)}" id="pl" onclick="this.select()">
    <div class="acts"><button class="btn" id="psh">Wyślij link</button><button class="btn line" id="pprev">Zobacz, jak to wygląda</button><button class="btn line" id="ppdf">Zapisz jako PDF</button></div>
    ${D.hide ? '<p class="hint">Ceny są ukryte. Odbiorca ich nie zobaczy, także w kodzie strony.</p>' : ''}
   </div>
   ${D.items.map((it) => propCard(it, r.votes, 'edit')).join('')}
   <div class="acts"><button class="btn line small" id="poff">${r.off ? 'Włącz link z powrotem' : 'Wyłącz link'}</button><button class="btn line small" id="pdel">Usuń propozycję</button></div>`;
  $('#psh').onclick = async () => { try { if (navigator.share) await navigator.share({ title: D.title, text: D.msg ? D.msg.slice(0, 140) : 'Mam dla Ciebie propozycję wyjazdu', url: link }); else { await navigator.clipboard.writeText(link); toast('Skopiowano link.'); } } catch { /* anulowane */ } };
  $('#pprev').onclick = () => viewProp(r.view, true);
  $('#ppdf').onclick = () => viewProp(r.view, true, true);
  $('#poff').onclick = async () => { try { await api('/api/prop/off', { k: edit, off: !r.off }); viewPropSent(edit); } catch (e) { toast(e.message); } };
  $('#pdel').onclick = async () => { try { await api('/api/prop/del', { k: edit }); } catch { /* juz nie ma */ } save('props', load('props', []).filter((x) => x.edit !== edit)); viewTrips(); };
  $$('[data-mk]').forEach((b) => { b.onclick = () => {
    const it = D.items.find((x) => x.id === b.dataset.mk); if (!it) return;
    if (it.plan) { const pl = JSON.parse(JSON.stringify(it.plan)); pl.home = S.q.origin; S.plan = pl; LV.savePlan(pl); viewPlan(); return; }
    S.option = it.option; S.result = { options: [it.option] };
    if (it.option.car && !it.option.flight) { setZone('pl'); viewPLOption(); } else viewOption();
  }; });
}
// Strona dla odbiorcy (i podgląd autora). Działa w przeglądarce, bez instalowania aplikacji.
async function viewProp(k, preview, print) {
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<section class="page prop"><p class="mute" style="color:#fff">Wczytuję propozycję…</p></section>`;
  let r; try { r = await api('/api/prop?k=' + encodeURIComponent(k)); } catch (e) { app.innerHTML = `<section class="page prop"><div class="note"><b>${esc(e.message)}</b></div></section>`; return; }
  const D = r.data; const role = preview ? 'preview' : r.role;
  const first = D.items[0]?.option?.dest;
  if (first) setBackdrop({ photo: photoOf(first.id, 1280)?.src || heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `${preview ? `<div class="topbar noprint"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Podgląd</h2></div>` : ''}
  <section class="page prop">
   <header class="prophd"><img src="icons/logo-96.png" alt="" width="40" height="40"><span>Propozycja wyjazdu</span></header>
   <h1 class="ptitle">${esc(D.title)}</h1>
   ${D.msg ? `<div class="pmsg">${esc(D.msg).replace(/\n/g, '<br>')}</div>` : ''}
   <p class="pintro">${D.items.length > 1 ? `${D.items.length} opcje do wyboru. ${role === 'view' ? 'Daj serce tej, która Ci się podoba, i napisz, co myślisz.' : ''}` : ''}</p>
   ${D.items.map((it) => propCard(it, r.votes, role)).join('')}
   <div class="acts noprint"><button class="btn line" id="pdf">Zapisz jako PDF</button></div>
   <p class="foot">Zrobione w Globtroterze. Ceny i rozkłady sprawdzone w dniu przygotowania propozycji.</p>
  </section>`;
  const b = $('#b'); if (b) b.onclick = () => viewPropSent(load('props', []).find((x) => x.view === k)?.edit || '');
  const doPrint = () => { $$('details').forEach((d) => { d.open = true; }); setTimeout(() => window.print(), 300); };
  $('#pdf').onclick = doPrint;
  if (role === 'view') {
    const send = async (item, body) => { try { const x = await api('/api/prop/vote', { k, item, ...body }); r.votes = x.votes; return true; } catch (e) { toast(e.message); return false; } };
    $$('[data-h]').forEach((h) => { h.onclick = async () => { const on = h.getAttribute('aria-pressed') !== 'true'; if (await send(h.dataset.h, { heart: on })) { h.setAttribute('aria-pressed', on); h.classList.toggle('on', on); h.querySelector('span').textContent = on ? 'Podoba mi się' : 'Daj serce'; } }; });
    $$('[data-cs]').forEach((c) => { c.onclick = async () => { const t = $(`[data-c="${c.dataset.cs}"]`).value.trim(); if (await send(c.dataset.cs, { comment: t })) toast('Wysłane. Dzięki!'); }; });
  }
  app.scrollTop = 0;
  if (print) doPrint();
}

/* ---------- Wyniki w Polsce ---------- */
const MODE_L = { car: 'Autem', train: 'Pociągiem', plane: 'Samolotem' };
function plLines(o, full) {
  const c = o.car; const t = o.train; const p = o.plane; const n = o.pax.adults + o.pax.children;
  const best = (m) => (o.best === m ? ' <span class="sure fact">najtaniej</span>' : '');
  const rows = [`<div class="kv"><span>${I.car} Autem${best('car')}<br><small>${c.km.toLocaleString('pl-PL')} km, około ${dur(c.min)} z postojami</small></span><b>${zl(c.total)}</b></div>`];
  if (full) rows.push(`<p class="hint">Paliwo tam i z powrotem ${zl(c.fuel)}${c.tolls ? `, autostrady ${zl(c.tolls)} (${c.tollItems.map((x) => esc(x.label)).join(', ')}, w obie strony)` : ', bez płatnych autostrad'}.${c.note ? ' ' + esc(c.note) : ''}</p>`);
  if (t) rows.push(`<div class="kv"><span>${I.train} Pociągiem${best('train')}<br><small>około ${dur(t.min)}, ${t.transfers ? `${t.transfers} ${t.transfers === 1 ? 'przesiadka' : 'przesiadki'}` : 'bez przesiadek'}${t.sample ? ', rozkład z podobnego dnia' : ''}</small></span><b>około ${zl(t.total)} <span class="sure est">szacunek</span></b></div>`);
  if (p) rows.push(`<div class="kv"><span>${I.plane} Samolotem ${esc(p.from)} → ${esc(p.to)}${best('plane')}<br><small>${dateL(p.dep)} ${timeL(p.dep)}, ${p.stops ? `${p.stops} ${p.stops === 1 ? 'przesiadka' : 'przesiadki'}` : 'bez przesiadek'}, od drzwi do drzwi około ${dur(p.min)}</small></span><b>${zl(p.total)}</b></div>`);
  if (full && p) rows.push(`<p class="hint">Bilety ${zl(p.tickets)} <span class="sure fact">sprawdzone</span> dla ${n} ${osob(n)}, do tego dojazd na lotnisko i parking ${zl(p.access.total)} oraz z lotniska do celu około ${zl(p.transfer.pln)} (${p.transfer.km} km).</p>`);
  return rows.join('');
}
function viewPLResults() {
  const R = S.result; const L = R.options || [];
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${L.length ? 'Najlepsze miejsca' : 'Brak wyników'}</h2></div>
  <section class="page">
  ${(R.notes || []).map((n) => `<div class="note"><b>${esc(n.text)}</b></div>`).join('')}
  ${L.map((o) => { const n = o.pax.adults + o.pax.children; return `<article class="card"><button data-o="${o.id}" style="display:block;width:100%;text-align:left">${posterOf(o, `<span class="pr">${zl(o.total)}<small style="font:600 12px var(--body)"> razem${o.hotelEst ? ' z noclegiem' : ''}</small></span>`)}
    <div class="in"><p><b>${dateL(o.dep)} – ${dateL(o.ret)}</b>, ${nightsL(o.nights)}, ${n} ${osob(n)}</p>
    ${plLines(o, false)}
    <p>${o.hotelEst ? `Nocleg około ${zl(o.hotelEst.total)} <span class="sure est">szacunek</span>` : '<span class="sure check">nocleg: nie pobrano cen</span>'}</p></div></button></article>`; }).join('')}
  <p class="foot">${esc(R.tollSrc || '')} Ceny paliwa i noclegów to szacunki, bilety lotnicze sprawdzone dziś.</p></section>`;
  $('#b').onclick = () => { S.step = STEPS.length - 1; viewWizard(); };
  $$('[data-o]').forEach((b) => { b.onclick = () => { S.option = L.find((o) => o.id === b.dataset.o); viewPLOption(); }; });
  app.scrollTop = 0;
}
function viewPLOption() {
  const o = S.option; const n = o.pax.adults + o.pax.children; const m = o.climate?.month;
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const pick = (k, sub) => `<button class="btn ${o.best === k ? '' : 'line'}" data-mode="${k}">${MODE_L[k]}${sub ? ` · ${sub}` : ''}</button>`;
  const p = o.plane; const t = o.train;
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${esc(o.dest.name)}</h2></div>
  <section class="page"><article class="card">${posterOf(o)}
   <div class="in"><p class="big">${zl(o.total)}</p><p class="mute">${dateL(o.dep)} – ${dateL(o.ret)}, ${nightsL(o.nights)}, ${n} ${osob(n)}. Najtańszy dojazd i nocleg, bez jedzenia na miejscu.</p>
   ${o.dest.desc ? `<p class="hint">${esc(o.dest.desc)}</p>` : ''}
   <h3 class="big" style="font-size:26px;margin-top:14px">Jak dojechać</h3>${plLines(o, true)}
   ${p ? `${passHtml(p.flight.out, 'Tam')}${passHtml(p.flight.back, 'Z powrotem')}` : ''}
   <p class="hint">${o.hotelEst ? `Nocleg: około ${zl(o.hotelEst.total)} za ${nightsL(o.nights)}, ${o.hotelEst.rooms} ${o.hotelEst.rooms > 1 ? 'pokoje' : 'pokój'}. Dokładne ceny hoteli zobaczysz w następnym kroku.` : 'Ceny noclegów sprawdzimy w następnym kroku.'}</p>
   ${m?.tmax != null ? `<p class="hint">Średnio w tym miesiącu: ${Math.round(m.tmin)}–${Math.round(m.tmax)}°C${m.rain != null ? `, opady ${Math.round(m.rain)} mm` : ''}.</p>` : ''}
   <h3 class="big" style="font-size:26px;margin-top:14px">Wybierz dojazd i nocleg</h3>
   <div class="acts">${pick('car', zl(o.car.total))}${t ? pick('train', 'około ' + zl(t.total)) : ''}${p ? pick('plane', zl(p.total)) : ''}</div>
   <div class="acts" style="margin-top:8px">${propBtn()}</div>
   <div class="linkset" style="margin-top:12px"><a class="btn line small" href="${url(o.car.map)}" target="_blank" rel="noopener">Trasa w Google Maps</a>${t ? t.links.map((l) => `<a class="btn line small" href="${url(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join('') : ''}${p ? `<a class="btn line small" href="${url(p.url)}" target="_blank" rel="noopener">Lot w Google Flights</a>` : ''}</div>
   ${!t ? '<p class="hint">Nie znaleźliśmy rozkładu pociągów dla tej trasy. Sprawdź w Koleo albo PKP Intercity.</p>' : ''}
   ${!p && o.car.min >= 240 ? '<p class="hint">Lotu krajowego na te daty nie znaleźliśmy.</p>' : ''}
   </div></article></section>`;
  $('#b').onclick = viewPLResults;
  $('#padd').onclick = () => propAdd({ ...o, plMode: o.best });
  $$('[data-mode]').forEach((b) => { b.onclick = () => { o.plMode = b.dataset.mode; viewHotels(); }; });
  app.scrollTop = 0;
}
function heat(v, lo, hi) {
  const t = hi > lo ? (v - lo) / (hi - lo) : 0;
  const c = [[11, 143, 158], [18, 58, 140], [244, 83, 58]];
  const m = t < 0.5 ? [c[0], c[1], t * 2] : [c[1], c[2], (t - 0.5) * 2];
  return `rgb(${m[0].map((x, i) => Math.round(x + (m[1][i] - x) * m[2])).join(',')})`;
}
function monthsHtml(R) {
  if (!R.months) return '';
  const ok = R.months.filter((m) => m.state === 'ok');
  if (!ok.length) return '';
  const lo = Math.min(...ok.map((m) => m.price)); const hi = Math.max(...ok.map((m) => m.price));
  return `<div class="note info months"><b>Ceny w każdym miesiącu</b><p class="mute">Najtańszy bilet w obie strony dla 1 osoby. Dotknij miesiąca, sprawdzę loty i nocleg.</p>
  ${R.months.map((m) => { const [y, mm] = m.ym.split('-'); const nm = `${MONTHS[+mm - 1]} ${y}`;
    if (m.state !== 'ok') return `<div class="mrow off"><span>${nm}</span><span>rozkład jeszcze niepełny</span></div>`;
    return `<button class="mrow${m.price === lo ? ' low' : ''}" data-ym="${m.ym}"><span class="m1">${nm}<small>${m.tmax != null ? `${Math.round(m.tmax)}°C${m.sea != null ? `, morze ${Math.round(m.sea)}°C` : ''}` : ''}${m.unfit ? ', za zimno na ten styl' : ''}</small></span><span class="mb"><i style="width:${hi > lo ? 25 + ((m.price - lo) / (hi - lo)) * 75 : 60}%"></i></span><b>${zl(m.price)}</b></button>`; }).join('')}</div>`;
}
async function openFare(x) {
  const R = S.result; const base = R.options.find((o) => o.dest.id === x.destId) || R.options[0];
  if (!base) return;
  const key = `${x.from}-${x.to}-${x.nights}`;
  toast('Sprawdzam loty na ' + dateL(x.dep));
  try {
    const opt = { ...base, from: x.from, to: x.to, drive: x.drive, dest: x.destId ? { ...base.dest, id: x.destId } : base.dest, calendar: R.grids?.[key] || base.calendar };
    const r = await api('/api/option', { option: opt, dep: x.dep, ret: x.ret, q: S.q });
    R.options.push(r); S.option = r; viewOption();
  } catch (e) { toast(e.message); }
}
function openMonth(ym) {
  const R = S.result; const have = R.options.find((o) => o.dep.startsWith(ym));
  if (have) { S.option = have; return viewOption(); }
  const m = R.months.find((x) => x.ym === ym);
  openFare({ ...m, drive: R.driveBy?.[m.from] });
}
function calendar() { return '<div class="in" id="calbox"></div>'; }
const addYm = (ym, k) => { const d = new Date(+ym.slice(0, 4), +ym.slice(5, 7) - 1 + k, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`; };
// Kalendarz jak w Skyscannerze: najpierw dzień wylotu, potem dzień powrotu, każdy z własną ceną w jedną stronę.
async function drawCal(o) {
  const box = $('#calbox'); if (!box) return;
  S.calCache ||= {};
  const c = (S.cal2 && S.cal2.id === o.id) ? S.cal2 : (S.cal2 = { id: o.id, step: 'out', dep: o.dep, ret: o.ret, ym: o.dep.slice(0, 7) });
  const dir = c.step; const ym = c.ym;
  const key = `${o.from}-${o.to}-${dir}-${ym}-${S.q.direct ? 1 : 0}`;
  const g = S.calCache[key];
  const nowYm = addYm(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`, 0);
  const nn = Math.round((new Date(c.ret) - new Date(c.dep)) / 864e5);
  const head = `<h3 class="big" style="font-size:32px">Kiedy najtaniej</h3>
  <div class="seg calstep"><button data-st="out" aria-pressed="${dir === 'out'}"><small>Wylot</small>${dateL(c.dep)}</button><button data-st="back" aria-pressed="${dir === 'back'}"><small>Powrót</small>${dateL(c.ret)}</button></div>
  <p class="mute" style="margin-top:8px">${dir === 'out' ? `Ceny wylotu ${esc(o.from)} → ${esc(o.to)}` : `Ceny powrotu ${esc(o.to)} → ${esc(o.from)}`} w jedną stronę dla 1 osoby. ${dir === 'out' ? 'Dotknij dnia wylotu, potem wybierz powrót.' : `Dotknij dnia powrotu. Teraz: ${nightsL(nn)}.`}</p>
  <div class="calnav"><button class="round" id="cp" aria-label="Poprzedni miesiąc" ${ym <= nowYm ? 'disabled' : ''}>‹</button><b>${MONTHS[+ym.slice(5, 7) - 1]} ${ym.slice(0, 4)}</b><button class="round" id="cn" aria-label="Następny miesiąc" ${ym >= addYm(nowYm, 12) ? 'disabled' : ''}>›</button></div>`;
  const bind = () => {
    const go = (k) => { c.ym = addYm(ym, k); drawCal(o); };
    const p = $('#cp'); const n = $('#cn');
    if (p) p.onclick = () => go(-1);
    if (n) n.onclick = () => go(1);
    $$('.calstep button').forEach((b) => { b.onclick = () => { c.step = b.dataset.st; c.ym = (c.step === 'out' ? c.dep : c.ret).slice(0, 7); drawCal(o); }; });
    $$('.cal button').forEach((b) => { b.onclick = () => {
      const k = b.dataset.d;
      if (dir === 'out') {
        const len = Math.max(1, nn); c.dep = k; if (c.ret <= k) { const r = new Date(k + 'T12:00'); r.setDate(r.getDate() + len); c.ret = r.toISOString().slice(0, 10); }
        c.step = 'back'; c.ym = c.ret.slice(0, 7); drawCal(o);
      } else { c.ret = k; S.cal2 = { ...c, step: 'out' }; recheck(c.dep, c.ret); }
    }; });
  };
  if (!g) {
    box.innerHTML = `${head}<p class="mute">Sprawdzam ceny w tym miesiącu…</p>`; bind();
    try { const r = await api('/api/calendar1', { from: o.from, to: o.to, ym, dir, direct: !!S.q.direct }); S.calCache[key] = r.days; }
    catch (e) { box.innerHTML = `${head}<p class="warn">${esc(e.message)}</p>`; bind(); return; }
    if (S.cal2 === c && c.ym === ym && c.step === dir && S.option === o) drawCal(o);
    return;
  }
  const vals = Object.entries(g).filter(([k]) => k.startsWith(ym) && (dir === 'out' || k > c.dep)).map(([, v]) => v);
  if (!vals.length) { box.innerHTML = `${head}<p class="mute">Brak lotów w tym miesiącu albo rozkład nie jest jeszcze sprzedawany.</p>`; bind(); return; }
  const sorted = [...vals].sort((x, z) => x - z); const cheap = sorted[Math.floor((sorted.length - 1) / 3)];
  const y = +ym.slice(0, 4); const m = +ym.slice(5, 7) - 1;
  const first = new Date(y, m, 1, 12); const days = new Date(y, m + 1, 0).getDate();
  let cells = '';
  for (let i = 0; i < (first.getDay() + 6) % 7; i++) cells += '<span></span>';
  for (let d = 1; d <= days; d++) {
    const k = `${ym}-${String(d).padStart(2, '0')}`; const v = g[k];
    const ok = v != null && (dir === 'out' || k > c.dep);
    const sel = k === (dir === 'out' ? c.dep : c.ret); const other = dir === 'back' && k === c.dep;
    cells += ok ? `<button data-d="${k}" class="${v <= cheap ? 'low' : ''}" aria-pressed="${sel}" aria-label="${dateL(k)}, ${v} zł">${d}<small>${v}</small></button>` : `<span class="mute${other ? ' dep' : ''}">${d}</span>`;
  }
  box.innerHTML = `${head}<div class="cal cal2">${DAYS.map((d) => `<b>${d}</b>`).join('')}${cells}</div><p class="hint">Zielone: najtańsza jedna trzecia dni. Po wybraniu powrotu sprawdzę konkretne loty i cenę w obie strony dla wszystkich osób.</p>`;
  bind();
}
function passHtml(f, label) {
  const L = f.legs; const a = L[0]; const z = L[L.length - 1];
  return `<div class="pass"><small>${label}: ${dateL(a.dep)}, ${esc(a.airlineName)} ${esc(a.airline)} ${esc(a.no)}</small>
  <div class="pass-r"><div><div class="iata">${a.from}</div><b>${timeL(a.dep)}</b></div><div class="pass-mid">${ICON.plane}</div><div style="text-align:right"><div class="iata">${z.to}</div><b>${timeL(z.arr)}</b></div></div>
  <small>${dur(f.min)}, ${f.stops ? `${f.stops} przesiadk${f.stops > 1 ? 'i' : 'a'} (${L.slice(0, -1).map((l) => l.to).join(', ')})` : 'bez przesiadek'}</small></div>`;
}
function viewOption() {
  const o = S.option;
  const others = (S.result.options || []).filter((x) => x.dest.id === o.dest.id && (!S.result.months || x.dep.slice(0, 7) === o.dep.slice(0, 7)));
  const cmp = others.find((x) => x.compare)?.compare;
  const insight = others.find((x) => x.insight)?.insight;
  const max = cmp ? Math.max(...cmp.map((c) => c.total || 0)) : 1;
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const n = o.pax.adults + o.pax.children;
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>${esc(o.dest.name)}</h2></div>
  <section class="page"><article class="card">${posterOf(o)}
   <div class="in"><p class="big">${zl(o.hotelEst ? o.totalWithHotel : o.total)}</p><p class="mute">${o.hotelEst ? `cały wyjazd bez jedzenia na miejscu, ${n} ${osob(n)}, ${zl(o.perPersonAll)} na osobę` : `loty i dojazd, bez noclegu, ${n} ${osob(n)}`}</p>
    <div style="margin-top:10px">
    <div class="kv"><span>Bilety</span><span>${zl(o.tickets)} <span class="sure ${o.verified ? 'fact' : 'est'}">${o.verified ? 'sprawdzone' : 'z kalendarza'}</span></span></div>
    ${o.access.items.map((i) => `<div class="kv"><span>${esc(i.label)}</span><span>${zl(i.pln)} <span class="sure est">szacunek</span></span></div>`).join('')}
    ${o.bags ? `<div class="kv"><span>Bagaż</span><span>${zl(o.bags)} <span class="sure est">szacunek</span></span></div>` : ''}
    ${o.hotelEst ? `<div class="kv"><span>Nocleg, ${o.nights} nocy</span><span>około ${zl(o.hotelEst.total)} <span class="sure est">szacunek</span></span></div>` : `<div class="kv"><span>Nocleg</span><span class="sure check">nie pobrano cen</span></div>`}</div>
    ${o.bagNote ? `<p class="hint">${esc(o.bagNote)}</p>` : ''}
    ${(o.warnings || []).map((w) => `<p class="warn">${esc(w)}</p>`).join('')}
    ${o.climate?.month?.tmax != null ? `<p class="hint">Średnio w tym miesiącu: ${Math.round(o.climate.month.tmin)}–${Math.round(o.climate.month.tmax)}°C${o.climate.month.sea != null ? `, morze ${Math.round(o.climate.month.sea)}°C` : ''}${o.climate.month.rain != null ? `, opady ${Math.round(o.climate.month.rain)} mm` : ''}.</p>` : ''}
    ${o.flight ? passHtml(o.flight.out, 'Tam') + passHtml(o.flight.back, 'Z powrotem') : ''}
    ${o.leaveHome ? `<p style="margin-top:12px"><b>Z domu wyjeżdżasz ${dateL(o.leaveHome)} o ${timeL(o.leaveHome)}.</b></p>` : ''}
    <div class="acts">${o.flight ? `<button class="btn" id="hot">Wybierz nocleg</button>${propBtn()}` : '<p class="warn">Nie potwierdziliśmy lotów na ten termin. Dotknij innego dnia w kalendarzu poniżej.</p>'}</div></div>
   ${calendar(o)}
   ${cmp?.length > 1 ? `<div class="in"><h3 class="big" style="font-size:32px">Z którego lotniska</h3><p class="mute">Bilety, bagaż i dojazd dla ${n} ${osob(n)}, ${o.compareNights || others[0].nights} nocy, w najtańszym terminie z każdego lotniska. Noclegu tu nie liczymy, bo nie zależy od lotniska.</p>${insight ? `<div class="insight">${esc(insight)}</div>` : ''}
    <div class="bars">${cmp.map((c, ci) => {
      if (c.state === 'none') return `<div class="cmp mute"><div class="t"><span>${esc(c.city)} ${c.from}, ${c.km} km</span><span>brak lotów w sprzedaży na ten termin</span></div></div>`;
      const inner = `<div class="t"><span>${esc(c.city)} ${c.from}, ${c.km} km${c.dep ? `<small class="mute" style="display:block;font-weight:500">${dateL(c.dep)} – ${dateL(c.ret)}${c.stops === 0 ? ', bez przesiadek' : c.stops ? `, przesiadki: ${c.stops}` : ''}</small>` : ''}</span><span>${c.state === 'estimate' ? 'około ' : ''}${zl(c.total)}</span></div><div class="tr" style="width:${(c.total / max) * 100}%"><i class="a" style="flex:${c.tickets}"></i><i class="b" style="flex:${c.access}"></i></div>`;
      return c.optionId ? `<button class="cmp" data-c="${c.optionId}">${inner}</button>` : c.state === 'fare' ? `<button class="cmp" data-f="${ci}">${inner}</button>` : `<div class="cmp">${inner}</div>`;
    }).join('')}</div>
    <div class="legend"><span><i style="background:var(--deep)"></i>bilety</span><span><i style="background:var(--coral)"></i>dojazd i bagaż</span></div></div>` : ''}
   <div class="in" id="carc"></div>
   <div class="in"><h3 class="big" style="font-size:32px">Kup bilety</h3><p class="mute">Otwierają się z wypełnionymi datami. Sprawdź cenę przed zapłatą.</p><div class="linkset">${o.links.map((l) => `<a class="btn line small" href="${url(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join('')}</div><div class="acts"><button class="btn line small" id="wch">Obserwuj cenę tej trasy</button></div></div>
  </article></section>`;
  $('#wch').onclick = () => LV.watchAdd(o, n);
  carCard(o);
  $('#b').onclick = viewResults;
  const h = $('#hot'); if (h) h.onclick = viewHotels;
  const pa = $('#padd'); if (pa) pa.onclick = () => propAdd(o);
  $$('[data-c]').forEach((b) => { b.onclick = () => { S.option = S.result.options.find((x) => x.id === b.dataset.c); viewOption(); }; });
  $$('[data-f]').forEach((b) => { b.onclick = () => { const c = cmp[+b.dataset.f]; openFare({ ...c, destId: o.dest.id }); }; });
  drawCal(o);
  app.scrollTop = 0;
}
async function carCard(o) {
  const el = $('#carc'); if (!el || !S.q.origin) { if (el) el.remove(); return; }
  try {
    const r = await api('/api/car', { lat: S.q.origin.lat, lon: S.q.origin.lon, la: o.dest.lat, lo: o.dest.lon, transport: S.q.transport });
    if (!el.isConnected) return;
    if (r.km > 2200) { el.remove(); return; }
    el.innerHTML = `<h3 class="big" style="font-size:32px">A może autem?</h3><p>${r.km.toLocaleString('pl-PL')} km w jedną stronę, około ${dur(r.min)} z postojami. Paliwo tam i z powrotem około ${zl(r.fuel)}.</p><p class="hint">Bez autostrad i winiet za granicą. Te sprawdź dla swojej trasy. Dla porównania samolot z dojazdem: ${zl(o.total)}.</p><div class="linkset"><a class="btn line small" href="${url(r.map)}" target="_blank" rel="noopener">Trasa</a><button class="btn small" id="bycar">Zaplanuj autem</button></div>`;
    $('#bycar').onclick = () => LV.viewNew({ dest: { id: o.dest.id, name: o.dest.name }, from: o.dep, to: o.ret, mode: 'car' });
  } catch { el.remove(); }
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
  app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi: ${esc(o.dest.name)}</h2></div><section class="page"><div class="card"><div class="in"><p>Zbieram hotele z dwóch źródeł i porównuję ceny. To potrwa około pół minuty.</p><div class="spin"></div></div></div></section>`;
  $('#b').onclick = S.option?.manual ? viewPlan : S.option?.plMode ? viewPLOption : viewOption;
  const P = new URLSearchParams({ dest: o.dest.id, in: o.dep, out: o.ret, adults: o.pax.adults, children: o.pax.children, pref: s.pref, minRating: s.minRating, breakfast: s.breakfast ? 1 : 0 });
  if (s.budget) P.set('budget', s.budget);
  try {
    const r = await api('/api/hotels?' + P);
    S.hotels = r;
    S.hf = S.hf || { breakfast: !!s.breakfast, sort: 'best', pool: false, stars: 0, limit: 12 };
    const list = () => {
      const f = S.hf;
      let v = r.hotels.filter((h) => (!f.breakfast || h.breakfast) && (!f.pool || (h.amen || []).includes('basen')) && (!f.stars || (h.stars || 0) >= f.stars));
      if (f.sort === 'cheap') v = [...v].sort((a, c) => a.bestTotal - c.bestTotal);
      if (f.sort === 'rate') v = [...v].sort((a, c) => (c.rating || 0) - (a.rating || 0) || (c.reviews || 0) - (a.reviews || 0));
      return v;
    };
    const priceBox = (h) => `${h.live ? `<p><span class="sure fact">ceny z serwisów, z podatkami</span></p>` : h.gkey && !h.liveFail ? '<p class="mute" style="font-size:14px">Sprawdzam ceny w serwisach…</p>' : '<p><span class="sure est">cena przybliżona</span></p>'}${h.noOffers ? '<p class="warn">Brak ofert na te daty.</p>' : ''}<div class="pricelist">${h.prices.slice(0, 6).map((p, j) => `<a class="pl ${j === 0 ? 'best' : ''}" href="${url(p.url)}" target="_blank" rel="noopener"><span>${esc(p.site)}${p.via ? ' (przez Google)' : ''}</span><span>${zl(p.total)}</span></a>`).join('')}</div>`;
    const fill = async () => {
      const run = (S.hfRun = {});
      for (const h of list().slice(0, S.hf.limit)) {
        if (S.hfRun !== run || S.hotels !== r || h.live || h.liveFail || !h.gkey) continue;
        try {
          let a = null;
          for (let t = 0; t < 3 && !a; t++) { try { a = await api(`/api/hotel/offers?${new URLSearchParams({ key: h.gkey, in: o.dep, out: o.ret, rooms: r.rooms })}`); } catch (er) { if (t === 2) throw er; await new Promise((ok) => setTimeout(ok, 4000)); } }
          if (a.offers.length) { const bk = a.offers.find((x) => x.site === 'Booking.com'); const top = a.offers.slice(0, 5); if (bk && !top.includes(bk)) top.push(bk); h.prices = top; h.bestTotal = a.offers[0].total; h.bestNight = a.offers[0].night; h.live = true; } else { h.noOffers = true; h.liveFail = true; }
        } catch { h.liveFail = true; }
        const el = document.querySelector(`[data-pl="${CSS.escape(String(h.key))}"]`); if (el) el.innerHTML = priceBox(h);
      }
    };
    const card = (h, i) => `<article class="card hot">${i === 0 && S.hf.sort === 'best' && !h.overBudget ? '<span class="badge">Nasz wybór</span>' : ''}${h.image ? `<img src="${url(h.image)}" alt="${esc(h.name)}" loading="lazy" referrerpolicy="no-referrer">` : ''}
    <div class="in"><h3>${esc(h.name)}</h3><p>${h.rating ? `<span class="stars">${String(h.rating).replace('.', ',')} / 5</span> ` : ''}<span class="mute">${(h.reviews || 0).toLocaleString('pl-PL')} opinii${h.stars ? `, ${h.stars}★` : ''}${h.distKm != null ? `, ${String(h.distKm).replace('.', ',')} km od centrum` : ''}</span></p>
    <p>${h.breakfast ? '<span class="sure fact">śniadanie w cenie</span>' : h.breakfastPaid ? '<span class="sure est">śniadanie płatne</span>' : '<span class="sure check">śniadanie: brak danych</span>'}</p>
    ${h.amen?.filter((a) => a !== 'śniadanie w cenie').length ? `<p class="mute" style="font-size:14px">${esc(h.amen.filter((a) => a !== 'śniadanie w cenie').slice(0, 6).join(', '))}</p>` : ''}
    ${h.overBudget ? '<p class="warn">Ponad Twój budżet.</p>' : ''}
    <div data-pl="${esc(h.key)}">${priceBox(h)}</div>
    ${h.gpage ? `<div class="linkset"><a class="btn line small" href="${url(h.gpage)}" target="_blank" rel="noopener">Ten hotel w Google, wszystkie oferty</a></div>` : ''}
    <div class="acts"><button class="btn" data-h="${esc(h.key)}">Wybieram ten hotel</button></div></div></article>`;
    const draw = () => {
      const v = list(); const f = S.hf; const L = r.hotels;
      const y = app.scrollTop;
      app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi: ${esc(o.dest.name)}</h2></div><section class="page">
      <button class="btn line small lightb" id="ownh">Mam własną rezerwację</button>
      ${!L.length ? `<div class="note"><b>${r.sourceDown ? 'Ceny hoteli są chwilowo niedostępne.' : 'Nie mamy pewnych cen dla tych kryteriów.'}</b><p class="mute">${r.sourceDown ? 'Oba źródła nie odpowiadają. Znajdź nocleg na stronach poniżej, a plan podróży ułożymy i tak.' : 'Złagodź wymagania albo sprawdź oferty bezpośrednio.'}</p><div class="linkset">${Object.entries(r.fallback || {}).slice(0, 4).map(([k, c]) => `<a class="btn line small" href="${url(c)}" target="_blank" rel="noopener">${esc(k)}</a>`).join('')}</div><div class="acts"><button class="btn" id="noh">Ułóż plan bez wybranego hotelu</button></div></div>` : `
      <div class="note info"><b>${v.length} z ${L.length} hoteli, ${L.filter((h) => h.breakfast).length} ze śniadaniem w cenie</b>
        <div class="chips" style="margin-top:8px">
        <button class="chip" data-f="breakfast" aria-pressed="${f.breakfast}">Śniadanie w cenie</button><button class="chip" data-f="pool" aria-pressed="${f.pool}">Basen</button>
        ${[3, 4, 5].map((n) => `<button class="chip" data-st="${n}" aria-pressed="${f.stars === n}">${n}★${n < 5 ? '+' : ''}</button>`).join('')}</div>
        <div class="seg" style="margin-top:8px">${[['best', 'Polecane'], ['cheap', 'Najtaniej'], ['rate', 'Oceny']].map(([k, l]) => `<button data-so="${k}" aria-pressed="${f.sort === k}">${l}</button>`).join('')}</div></div>`}
      ${v.slice(0, f.limit).map(card).join('')}
      ${v.length > f.limit ? '<button class="btn ghost" id="more">Pokaż więcej hoteli</button>' : ''}
      ${L.length && !v.length ? '<div class="note"><b>Żaden hotel nie spełnia tych filtrów.</b></div>' : ''}
      ${L.length ? `<p class="foot">${r.rooms} ${r.rooms > 1 ? 'pokoje' : 'pokój'}, ${r.nights} nocy. ${esc(r.note || '')} Źródła: ${esc((r.sources || []).join(', '))}.</p>` : ''}</section>`;
      $('#b').onclick = S.option?.manual ? viewPlan : S.option?.plMode ? viewPLOption : viewOption;
      $$('[data-f]').forEach((b) => { b.onclick = () => { f[b.dataset.f] = !f[b.dataset.f]; f.limit = 12; draw(); }; });
      $$('[data-st]').forEach((b) => { b.onclick = () => { const n = +b.dataset.st; f.stars = f.stars === n ? 0 : n; f.limit = 12; draw(); }; });
      $$('[data-so]').forEach((b) => { b.onclick = () => { f.sort = b.dataset.so; f.limit = 12; draw(); }; });
      const m = $('#more'); if (m) m.onclick = () => { f.limit += 12; draw(); };
      $$('[data-h]').forEach((b) => { b.onclick = async () => {
        const h = L.find((x) => String(x.key) === b.dataset.h);
        // Plan dostaje cene z oferty, a nie wstepna z listy
        if (h.gkey && !h.live && !h.liveFail) { b.disabled = true; b.textContent = 'Sprawdzam aktualną cenę…'; try { const a = await api(`/api/hotel/offers?${new URLSearchParams({ key: h.gkey, in: o.dep, out: o.ret, rooms: r.rooms })}`); if (a.offers.length) { h.prices = a.offers.slice(0, 6); h.bestTotal = a.offers[0].total; h.bestNight = a.offers[0].night; h.live = true; } } catch { /* zostaje cena z listy */ } }
        buildPlan(h);
      }; });
      $('#ownh').onclick = () => LV.viewOwnHotel(o, buildPlan, viewHotels);
      const nh = $('#noh'); if (nh) nh.onclick = () => buildPlan({ name: 'centrum: ' + o.dest.name, lat: o.dest.lat, lon: o.dest.lon, bestTotal: 0 });
      app.scrollTop = y;
      fill();
    };
    draw();
    app.scrollTop = 0;
  } catch (e) {
    app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi</h2></div><section class="page"><div class="note"><b>${esc(e.message)}</b><div class="acts"><button class="btn" id="r">Spróbuj ponownie</button></div></div></section>`;
    $('#b').onclick = S.option?.manual ? viewPlan : S.option?.plMode ? viewPLOption : viewOption; $('#r').onclick = viewHotels;
  }
}

/* ---------- Kompendium ---------- */
async function buildPlan(hotel) {
  if (S.option.manual) { S.plan.hotel = hotel; LV.put('meta', 'hotel', { hotel }); LV.applyDays(S.plan); LV.savePlan(S.plan); LV.ownToVault(S.plan); S.tab = 'noc'; return viewPlan(); }
  app.innerHTML = `<section class="board-wrap"><h1 class="board-title">Układam plan</h1><div class="bar"><i style="width:60%"></i></div><p class="board-label">Liczę godziny, dojazdy i dni na miejscu</p></section>`;
  try {
    S.plan = S.option.plMode ? await api('/api/pl/plan', { option: S.option, mode: S.option.plMode, hotel, home: S.q.origin, transport: S.q.transport, prefs: S.q.plan || {} })
      : await api('/api/plan', { option: S.option, hotel, home: S.q.origin, prefs: S.q.plan || {} });
    if (S.q.tripBudget) LV.L(S.plan).s.meta.limit = { v: S.q.tripBudget, u: Date.now() };
    LV.ownToVault(S.plan); LV.savePlan(S.plan); LV.ensureRemote(S.plan).catch(() => {});
    S.tab = 'sum'; viewPlan();
  } catch (e) { toast(e.message); viewHotels(); }
}
const SURE = { fact: 'sprawdzone', est: 'szacunek', check: 'sprawdź' };
const evHtml = (e) => `<div class="ev"><time>${timeL(e.at)}</time> <span class="sure ${e.sure}">${SURE[e.sure]}</span><h4>${esc(e.title)}</h4><p>${esc(e.text)}${e.sample ? ' Rozkład z najbliższego takiego dnia tygodnia, sprawdź bliżej wyjazdu.' : ''}</p>
 ${e.legs?.length ? `<ul class="legs">${e.legs.map((l) => `<li>${l.mode === 'WALK' ? `Pieszo ${l.min} min` : `${esc(l.line || l.mode)}: ${esc(l.from)} → ${esc(l.to)}, ${l.min} min`}</li>`).join('')}</ul>` : ''}
 ${e.map ? `<a href="${url(e.map)}" target="_blank" rel="noopener">Pokaż na mapie</a>` : ''}</div>`;
const shortD = (iso) => { const d = new Date(iso.slice(0, 10) + 'T12:00'); return `${d.getDate()}.${String(d.getMonth() + 1).padStart(2, '0')} (${['ND', 'PN', 'WT', 'ŚR', 'CZ', 'PT', 'SB'][d.getDay()]})`; };
const dayStops = (d) => d.stops.filter((s) => !s.meal);
const stopSrc = (s, w) => (s.img ? commons(s.img, w) : artOf(s.kind));
const dayTitle = (d, i, p) => { const st = dayStops(d); if (d.kind === 'departure' && !st.length) return 'Powrót do domu'; if (d.kind === 'arrival' && !st.length) return `${p.option?.manual && p.option.mode !== 'plane' ? 'Przyjazd' : 'Przylot'} do ${p.dest.name.replace(/\s*\(.*/, '')}`; return st.length ? st[0].name : d.kind === 'rest' ? 'Odpoczynek' : 'Dzień wolny'; };
const daySub = (d, p) => { const st = dayStops(d).slice(0, 3).map((s) => s.name); if (st.length) return st.join(', '); return d.kind === 'departure' ? (p.option?.manual && p.option.mode !== 'plane' ? 'Wymeldowanie i droga do domu' : 'Wymeldowanie i droga na lotnisko') : d.kind === 'arrival' ? 'Zakwaterowanie i odpoczynek' : d.kind === 'rest' ? ((p.dest.tags || []).includes('beach') && [5, 6, 7, 8, 9].includes(+d.date.slice(5, 7)) ? 'Plaża, basen i hotel' : 'Odpoczynek, spacer albo hotel') : 'Spacer albo wycieczka'; };
function tipFor(d, p) {
  const k = new Set(dayStops(d).map((s) => s.kind));
  if (d.weather && (d.weather.rain ?? 0) >= 50) return 'Prognoza mówi o deszczu. Weź kurtkę i zacznij od miejsc pod dachem.';
  if (k.has('church')) return 'Do świątyń zwykle obowiązuje skromny strój: zakryte ramiona i kolana.';
  if (k.has('museum')) return 'Bilety do muzeów kup online, żeby ominąć kolejki. Godziny sprawdź dzień wcześniej.';
  if (k.has('ruins')) return 'Na zabytkach starożytnych przydają się wygodne buty i woda. Zamykają je wcześnie zimą.';
  if (k.has('beach')) return 'Sprawdź prognozę i weź krem z filtrem, nawet przy chmurach.';
  return 'Zabierz wygodne buty i miej przy sobie dokument tożsamości.';
}
const planHead = (p, sub) => `<header class="phead"><button class="back" id="b" aria-label="Wstecz">${ICON.back}</button><div><h2>${esc(sub.t)}</h2><p>${esc(sub.s)}</p></div>${sub.r || ''}</header>`;
const planNav = (act) => `<nav class="tabbar" aria-label="Plan podróży">${[['h', 'Start', I.home], ['p', 'Plan podróży', I.cal], ['m', 'Mapa', I.map], ['u', 'Budżet', I.coin], ['d', 'Dokumenty', I.doc]].map(([k, l, ic]) => `<button data-pn="${k}" class="${act === k ? 'on' : ''}">${ic}<span>${l}</span></button>`).join('')}</nav>`;
function bindPlanNav() {
  $$('[data-pn]').forEach((b) => { b.onclick = () => { const k = b.dataset.pn; if (k === 'h') viewHome(); if (k === 'p') { S.tab = 'sum'; viewPlan(); } if (k === 'm') viewTripMap(); if (k === 'u') { S.tab = 'bud'; viewPlan(); } if (k === 'd') viewDocs(); }; });
}
function viewPlan() {
  const p = S.plan; const o = p.option; const c = p.country; const name = p.dest.name.replace(/\s*\(.*/, '');
  S.tab = ['sum', 'loty', 'noc', 'dni', 'bud'].includes(S.tab) ? S.tab : 'sum';
  const hero = photoOf(p.dest.id, 1000);
  const tg = S.dests.find((d) => d.id === p.dest.id)?.tags || [];
  // Morze i gory maja wspolna panorame. Miasto dostaje swoje zdjecie, bo cudza panorama byloby innym miastem.
  const own = { rzym: 'rzym', paryz: 'paryz', barcelona: 'barcelona', santorini: 'santorini' }[p.dest.id];
  const bandSrc = own ? `art/hero/${own}.jpg` : tg.includes('ski') ? 'art/band/gory.jpg' : tg.includes('beach') && !tg.includes('city') ? 'art/band/morze.jpg' : hero?.src || (p.dest.id === 'praga' ? 'art/band/miasto.jpg' : 'art/band/morze.jpg');
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const T = [['sum', 'Podsumowanie', I.sum], ['loty', o.flight ? 'Loty' : 'Dojazd', I.plane], ['noc', 'Nocleg', I.bed], ['dni', 'Plan dnia', I.cal], ['bud', 'Budżet', I.coin]];
  const dayRow = (d, i) => { const st = dayStops(d)[0]; const src = st ? stopSrc(st, 300) : hero?.src; return `<button class="drow" data-d="${i}">${src ? IMG(src, st?.name) : '<span class="ph"></span>'}<span><em>Dzień ${i + 1} – ${shortD(d.date)}</em><b>${esc(dayTitle(d, i, p))}</b><small>${esc(daySub(d, p))}</small></span>${SV('<path d="M9 6l6 6-6 6"/>', 'class="go"')}</button>`; };
  const shape = S.shapes?.[p.dest.cc];
  const shapeSvg = shape ? `<svg class="shape" viewBox="-4 -4 ${shape.w + 8} ${shape.h + 8}" aria-hidden="true"><path d="${shape.d}"/><circle cx="${((p.dest.lon - shape.b[0]) * shape.b[2] * shape.b[3]).toFixed(1)}" cy="${((shape.b[1] - p.dest.lat) * shape.b[3]).toFixed(1)}" r="${Math.max(shape.w, shape.h) / 30}"/></svg>` : '';
  const budget = S.q.stay.budget;
  const stopsN = p.days.reduce((n, d) => n + dayStops(d).length, 0);
  const fo = o.flight?.out.legs[0]; const fr = o.flight?.back.legs[0];
  LV.refreshWeather(p).then((n) => { if (n && S.plan === p) viewPlan(); });
  const bodies = {
    sum: () => `<div class="wcard pill"><h3>Twój plan w pigułce</h3>${shapeSvg}
      <div class="pr">${I.plane}<div>${fo ? `<b>Przelot: ${shortD(fo.dep)} – ${shortD(fr.dep)}</b><small>${esc(o.fromName)} (${o.from}) ↔ ${esc(o.toName)} (${o.to})</small>` : `<b>${esc(o.modeName)}: ${shortD(o.dep)} – ${shortD(o.ret)}</b><small>${esc(o.fromName)} ↔ ${esc(o.toName)}</small>`}</div></div>
      <div class="pr">${I.bed}<div><b>Nocleg: ${esc(p.hotel.bestTotal || p.hotel.own ? p.hotel.name : 'do wyboru')}</b><small>${o.nights} nocy${p.hotel.board ? `, ${esc(p.hotel.board.toLowerCase())}` : p.hotel.breakfast ? ', śniadanie w cenie' : ''}</small></div><i>${I.check}</i></div>
      <div class="pr">${I.map}<div><b>Plan zwiedzania: ${p.days.length} dni</b><small>${stopsN} atrakcji, trasy i restauracje w pobliżu</small></div><i>${I.check}</i></div>
      <div class="pr">${I.coin}<div><b>Budżet (szacunkowy): ${zl(p.total)}</b><small>${['All inclusive', 'Pełne wyżywienie'].includes(p.hotel.board) ? 'Wyżywienie w cenie wyjazdu' : 'Bez jedzenia na miejscu'}</small></div><i>${I.check}</i></div></div>
      <button class="aibtn" id="aio">${I.bulb}<span><b>Zapytaj asystenta</b><small>Zmień plan, znajdź oszczędności, co gdy pada</small></span></button>
      <button class="aibtn" id="padd">${I.heart}<span><b>Dodaj do propozycji</b><small>Wyślij komuś kilka opcji do wyboru, z sercem i komentarzem</small></span></button>
      <div class="wcard"><div class="rowh"><h3>Plan dnia – skrót</h3><button id="all">Zobacz cały plan ›</button></div>${p.days.slice(0, 3).map(dayRow).join('')}</div>
      ${o.leaveHome ? `<div class="tip">${I.bulb}<p><b>Wyjazd z domu:</b> ${dateL(o.leaveHome)} o ${timeL(o.leaveHome)}.</p></div>` : ''}`,
    loty: () => `<div class="wcard">${o.flight ? `${passHtml(o.flight.out, 'Tam')}${passHtml(o.flight.back, 'Z powrotem')}${o.flight.separate ? '<p class="hint">To dwa osobne bilety w jedną stronę.</p>' : ''}` : `<h3>${esc(o.modeName)}</h3>${(o.warnings || []).map((w) => `<p class="warn">${esc(w)}</p>`).join('')}`}<div class="linkset">${o.links.map((l) => `<a class="btn line small" href="${url(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join('')}</div></div>
      <div class="wcard"><h3>Droga tam</h3>${byDay(p.timeline)}</div><div class="wcard"><h3>Droga z powrotem</h3>${byDay(p.return)}</div>`,
    noc: () => `<div class="wcard hotelc">${p.hotel.image ? IMG(p.hotel.image, p.hotel.name) : ''}<h3>${esc(p.hotel.name)}</h3>${p.hotel.own ? `<p><span class="sure fact">Twoja rezerwacja</span></p><p>${esc(p.hotel.address || '')}</p><p class="mute">${dateL(p.hotel.ci)} – ${dateL(p.hotel.co)}${p.hotel.code ? `, numer ${esc(p.hotel.code)}` : ''}${p.hotel.checkin ? `, zameldowanie od ${esc(p.hotel.checkin)}` : ''}</p><div class="linkset"><a class="btn line small" href="https://www.google.com/maps/search/?api=1&query=${p.hotel.lat},${p.hotel.lon}" target="_blank" rel="noopener">Pokaż na mapie</a></div>` : ''}${p.hotel.rating ? `<p><b>${String(p.hotel.rating).replace('.', ',')} / 5</b> <span class="mute">${(p.hotel.reviews || 0).toLocaleString('pl-PL')} opinii</span></p>` : ''}
      <p>${p.hotel.board ? `<span class="sure fact">${esc(p.hotel.board)}</span>` : p.hotel.breakfast ? '<span class="sure fact">śniadanie w cenie</span>' : p.hotel.breakfastPaid ? '<span class="sure est">śniadanie płatne</span>' : ''}</p>${(p.hotel.amen || []).length ? `<p class="mute">${esc(p.hotel.amen.join(', '))}</p>` : ''}
      ${p.hotel.prices?.length ? `<div class="pricelist">${p.hotel.prices.map((x, j) => `<a class="pl ${j === 0 ? 'best' : ''}" href="${url(x.url)}" target="_blank" rel="noopener"><span>${esc(x.site)}${x.via ? ' (przez Google)' : ''}</span><span>${zl(x.total)}</span></a>`).join('')}</div>` : (p.hotel.own ? '' : '<p class="mute">Hotel możesz wybrać później, plan liczymy od centrum.</p>')}${o.manual && !p.dest.id.startsWith('x-') && LV.canEdit() ? '<div class="acts"><button class="btn small" id="fh">Znajdź nocleg</button></div>' : ''}</div>`,
    dni: () => `<div class="wcard">${p.days.map(dayRow).join('')}</div>`,
    bud: () => { const max = Math.max(...p.cost.map((x) => x.pln)); return `${LV.budgetHtml(p)}<div class="wcard"><h3>Koszt planowany</h3><p class="big">${zl(p.total)}</p><p class="mute">cały wyjazd bez jedzenia na miejscu, ${zl(p.total / (o.pax.adults + o.pax.children))} na osobę</p>${p.cost.map((i) => `<div class="cost"><div class="kv"><span>${esc(i.label)}</span><span>${zl(i.pln)} <span class="sure ${i.sure}">${SURE[i.sure]}</span></span></div><i style="width:${(i.pln / max) * 100}%"></i></div>`).join('')}</div>${budget && p.hotel.bestTotal > budget ? `<div class="note"><b>Nocleg przekracza Twój budżet o ${zl(p.hotel.bestTotal - budget)}.</b></div>` : ''}`; },
  };
  app.innerHTML = `${planHead(p, { t: `Plan podróży – ${name}`, s: `${dateL(o.dep)} – ${dateL(o.ret)} (${o.nights} nocy)`, r: `<button class="ico" id="shr" aria-label="Udostępnij">${I.share}</button><button class="ico" id="mn" aria-label="Więcej">${I.dots}</button>` })}
    <section class="plan"><div class="band ${own ? 'hart' : ''}"><img src="${esc(bandSrc)}" alt="" onerror="this.onerror=null;this.src='art/band/miasto.jpg'"></div>
    <div class="ptabs" role="tablist">${T.map(([k, l, ic]) => `<button role="tab" data-t="${k}" class="${S.tab === k ? 'on' : ''}" aria-selected="${S.tab === k}">${ic}<span>${l}</span></button>`).join('')}</div>
    <div class="pbody">${bodies[S.tab]()}<p class="stamp">Plan z ${esc(p.at.replace('T', ', '))}. Działa bez internetu.</p></div></section>${planNav(S.tab === 'bud' ? 'u' : 'p')}`;
  $('#b').onclick = viewTrips;
  $$('.ptabs button').forEach((b) => { b.onclick = () => { S.tab = b.dataset.t; viewPlan(); }; });
  $$('[data-d]').forEach((b) => { b.onclick = () => { S.day = +b.dataset.d; S.dayTab = 'plan'; viewDay(); }; });
  const aio = $('#aio'); if (aio) aio.onclick = LV.viewAI;
  const pd = $('#padd'); if (pd) pd.onclick = () => propAdd(p.option, p);
  const fh = $('#fh'); if (fh) fh.onclick = () => { S.option = o; viewHotels(); };
  if (S.tab === 'bud') LV.bindBudget(p);
  const all = $('#all'); if (all) all.onclick = () => { S.tab = 'dni'; viewPlan(); };
  $('#shr').onclick = LV.viewShare;
  $('#mn').onclick = () => { if (confirm0()) { const l = p.live; if (l?.own && l.k) api('/api/trip/del', { k: l.k }).catch(() => {}); save('trips', load('trips', []).filter((x) => x.option.id !== o.id)); viewTrips(); } };
  bindPlanNav();
}
const confirm0 = () => { const b = S.delArm; S.delArm = true; setTimeout(() => { S.delArm = false; }, 3000); if (!b) toast('Dotknij jeszcze raz, żeby usunąć ten wyjazd.'); return b; };
const byDay = (list) => { const m = {}; list.forEach((e) => { (m[e.at.slice(0, 10)] ||= []).push(e); }); return Object.entries(m).map(([d, L]) => `<p class="mute" style="margin-top:8px">${WEEK[new Date(d + 'T12:00').getDay()]}, ${dateL(d)}</p><div class="tl">${L.map(evHtml).join('')}</div>`).join(''); };
let leafletReady = null;
function leaflet() {
  leafletReady ||= new Promise((ok, no) => {
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = 'vendor/leaflet/leaflet.css'; document.head.append(l);
    const s = document.createElement('script'); s.src = 'vendor/leaflet/leaflet.js'; s.onload = ok; s.onerror = no; document.head.append(s);
  });
  return leafletReady;
}
const ROUTE = { foot: [0, 0, 'Pieszo'], bike: [0, 0, 'Rowerem'], car: [0, 0, 'Autem'] };
async function drawMap(el, pts, opts = {}) {
  try { await leaflet(); } catch { el.innerHTML = '<p class="mute" style="padding:14px">Mapa wymaga internetu.</p>'; return; }
  if (!pts.length || !el.isConnected) return;
  const L = window.L;
  const m = L.map(el, { zoomControl: false, dragging: !!opts.drag, touchZoom: !!opts.drag, scrollWheelZoom: false, doubleClickZoom: !!opts.drag, tap: false, attributionControl: true });
  m.attributionControl.setPrefix('');
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Esri' }).addTo(m);
  const line = L.polyline(pts.map((p) => [p.lat, p.lon]), { color: '#2f6bff', weight: 5, dashArray: '1 10', lineCap: 'round' }).addTo(m);
  pts.forEach((p, i) => L.marker([p.lat, p.lon], { icon: L.divIcon({ className: 'mk', html: `<b>${i + 1}</b><span>${esc(p.name.length > 24 ? p.name.slice(0, 23) + '…' : p.name)}</span>`, iconSize: [30, 30], iconAnchor: [15, 15] }) }).addTo(m));
  m.fitBounds(L.latLngBounds(pts.map((p) => [p.lat, p.lon])).pad(0.22), { maxZoom: 16 });
  if (opts.route && pts.length > 1) {
    const lab = ROUTE[opts.route][2];
    try {
      const j = await api('/api/route', { mode: opts.route, pts: pts.slice(0, 24).map((p) => [p.lat, p.lon]) }); const r = j.routes?.[0]; if (!r) throw new Error();
      line.setLatLngs(r.geometry.coordinates.map(([a, b]) => [b, a])); line.setStyle({ dashArray: null, weight: 4 });
      const info = $('#rinfo'); if (info) info.textContent = `${lab}: ${(r.distance / 1000).toFixed(1).replace('.', ',')} km, około ${dur(Math.round(r.duration / 60))}. Trasa: OpenStreetMap.`;
    } catch { const info = $('#rinfo'); if (info) info.textContent = 'Nie udało się pobrać trasy. Linia pokazuje tylko kolejność.'; }
  }
}
function viewDay() {
  const p = S.plan; const d = p.days[S.day]; const st = dayStops(d); const hb = p.hotel;
  S.dayTab = S.dayTab || 'plan';
  const items = [];
  if (d.kind === 'full' || d.kind === 'rest' || (d.kind === 'departure')) items.push(`<div class="tr"><time>08:00</time><i>${I.fork}</i><div><span>${hb.breakfast ? 'Śniadanie w hotelu' : 'Śniadanie'}</span></div></div>`);
  d.stops.forEach((s, si) => {
    const dn = `<button class="dn ${s.done ? 'on' : ''}" data-dn="${si}" aria-label="Zaliczone" aria-pressed="${!!s.done}">✓</button>`;
    const nt = s.note ? `<small class="nt">${esc(s.note)}</small>` : '';
    if (s.meal) { const r = s.options?.[0]; items.push(`<div class="tr ${s.done ? 'isd' : ''}"><time>${s.time}</time><i>${I.fork}</i><div class="grow"><small>${s.meal === 'lunch' ? 'Obiad' : 'Kolacja'}${r ? ' – restauracja w pobliżu' : ''}</small>${r ? `<a href="${url(r.map)}" target="_blank" rel="noopener"><b>${esc(r.name)}</b></a>${r.cuisine ? `<small>${esc(r.cuisine)}</small>` : ''}` : `<a href="${url(s.mapSearch)}" target="_blank" rel="noopener"><b>Restauracje w pobliżu</b></a>`}${nt}</div>${dn}</div>`); return; }
    const src = stopSrc(s, 300);
    items.push(`<div class="tr ${s.done ? 'isd' : ''}"><time>${s.time}</time><i>${I.walk}</i><div class="grow"><a href="${url(s.map)}" target="_blank" rel="noopener"><b>${esc(s.name)}</b></a><small>${esc(s.type)}, około ${dur(s.min)}${s.walk ? (s.by === 'car' ? `, około ${s.walk} min taksówką lub autem` : `, ${s.walk} min dojścia`) : ''}</small>${s.web ? `<a class="sm" href="${url(s.web)}" target="_blank" rel="noopener">Godziny i bilety</a>` : '<span class="sure check">sprawdź godziny</span>'}${nt}</div>${src ? IMG(src, s.name, 'th') : ''}${dn}</div>`);
  });
  const bodies = {
    plan: () => `${st.length ? '<div class="dmap" id="dm"></div>' : ''}<div class="wbody">${d.sun ? `<p class="mute">Wschód słońca ${d.sun[0]}, zachód ${d.sun[1]}</p>` : ''}${d.weather ? `<p class="mute">Prognoza: ${Math.round(d.weather.tmin)}–${Math.round(d.weather.tmax)}°C${d.weather.feels != null ? `, odczuwalna ${Math.round(d.weather.feels)}°C` : ''}, deszcz ${d.weather.rain ?? '?'}%${d.weather.wind != null ? `, wiatr ${Math.round(d.weather.wind)} km/h` : ''}${d.weather.cloud != null ? `, zachmurzenie ${Math.round(d.weather.cloud)}%` : ''}</p>` : p.climate?.tmax != null ? `<p class="mute">Średnio w tym miesiącu ${Math.round(p.climate.tmin)}–${Math.round(p.climate.tmax)}°C. Prognoza pojawi się na 15 dni przed wyjazdem.</p>` : ''}${LV.canEdit() && swapDay(p.days, S.day) >= 0 ? `<div class="note"><b>Tego dnia ma padać, a plan jest na zewnątrz.</b><p class="mute">Dzień ${swapDay(p.days, S.day) + 1} zapowiada się sucho.</p><div class="acts"><button class="btn small" id="swp" data-j="${swapDay(p.days, S.day)}">Zamień z dniem ${swapDay(p.days, S.day) + 1}</button></div></div>` : ''}${S.edit && LV.canEdit() ? LV.editHtml(d) : `<div class="tline">${items.join('') || `<p class="mute">${esc(daySub(d, p))}.</p>`}</div>${LV.canEdit() ? '<div class="linkset"><button class="btn line small" id="ed">Zmień plan</button><button class="btn line small" id="addS">Dodaj miejsce</button><button class="btn line small" id="planb">Plan B na deszcz</button></div>' : ''}<div class="tip">${I.bulb}<p><b>Wskazówka:</b> ${esc(tipFor(d, p))}</p></div>`}</div>`,
    mapa: () => `<div class="dmap big" id="dm"></div><div class="wbody">${st.map((s, i) => `<div class="kv"><span><b>${i + 1}.</b> ${esc(s.name)}</span><a href="${url(s.map)}" target="_blank" rel="noopener">Nawiguj</a></div>`).join('')}<div class="seg" id="rm">${Object.entries(ROUTE).map(([k, v]) => `<button data-rm2="${k}" aria-pressed="${(S.route || 'foot') === k}">${v[2]}</button>`).join('')}</div><p class="hint" id="rinfo">Liczę trasę…</p></div>`,
    atr: () => `<div class="wbody">${st.map((s) => `<div class="acard">${stopSrc(s, 700) ? IMG(stopSrc(s, 700), s.name) : ''}${!s.img && artOf(s.kind) ? '<p class="illu">Ilustracja poglądowa</p>' : ''}<h3>${esc(s.name)}</h3><p class="mute">${esc(s.type)}, około ${dur(s.min)}</p>${s.info ? `<p>${esc(s.info)}</p>${s.src ? `<a class="sm" href="${url(s.src)}" target="_blank" rel="noopener">Źródło opisu</a>` : '<p class="mute" style="font-size:12px">Opis: Wikipedia</p>'}` : ''}${s.web ? `<a href="${url(s.web)}" target="_blank" rel="noopener">Godziny i bilety</a>` : ''}</div>`).join('') || '<p class="mute">Na ten dzień nie ma atrakcji.</p>'}</div>`,
    gas: () => { const m = d.stops.filter((s) => s.meal); return `<div class="wbody"><img class="artb" src="art/ph/restauracja.jpg" alt="">${m.map((s) => `<h3 class="gh">${s.meal === 'lunch' ? 'Obiad' : 'Kolacja'}, ${s.time}</h3>${(s.options || []).map((r) => `<div class="kv"><span><b>${esc(r.name)}</b><br><small class="mute">${esc(r.cuisine)}</small></span><a href="${url(r.map)}" target="_blank" rel="noopener">Mapa</a></div>`).join('') || '<p class="mute">Brak lokali w bazie dla tej okolicy.</p>'}<a class="sm" href="${url(s.mapSearch)}" target="_blank" rel="noopener">Więcej restauracji i ich oceny</a>`).join('') || '<p class="mute">Na ten dzień nie planujemy posiłków na mieście.</p>'}</div>`; },
  };
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `${planHead(p, { t: `Dzień ${S.day + 1} – ${dayTitle(d, S.day, p)}`, s: `${WEEK[new Date(d.date + 'T12:00').getDay()]}, ${dateL(d.date)}`, r: `<button class="ico" id="ics" aria-label="Dodaj do kalendarza">${I.cal}</button>` })}
    <div class="dtabs">${[['plan', 'Plan dnia'], ['mapa', 'Mapa trasy'], ['atr', 'Atrakcje'], ['gas', 'Gastronomia']].map(([k, l]) => `<button data-x="${k}" class="${S.dayTab === k ? 'on' : ''}">${l}</button>`).join('')}</div>
    <section class="dbody">${bodies[S.dayTab]()}</section>${planNav('p')}`;
  $('#b').onclick = () => { S.tab = 'dni'; viewPlan(); };
  $$('[data-x]').forEach((b) => { b.onclick = () => { S.dayTab = b.dataset.x; viewDay(); }; });
  $('#ics').onclick = () => icsDay(d);
  if (S.dayTab === 'plan') LV.bindDay(viewDay);
  bindPlanNav();
  const el = $('#dm'); if (el) drawMap(el, st.filter((s) => s.lat != null), { drag: S.dayTab === 'mapa', route: S.dayTab === 'mapa' ? (S.route || 'foot') : null });
  $$('[data-rm2]').forEach((b) => { b.onclick = () => { S.route = b.dataset.rm2; viewDay(); }; });
  app.scrollTop = 0;
}
function icsDay(d) {
  const fmt = (day, t) => day.replace(/-/g, '') + 'T' + t.replace(':', '') + '00';
  const ev = dayStops(d).filter((s) => s.time).map((s, i) => { const [h, m] = s.time.split(':').map(Number); const e = h * 60 + m + s.min; return `BEGIN:VEVENT\r\nUID:gt-${d.date}-${i}@globtroter\r\nDTSTAMP:${fmt(d.date, '00:00')}Z\r\nDTSTART:${fmt(d.date, s.time)}\r\nDTEND:${fmt(d.date, `${String(Math.floor(e / 60) % 24).padStart(2, '0')}:${String(e % 60).padStart(2, '0')}`)}\r\nSUMMARY:${s.name.replace(/[,;]/g, ' ')}\r\nEND:VEVENT`; }).join('\r\n');
  const b = new Blob([`BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Globtroter//PL\r\n${ev}\r\nEND:VCALENDAR\r\n`], { type: 'text/calendar' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `dzien-${d.date}.ics`; a.click();
}
function viewTripMap() {
  const p = S.plan; const LY = (S.mapL ||= { plan: true, attr: false, food: false });
  const pts = p.days.flatMap((d, i) => dayStops(d).filter((s) => s.lat != null).map((s) => ({ ...s, day: i })));
  const known = !p.dest.id.startsWith('x-');
  app.innerHTML = `${planHead(p, { t: `Mapa – ${p.dest.name.replace(/\s*\(.*/, '')}`, s: `${pts.length} miejsc w planie` })}${known ? `<div class="dtabs">${[['plan', 'Plan'], ['attr', 'Atrakcje'], ['food', 'Restauracje']].map(([k, l]) => `<button data-ly="${k}" class="${LY[k] ? 'on' : ''}">${l}</button>`).join('')}</div>` : ''}<div class="dmap full" id="dm"></div>${planNav('m')}`;
  $('#b').onclick = () => { S.tab = 'sum'; viewPlan(); }; bindPlanNav();
  $$('[data-ly]').forEach((b) => { b.onclick = () => { LY[b.dataset.ly] = !LY[b.dataset.ly]; viewTripMap(); }; });
  (async () => {
    try { await leaflet(); } catch { $('#dm').innerHTML = '<p class="mute" style="padding:14px">Mapa wymaga internetu.</p>'; return; }
    const L = window.L; const el = $('#dm'); if (!el) return;
    const m = L.map(el, { zoomControl: false, tap: false }); m.attributionControl.setPrefix('');
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Esri' }).addTo(m);
    const COL = ['#2f6bff', '#f6b52e', '#12b886', '#f4533a', '#b197fc', '#22b8cf', '#ff922b', '#e64980'];
    const all = [[p.hotel.lat, p.hotel.lon]];
    L.marker(all[0], { icon: L.divIcon({ className: 'mk', html: '<b style="background:#03122f">H</b>', iconSize: [30, 30], iconAnchor: [15, 15] }) }).addTo(m).bindPopup(esc(p.hotel.name));
    const dot = (a, c, t) => L.circleMarker(a, { radius: 7, color: '#fff', weight: 2, fillColor: c, fillOpacity: 1 }).addTo(m).bindPopup(t);
    if (LY.plan) { pts.forEach((s) => { all.push([s.lat, s.lon]); dot([s.lat, s.lon], COL[s.day % 8], `<b>Dzień ${s.day + 1}</b><br>${esc(s.name)}`); }); }
    m.fitBounds(L.latLngBounds(all).pad(0.15), { maxZoom: 15 });
    if ((LY.attr || LY.food) && known) {
      try {
        const D = await LV.exploreData(p.dest.id);
        if (LY.attr) D.attractions.slice(0, 80).forEach((a) => dot([a.lat, a.lon], '#ffffff', `${esc(a.name)}<br>${esc(a.type)}`));
        if (LY.food) D.restaurants.slice(0, 120).forEach((r) => dot([r.lat, r.lon], '#ff6b6b', `${esc(r.name)}<br>${esc(r.cuisine)}`));
      } catch (e) { toast(e.message); }
    }
  })();
}
function viewDocs() {
  const p = S.plan; const o = p.option; const c = p.country;
  app.innerHTML = `${planHead(p, { t: 'Dokumenty i lista', s: c?.name || p.dest.name })}<section class="dbody"><div class="wbody">
    ${LV.docsHtml(p)}
    <h3 class="gh">Do zrobienia</h3><div class="checks">${p.checklist.map((x, i) => `<label><input type="checkbox" data-ck="${i}" ${(LV.L(p).s.ck[i]?.v || load('ck.' + o.id, {})[i]) ? 'checked' : ''}><span>${esc(x.t)}<br><small class="mute">${dateL(new Date(new Date(o.dep + 'T12:00').getTime() + x.d * 864e5).toISOString())}</small>${x.url ? ` <a href="${url(x.url)}" target="_blank" rel="noopener">Otwórz</a>` : ''}</span></label>`).join('')}</div>
    ${c ? `<h3 class="gh">Na miejscu</h3><div class="kv"><span>Dokument</span><span style="text-align:right">${esc(c.docs)}</span></div><div class="kv"><span>Waluta</span><span>${esc(c.currencyName)}${c.rate ? `, 1 ${c.currency} = ${c.rate.toFixed(2).replace('.', ',')} zł` : ''}</span></div><div class="kv"><span>Język</span><span>${esc(c.language)}</span></div><div class="kv"><span>Gniazdka</span><span>${esc(c.plugs)}</span></div><div class="kv"><span>Numer alarmowy</span><span><a href="tel:${esc(c.emergency.split(' ')[0])}">${esc(c.emergency)}</a></span></div><p class="hint">${esc(c.plugNote)}</p><div class="acts"><a class="btn line small" href="${url(c.msz)}" target="_blank" rel="noopener">Ostrzeżenia i wymogi MSZ</a></div>` : ''}
    ${p.holidays?.length ? `<p class="warn">Święta w czasie pobytu: ${p.holidays.map((h) => `${esc(h.name)} (${dateL(h.date)})`).join(', ')}. Część miejsc może być zamknięta.</p>` : ''}
  </div></section>${planNav('d')}`;
  $('#b').onclick = () => { S.tab = 'sum'; viewPlan(); }; bindPlanNav();
  $$('[data-ck]').forEach((x) => { x.onchange = () => { LV.put('ck', x.dataset.ck, { v: x.checked }); }; });
  LV.bindDocs(p);
  app.scrollTop = 0;
}

// Aktualizacje: kod idzie zawsze najpierw z sieci (sw.js), a przy powrocie do aplikacji sprawdzamy, czy na serwerze jest coś nowszego.
let stamp = '';
async function currentStamp() {
  const heads = await Promise.all(['js/app.js', 'css/app.css'].map((u) => fetch(u, { method: 'HEAD', cache: 'no-store' })));
  return heads.map((r) => r.headers.get('etag') || r.headers.get('last-modified') || '').join('|');
}
let reloading = false;
function freshReload() {
  if (reloading) return;
  if ($('.wiz')) { S.reloadLater = true; return; } // nie przerywamy wypełniania formularza
  reloading = true; location.reload();
}
async function checkForUpdate() {
  if (!navigator.onLine) return;
  try {
    const now2 = await currentStamp();
    if (stamp && now2 && now2 !== stamp) freshReload();
    else if (!stamp) stamp = now2;
  } catch { /* brak sieci: zostajemy na wersji offline */ }
}
function startUpdates() {
  checkForUpdate();
  addEventListener('online', () => { if (S.plan) LV.syncNow(S.plan).catch(() => {}); });
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') { if (S.plan) LV.syncNow(S.plan).catch(() => {}); checkForUpdate(); swReg?.update().catch(() => {}); } });
  addEventListener('pageshow', (e) => { if (e.persisted) checkForUpdate(); });
  if (!('serviceWorker' in navigator)) return;
  const had = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener('controllerchange', () => { if (had) freshReload(); });
  navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' }).then((r) => { swReg = r; r.update().catch(() => {}); }).catch(() => {});
}
let swReg = null;
const LV = initLive({ S, app, $, $$, esc, url, zl, toast, api, load, save, I, IMG, commons, dateL, dur, ICON, planHead, planNav, bindPlanNav, API_LINK: location.origin + location.pathname, viewPlan, viewDay, viewDocs, viewTrips });

(async function boot() {
  try { await data(); } catch { toast('Nie udało się wczytać bazy miejsc. Sprawdź internet.'); }
  viewHome();
  const lk = new URLSearchParams(location.hash.slice(1)).get('t');
  if (lk) { history.replaceState(null, '', location.pathname); if (await LV.openLink(lk)) { viewPlan(); startUpdates(); return; } }
  const pk = new URLSearchParams(location.hash.slice(1)).get('p');
  if (pk) { await viewProp(pk); startUpdates(); return; }
  LV.linkPush();
  const job = load('job', null);
  if (job && Date.now() - job.t < 3e6) { S.q = job.q; if (job.zone) S.zone = job.zone; viewSearch(job.id); }
  startUpdates();
  window.__gt = { S, viewProp, viewPropDraft, viewPropSent, propAdd, viewHotels, viewResults, viewOption, viewPlan, viewDay, viewTrips, viewInspire, viewProfile, viewHome, VERSION };
})();
