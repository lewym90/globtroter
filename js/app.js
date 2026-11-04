import { scene, themeOf, landmarkOf } from './scene.js';
import { flapRow } from './flap.js';
import { initLive } from './live.js';

const API = ['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://127.0.0.1:8796' : 'https://188-68-247-201.sslip.io/globtroter';
const VERSION = '2.5.2';
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
  q: { ...defaults(), ...load('prefs', {}) }, step: 0, airports: [], dests: [], photos: {}, hero: [], shapes: {}, result: null, option: null, plan: null, tab: 'droga', day: 0,
};

let backKey = '';
function setBackdrop(opts) {
  const k = JSON.stringify(opts);
  if (k === backKey) return;
  backKey = k;
  const olds = [...backdrop.children];
  if (opts.photo) backdrop.insertAdjacentHTML('beforeend', `<div class="bdp ${opts.strong ? 'strong' : ''}"><img src="${esc(opts.photo)}" alt=""></div>`);
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
const commons = (f, w) => `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(safeDec(f))}?width=${w}`;
const safeDec = (f) => { try { return decodeURIComponent(f); } catch { return f; } };
const photoOf = (id, w = 900, shift = 0) => { const L = S.photos[id] || []; return L.length ? { ...L[(dayIdx() + shift) % L.length], src: commons(L[(dayIdx() + shift) % L.length].f, w) } : null; };
const heroNow = () => (S.hero.length ? S.hero[dayIdx() % S.hero.length] : null);
const IMG = (src, alt = '', cls = '') => `<img class="${cls}" src="${esc(src)}" alt="${esc(alt)}" loading="lazy" onerror="this.remove()">`;
const SV = (d, extra = '') => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${extra}>${d}</svg>`;
const I = {
  pin: SV('<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.500C5 14.800 12 21 12 21z" fill="currentColor"/><circle cx="12" cy="9.500" r="2.500" fill="#0b1a33" stroke="none"/>'),
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
  bell: SV('<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 21h4"/>'),
  menu: SV('<path d="M4 6h16M4 12h16M4 18h16"/>', 'stroke-width="2.400"'),
  share: SV('<circle cx="6" cy="12" r="2.500"/><circle cx="18" cy="6" r="2.500"/><circle cx="18" cy="18" r="2.500"/><path d="M8 11l8-4M8 13l8 4"/>'),
  dots: SV('<circle cx="12" cy="5" r="1.300" fill="currentColor"/><circle cx="12" cy="12" r="1.300" fill="currentColor"/><circle cx="12" cy="19" r="1.300" fill="currentColor"/>'),
  bulb: SV('<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.500 11c.7.600 1 1.300 1 2h5c0-.7.300-1.400 1-2A6 6 0 0 0 12 3z"/>'),
  walk: SV('<circle cx="13" cy="4.500" r="1.800" fill="currentColor"/><path d="M9 21l2-6-2-3 1-5 3 1 2 3h3M11 15l3 2 1 4M10 7l-3 3v3"/>'),
  fork: SV('<path d="M7 3v8M4 3v5a3 3 0 0 0 6 0V3M7 11v10M17 3c-2 1-3 4-3 8h3v10"/>'),
  car: SV('<path d="M4 16v-3l2-5h12l2 5v3zM4 16v2M20 16v2"/><circle cx="7.500" cy="13.500" r=".8" fill="currentColor"/><circle cx="16.500" cy="13.500" r=".8" fill="currentColor"/>'),
  sum: SV('<rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4M16 3v4M4 10h16M9 15l2 2 4-4"/>'),
};
const tabbar = (act) => `<nav class="tabbar" aria-label="Główna nawigacja">${[['home', 'Start', I.home, viewHome], ['trips', 'Moje podróże', I.cal, viewTrips], ['insp', 'Inspiracje', I.star, viewInspire], ['fav', 'Ulubione', I.heart, viewFav], ['prof', 'Profil', I.user, viewProfile]].map(([k, l, ic]) => `<button data-nav="${k}" class="${act === k ? 'on' : ''}">${ic}<span>${l}</span></button>`).join('')}</nav>`;
const NAV = () => ({ home: viewHome, trips: viewTrips, insp: viewInspire, fav: viewFav, prof: viewProfile });
const bindNav = () => $$('[data-nav]').forEach((b) => { b.onclick = () => NAV()[b.dataset.nav](); });
const CN_ = { beach: 'plaża', city: 'zwiedzanie', ski: 'narty', nature: 'przyroda', party: 'imprezy', family: 'z rodziną', food: 'jedzenie', romance: 'we dwoje' };
function destLabel() {
  const t = S.q.dest;
  if (t.mode === 'city') { const n = t.ids.map((i) => S.dests.find((d) => d.id === i)?.name).filter(Boolean); return n.length ? n.join(', ') : 'Wybierz miejsce'; }
  if (t.mode === 'country') return t.countries.length ? t.countries.join(', ') + (t.style ? `, ${CN_[t.style]}` : '') : 'Wybierz kraj';
  if (t.mode === 'style') return `Styl: ${CN_[t.style] || 'wybierz'}`;
  return 'Gdziekolwiek' + (t.style ? `, ${CN_[t.style]}` : '');
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
  if (m?.then) m.then(); else viewHome();
}

/* ---------- Start ---------- */
function viewHome() {
  if (S.reloadLater) { S.reloadLater = false; freshReload(); }
  const h = heroNow();
  setBackdrop({ photo: h?.src, dim: true });
  const s = S.q;
  const field = (id, ic, lab, val, cls = '') => `<button class="fld ${cls}" id="${id}">${ic}<span><small>${lab}</small><b>${esc(val)}</b></span>${cls.includes('wide') ? SV('<path d="M6 9l6 6 6-6"/>', 'class="chev"') : ''}</button>`;
  const soon = load('trips', []).find((t) => t.option.dep >= new Date().toISOString().slice(0, 10));
  app.innerHTML = `<section class="home">
    <header class="hd"><img src="icons/logo-96.png" alt="" width="56" height="56"><div><strong>Globtroter</strong><span>Twój kompleksowy plan podróży</span></div>
      <button class="ico" id="bell" aria-label="Najbliższa podróż">${I.bell}${soon ? '<i></i>' : ''}</button><button class="ico" id="burger" aria-label="Menu">${I.menu}</button></header>
    <div class="headline"><h1>Zaplanuj idealne wakacje od <em>A do Z</em></h1>
      <p>Loty · Noclegi · Plan zwiedzania · Gastronomia · Logistyka</p></div>
    <div class="form">
      <div class="say"><input id="say" maxlength="400" placeholder="Napisz, np. 5 dni w Rzymie, 2 osoby, 5000 zł" aria-label="Opisz wyjazd jednym zdaniem"><button id="sayb" aria-label="Uzupełnij formularz">${I.search}</button></div>
      ${field('f-dest', I.pin, 'Dokąd chcesz lecieć?', destLabel(), 'wide')}
      <div class="two">${field('f-when', I.cal, 'Kiedy?', whenLabel())}${field('f-pax', I.people, 'Ile osób?', paxLabel())}</div>
      <div class="two">${field('f-bud', I.filter, 'Budżet na nocleg', `do ${zl(s.stay.budget)}`)}${field('f-std', I.bed, 'Standard noclegu', stayLabel())}</div>
      <button class="cta" id="go">${I.search}Zaplanuj podróż</button>
      <p class="from"><button id="f-from">${I.pin}Start: ${esc(s.origin?.label || 'ustaw miejsce wyjazdu')}</button><button id="f-more">Więcej opcji</button></p>
      ${load('last', null) && Date.now() - load('last').t < 6 * 36e5 ? '<button class="lastr" id="lastr">Wróć do ostatnich wyników</button>' : ''}
    </div>
    <div class="feats">${[['insp', I.plane, 'Najlepsze<br>loty'], ['insp', I.bed, 'Sprawdzone<br>noclegi'], ['trips', I.cal, 'Szczegółowy<br>plan dnia'], ['insp', I.pin, 'Zwiedzanie<br>i atrakcje']].map(([k, ic, l]) => `<button data-nav="${k}"><i>${ic}</i><span>${l}</span></button>`).join('')}</div>
    ${h ? `<p class="credit">${esc(h.n)}. Zdjęcie: <a href="https://commons.wikimedia.org/wiki/File:${encodeURIComponent(h.f)}" target="_blank" rel="noopener">Wikimedia Commons</a></p>` : ''}
  </section>${tabbar('home')}`;
  const need = (fn) => () => { fn(); };
  const say = async () => { const t = $('#say').value.trim(); if (!t) return; toast('Czytam…'); try { const did = await LV.askSentence(t); if (!did.length) return toast('Nie wyłapałem szczegółów. Wybierz je niżej.'); viewHome(); toast(`Uzupełnione: ${did.join(', ')}. Sprawdź i szukaj.`); } catch (e) { toast(e.message); } };
  $('#sayb').onclick = say; $('#say').onkeydown = (e) => { if (e.key === 'Enter') say(); };
  $('#f-dest').onclick = need(() => openStep(1));
  $('#f-when').onclick = need(() => openStep(2));
  $('#f-pax').onclick = need(() => openStep(3));
  $('#f-bud').onclick = $('#f-std').onclick = need(() => openStep(5));
  $('#f-from').onclick = need(() => openStep(0));
  $('#f-more').onclick = () => { S.step = 0; viewWizard(); };
  $('#bell').onclick = () => (soon ? viewTrips() : toast('Nie masz jeszcze zaplanowanej podróży.'));
  $('#burger').onclick = viewProfile;
  $('#go').onclick = () => {
    const t = S.q.dest;
    if ((t.mode === 'city' && !t.ids.length) || (t.mode === 'country' && !t.countries.length) || (t.mode === 'style' && !t.style)) return openStep(1);
    if (!S.q.origin) return openStep(0, () => { if (S.q.origin) viewSearch(); else viewHome(); });
    viewSearch();
  };
  const lr = $('#lastr'); if (lr) lr.onclick = () => { const l = load('last'); S.result = l.result; S.q = l.q; viewResults(); };
  bindNav();
  app.scrollTop = 0;
}

const ageLabel = (dep) => { const d = Math.ceil((new Date(dep + 'T12:00') - Date.now()) / 864e5); return d > 1 ? `za ${d} dni` : d === 1 ? 'jutro' : d === 0 ? 'dziś' : 'minęła'; };
const pageTop = (t, sub = '') => `<div class="ptop"><h2>${esc(t)}</h2>${sub ? `<p>${esc(sub)}</p>` : ''}</div>`;
function viewTrips() {
  const T = load('trips', []);
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<section class="tabpage">${pageTop('Moje podróże', T.length ? 'Działają bez internetu, a kopia jest na serwerze.' : '')}
    ${T.length ? T.map((t, i) => { const p = photoOf(t.dest.id, 700); return `<button class="pcard" data-trip="${i}">${p ? IMG(p.src, p.n) : ''}<div><h3>${esc(t.dest.name.replace(/\s*\(.*/, ''))}</h3><p>${dateL(t.option.dep)} – ${dateL(t.option.ret)}, ${ageLabel(t.option.dep)}${t.live?.own === false ? ', wspólny' : ''}</p></div></button>`; }).join('') : `<div class="wcard"><h3>Tu pojawią się Twoje wyjazdy</h3><p class="mute">Po wybraniu lotu i hotelu plan zapisze się tutaj.</p><div class="acts"><button class="btn" id="st">Zaplanuj podróż</button></div></div>`}
  </section>${tabbar('trips')}`;
  $$('[data-trip]').forEach((b) => { b.onclick = () => { S.plan = load('trips', [])[+b.dataset.trip]; LV.applyDays(S.plan); S.tab = 'sum'; viewPlan(); LV.syncNow(S.plan, () => S.tab === 'sum' && viewPlan()).catch(() => {}); }; });
  const st = $('#st'); if (st) st.onclick = viewHome;
  bindNav(); app.scrollTop = 0;
}
const favs = () => load('fav', []);
function toggleFav(id) { const f = favs(); save('fav', f.includes(id) ? f.filter((x) => x !== id) : [...f, id]); }
const fitOf = (d, m, st) => { const c = d.climate; if (!c) return 0; const t = c.tmax[m - 1]; const s = c.sea ? c.sea[m - 1] : null; if (st === 'beach') return s == null ? 0 : Math.min(1, Math.max(0, (t - 16) / 8)) * 0.6 + Math.min(1, Math.max(0, (s - 15) / 7)) * 0.4; if (st === 'ski') return Math.min(1, Math.max(0, (9 - t) / 7)); return 1 - Math.min(1, Math.abs(t - 22) / 16); };
function destCard(d, m) {
  const p = photoOf(d.id, 700); const c = d.climate;
  return `<div class="pcard" data-dest="${d.id}" role="button" tabindex="0">${p ? IMG(p.src, p.n) : ''}<button class="heart ${favs().includes(d.id) ? 'on' : ''}" data-h2="${d.id}" aria-label="Ulubione">${I.heart}</button><div><h3>${esc(d.name.replace(/\s*\(.*/, ''))}</h3><p>${c ? `${Math.round(c.tmax[m - 1])}°C w dzień${c.sea ? `, morze ${Math.round(c.sea[m - 1])}°C` : ''}` : ''}</p></div></div>`;
}
function bindDest() {
  $$('[data-h2]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); toggleFav(b.dataset.h2); b.classList.toggle('on'); }; });
  $$('[data-dest]').forEach((b) => { b.onclick = () => { S.q.dest = { mode: 'city', ids: [b.dataset.dest], countries: [], style: null }; save('prefs', S.q); viewHome(); }; });
}
function viewInspire() {
  const m = S.q.when.mode === 'month' ? S.q.when.month : new Date().getMonth() + 1;
  S.ins = S.ins || 'city';
  const L = S.dests.map((d) => [fitOf(d, m, S.ins), d]).filter(([, d]) => S.ins === 'city' ? d.tags.includes('city') : d.tags.includes(S.ins)).sort((a, b) => b[0] - a[0]).slice(0, 12).map(([, d]) => d);
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<section class="tabpage">${pageTop('Inspiracje', `Najlepsze miejsca na ${MONTHS[m - 1]}. Zdjęcia zmieniają się codziennie o 8:00.`)}
   <div class="pills">${[['city', 'Zwiedzanie'], ['beach', 'Plaża'], ['ski', 'Narty'], ['nature', 'Przyroda'], ['food', 'Jedzenie']].map(([k, l]) => `<button data-i="${k}" class="${S.ins === k ? 'on' : ''}">${l}</button>`).join('')}</div>
   <div class="grid">${L.map((d) => destCard(d, m)).join('')}</div></section>${tabbar('insp')}`;
  $$('[data-i]').forEach((b) => { b.onclick = () => { S.ins = b.dataset.i; viewInspire(); }; });
  bindDest(); bindNav(); app.scrollTop = 0;
}
function viewFav() {
  const m = new Date().getMonth() + 1; const L = favs().map((i) => S.dests.find((d) => d.id === i)).filter(Boolean);
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  app.innerHTML = `<section class="tabpage">${pageTop('Ulubione')}${L.length ? `<div class="grid">${L.map((d) => destCard(d, m)).join('')}</div>` : '<div class="wcard"><h3>Nic tu jeszcze nie ma</h3><p class="mute">Dotknij serca przy miejscu w Inspiracjach.</p></div>'}</section>${tabbar('fav')}`;
  bindDest(); bindNav(); app.scrollTop = 0;
}
function viewProfile() {
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const q = S.q;
  const row = (id, l, v) => `<button class="kvb" id="${id}"><span>${l}</span><b>${esc(v)}</b></button>`;
  app.innerHTML = `<section class="tabpage">${pageTop('Profil')}
   <div class="wcard"><h3>Moje ustawienia</h3>
   ${row('p0', 'Miejsce wyjazdu', q.origin?.label || 'nie ustawiono')}${row('p3', 'Osoby i bagaż', paxLabel())}
   ${row('p4', 'Dojazd na lotnisko', { car: 'Autem', dropoff: 'Podwiezie mnie', public: 'Komunikacją' }[q.transport.mode])}${row('p5', 'Nocleg', stayLabel())}${row('p6', 'Styl zwiedzania', { slow: 'Spokojnie', normal: 'Normalnie', fast: 'Intensywnie' }[q.plan?.pace || 'normal'])}</div>
   ${LV.pushHtml()}
   <div class="wcard"><h3>Skąd są dane</h3><p class="mute">Loty: Google i Ryanair. Część hoteli: Google. Hotele i ceny: Xotelo. Dojazd: OSRM i Transitous. Klimat: Meteostat i Open-Meteo. Atrakcje i zdjęcia: Wikidata i Wikimedia Commons. Opisy: Wikipedia. Restauracje: OpenStreetMap. Mapa lotnicza: Esri. Kursy: NBP.</p></div>
   <p class="foot">Globtroter ${VERSION}. Aplikacja niekomercyjna.</p></section>${tabbar('prof')}`;
  [['p0', 0], ['p3', 3], ['p4', 4], ['p5', 5], ['p6', 6]].forEach(([id, i]) => { $('#' + id).onclick = () => openStep(i, viewProfile); });
  LV.bindPush(viewProfile);
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
  $('#back').onclick = () => { if (S.step > 0) { S.step--; viewWizard(); } else viewHome(); };
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
  const TP = { beach: 'split', city: 'rzym', ski: 'zermatt', nature: 'madera-funchal', party: 'ibiza', family: 'palma-de-mallorca', food: 'bolonia', romance: 'wenecja' };
  const tiles = () => `<div class="tiles">${STYLES.map(([k, l]) => { const p = photoOf(TP[k], 500); return `<button class="tile" data-style="${k}" aria-pressed="${t.style === k}">${p ? IMG(p.src, '') : ''}<b>${l}</b></button>`; }).join('')}</div>`;
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
    $('#next').onclick = () => { save('prefs', S.q); if (S.modal) closeModal(); else viewSearch(); };
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
  const d = o.dest; const p = photoOf(d.id, 900);
  return `<div class="poster">${scene(sceneOf(d))}${p ? IMG(p.src, p.n, 'ph') : ''}<span class="shade"></span>${h}<h3>${esc(d.name.replace(/\s*\(.*/, ''))}</h3></div>`;
}
function viewResults() {
  const R = S.result;
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
async function drawCal(o) {
  const box = $('#calbox'); if (!box) return;
  S.calCache ||= {};
  const ym = S.calYm || o.dep.slice(0, 7);
  const key = `${o.from}-${o.to}-${o.nights}-${ym}`;
  const here = (o.calendar || []).filter((x) => x.dep.startsWith(ym));
  let g = here.length ? here : S.calCache[key];
  const nowYm = addYm(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`, 0);
  const head = `<h3 class="big" style="font-size:32px">Kiedy najtaniej</h3><p class="mute">Bilet w obie strony dla 1 osoby według dnia wylotu, ${o.nights} nocy. Dotknij dnia, by sprawdzić.</p>
  <div class="calnav"><button class="round" id="cp" aria-label="Poprzedni miesiąc" ${ym <= nowYm ? 'disabled' : ''}>‹</button><b>${MONTHS[+ym.slice(5, 7) - 1]} ${ym.slice(0, 4)}</b><button class="round" id="cn" aria-label="Następny miesiąc" ${ym >= addYm(nowYm, 12) ? 'disabled' : ''}>›</button></div>`;
  const bind = () => {
    const go = (k) => { S.calYm = addYm(ym, k); drawCal(o); };
    const p = $('#cp'); const n = $('#cn');
    if (p) p.onclick = () => go(-1);
    if (n) n.onclick = () => go(1);
    $$('.cal button').forEach((b) => { b.onclick = () => recheck(b.dataset.dep, b.dataset.ret); });
  };
  if (!g) {
    box.innerHTML = `${head}<p class="mute">Sprawdzam ceny w tym miesiącu…</p>`; bind();
    try { const r = await api('/api/calendar', { from: o.from, to: o.to, ym, nights: o.nights, direct: !!S.q.direct }); S.calCache[key] = r.grid; }
    catch (e) { box.innerHTML = `${head}<p class="warn">${esc(e.message)}</p>`; bind(); return; }
    if ((S.calYm || o.dep.slice(0, 7)) === ym && S.option === o) drawCal(o);
    return;
  }
  if (!g.length) { box.innerHTML = `${head}<p class="mute">Brak lotów w tym miesiącu albo rozkład nie jest jeszcze sprzedawany.</p>`; bind(); return; }
  const lo = Math.min(...g.map((x) => x.price)); const hi = Math.max(...g.map((x) => x.price));
  const map = Object.fromEntries(g.map((x) => [x.dep, x]));
  const y = +ym.slice(0, 4); const m = +ym.slice(5, 7) - 1;
  const first = new Date(y, m, 1, 12); const days = new Date(y, m + 1, 0).getDate();
  let cells = '';
  for (let i = 0; i < (first.getDay() + 6) % 7; i++) cells += '<span></span>';
  for (let d = 1; d <= days; d++) {
    const k = `${ym}-${String(d).padStart(2, '0')}`; const x = map[k];
    cells += x ? `<button data-dep="${k}" data-ret="${x.ret}" style="background:${heat(x.price, lo, hi)}" aria-pressed="${k === o.dep}" aria-label="${dateL(k)}, ${x.price} zł">${d}<small>${x.price}</small></button>` : `<span class="mute">${d}</span>`;
  }
  box.innerHTML = `${head}<div class="cal">${DAYS.map((d) => `<b>${d}</b>`).join('')}${cells}</div>`;
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
    <div class="acts">${o.flight ? `<button class="btn" id="hot">Wybierz nocleg</button>` : '<p class="warn">Nie potwierdziliśmy lotów na ten termin. Dotknij innego dnia w kalendarzu poniżej.</p>'}</div></div>
   ${calendar(o)}
   ${cmp?.length > 1 ? `<div class="in"><h3 class="big" style="font-size:32px">Z którego lotniska</h3><p class="mute">Bilety, bagaż i dojazd dla ${n} ${osob(n)}, ${o.compareNights || others[0].nights} nocy, w najtańszym terminie z każdego lotniska. Noclegu tu nie liczymy, bo nie zależy od lotniska.</p>${insight ? `<div class="insight">${esc(insight)}</div>` : ''}
    <div class="bars">${cmp.map((c, ci) => {
      if (c.state === 'none') return `<div class="cmp mute"><div class="t"><span>${esc(c.city)} ${c.from}, ${c.km} km</span><span>brak lotów w tym terminie</span></div></div>`;
      const inner = `<div class="t"><span>${esc(c.city)} ${c.from}, ${c.km} km${c.dep ? `<small class="mute" style="display:block;font-weight:500">${dateL(c.dep)} – ${dateL(c.ret)}${c.stops === 0 ? ', bez przesiadek' : c.stops ? `, przesiadki: ${c.stops}` : ''}</small>` : ''}</span><span>${c.state === 'estimate' ? 'około ' : ''}${zl(c.total)}</span></div><div class="tr" style="width:${(c.total / max) * 100}%"><i class="a" style="flex:${c.tickets}"></i><i class="b" style="flex:${c.access}"></i></div>`;
      return c.optionId ? `<button class="cmp" data-c="${c.optionId}">${inner}</button>` : c.state === 'fare' ? `<button class="cmp" data-f="${ci}">${inner}</button>` : `<div class="cmp">${inner}</div>`;
    }).join('')}</div>
    <div class="legend"><span><i style="background:var(--deep)"></i>bilety</span><span><i style="background:var(--coral)"></i>dojazd i bagaż</span></div></div>` : ''}
   <div class="in"><h3 class="big" style="font-size:32px">Kup bilety</h3><p class="mute">Otwierają się z wypełnionymi datami. Sprawdź cenę przed zapłatą.</p><div class="linkset">${o.links.map((l) => `<a class="btn line small" href="${url(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join('')}</div></div>
  </article></section>`;
  $('#b').onclick = viewResults;
  const h = $('#hot'); if (h) h.onclick = viewHotels;
  $$('[data-c]').forEach((b) => { b.onclick = () => { S.option = S.result.options.find((x) => x.id === b.dataset.c); viewOption(); }; });
  $$('[data-f]').forEach((b) => { b.onclick = () => { const c = cmp[+b.dataset.f]; openFare({ ...c, destId: o.dest.id }); }; });
  S.calYm = null; drawCal(o);
  app.scrollTop = 0;
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
  $('#b').onclick = viewOption;
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
    const card = (h, i) => `<article class="card hot">${i === 0 && S.hf.sort === 'best' && !h.overBudget ? '<span class="badge">Nasz wybór</span>' : ''}${h.image ? `<img src="${url(h.image)}" alt="${esc(h.name)}" loading="lazy" referrerpolicy="no-referrer">` : ''}
    <div class="in"><h3>${esc(h.name)}</h3><p>${h.rating ? `<span class="stars">${String(h.rating).replace('.', ',')} / 5</span> ` : ''}<span class="mute">${(h.reviews || 0).toLocaleString('pl-PL')} opinii${h.stars ? `, ${h.stars}★` : ''}${h.distKm != null ? `, ${String(h.distKm).replace('.', ',')} km od centrum` : ''}</span></p>
    <p>${h.breakfast ? '<span class="sure fact">śniadanie w cenie</span>' : h.breakfastPaid ? '<span class="sure est">śniadanie płatne</span>' : '<span class="sure check">śniadanie: brak danych</span>'}</p>
    ${h.amen?.filter((a) => a !== 'śniadanie w cenie').length ? `<p class="mute" style="font-size:14px">${esc(h.amen.filter((a) => a !== 'śniadanie w cenie').slice(0, 6).join(', '))}</p>` : ''}
    ${h.overBudget ? '<p class="warn">Ponad Twój budżet.</p>' : ''}
    <div class="pricelist">${h.prices.map((p, j) => `<a class="pl ${j === 0 ? 'best' : ''}" href="${url(p.url)}" target="_blank" rel="noopener"><span>${esc(p.site)}</span><span>${zl(p.total)}</span></a>`).join('')}</div>
    ${h.compare?.length ? `<p class="hint">Szukaj też na tych stronach. Szukamy po nazwie, więc sprawdź, czy otwarty hotel to ten sam. Nie każdy hotel jest na każdej stronie.</p><div class="linkset">${h.compare.map((c) => `<a class="btn line small" href="${url(c.url)}" target="_blank" rel="noopener">${esc(c.site)}</a>`).join('')}</div>` : ''}
    <div class="acts"><button class="btn" data-h="${esc(h.key)}">Wybieram ten hotel</button></div></div></article>`;
    const draw = () => {
      const v = list(); const f = S.hf; const L = r.hotels;
      const y = app.scrollTop;
      app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Noclegi: ${esc(o.dest.name)}</h2></div><section class="page">
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
      $('#b').onclick = viewOption;
      $$('[data-f]').forEach((b) => { b.onclick = () => { f[b.dataset.f] = !f[b.dataset.f]; f.limit = 12; draw(); }; });
      $$('[data-st]').forEach((b) => { b.onclick = () => { const n = +b.dataset.st; f.stars = f.stars === n ? 0 : n; f.limit = 12; draw(); }; });
      $$('[data-so]').forEach((b) => { b.onclick = () => { f.sort = b.dataset.so; f.limit = 12; draw(); }; });
      const m = $('#more'); if (m) m.onclick = () => { f.limit += 12; draw(); };
      $$('[data-h]').forEach((b) => { b.onclick = () => buildPlan(L.find((h) => String(h.key) === b.dataset.h)); });
      const nh = $('#noh'); if (nh) nh.onclick = () => buildPlan({ name: 'centrum: ' + o.dest.name, lat: o.dest.lat, lon: o.dest.lon, bestTotal: 0 });
      app.scrollTop = y;
    };
    draw();
    app.scrollTop = 0;
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
    if (S.q.tripBudget) LV.L(S.plan).s.meta.limit = { v: S.q.tripBudget, u: Date.now() };
    LV.savePlan(S.plan); LV.ensureRemote(S.plan).catch(() => {});
    S.tab = 'sum'; viewPlan();
  } catch (e) { toast(e.message); viewHotels(); }
}
const SURE = { fact: 'sprawdzone', est: 'szacunek', check: 'sprawdź' };
const evHtml = (e) => `<div class="ev"><time>${timeL(e.at)}</time> <span class="sure ${e.sure}">${SURE[e.sure]}</span><h4>${esc(e.title)}</h4><p>${esc(e.text)}${e.sample ? ' Rozkład z najbliższego takiego dnia tygodnia, sprawdź bliżej wyjazdu.' : ''}</p>
 ${e.legs?.length ? `<ul class="legs">${e.legs.map((l) => `<li>${l.mode === 'WALK' ? `Pieszo ${l.min} min` : `${esc(l.line || l.mode)}: ${esc(l.from)} → ${esc(l.to)}, ${l.min} min`}</li>`).join('')}</ul>` : ''}
 ${e.map ? `<a href="${url(e.map)}" target="_blank" rel="noopener">Pokaż na mapie</a>` : ''}</div>`;
const shortD = (iso) => { const d = new Date(iso.slice(0, 10) + 'T12:00'); return `${d.getDate()}.${String(d.getMonth() + 1).padStart(2, '0')} (${['ND', 'PN', 'WT', 'ŚR', 'CZ', 'PT', 'SB'][d.getDay()]})`; };
const dayStops = (d) => d.stops.filter((s) => !s.meal);
const stopSrc = (s, w) => (s.img ? commons(s.img, w) : null);
const dayTitle = (d, i, p) => { const st = dayStops(d); if (d.kind === 'departure' && !st.length) return 'Powrót do domu'; if (d.kind === 'arrival' && !st.length) return `Przylot do ${p.dest.name.replace(/\s*\(.*/, '')}`; return st.length ? st[0].name : 'Dzień wolny'; };
const daySub = (d, p) => { const st = dayStops(d).slice(0, 3).map((s) => s.name); if (st.length) return st.join(', '); return d.kind === 'departure' ? 'Wymeldowanie i droga na lotnisko' : d.kind === 'arrival' ? 'Zakwaterowanie i odpoczynek' : 'Plaża, spacer albo wycieczka'; };
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
  setBackdrop({ photo: heroNow()?.src, dim: true, strong: true });
  const T = [['sum', 'Podsumowanie', I.sum], ['loty', 'Loty', I.plane], ['noc', 'Nocleg', I.bed], ['dni', 'Plan dnia', I.cal], ['bud', 'Budżet', I.coin]];
  const dayRow = (d, i) => { const st = dayStops(d)[0]; const src = st ? stopSrc(st, 300) : hero?.src; return `<button class="drow" data-d="${i}">${src ? IMG(src, st?.name) : '<span class="ph"></span>'}<span><em>Dzień ${i + 1} – ${shortD(d.date)}</em><b>${esc(dayTitle(d, i, p))}</b><small>${esc(daySub(d, p))}</small></span>${SV('<path d="M9 6l6 6-6 6"/>', 'class="go"')}</button>`; };
  const shape = S.shapes?.[p.dest.cc];
  const shapeSvg = shape ? `<svg class="shape" viewBox="-4 -4 ${shape.w + 8} ${shape.h + 8}" aria-hidden="true"><path d="${shape.d}"/><circle cx="${((p.dest.lon - shape.b[0]) * shape.b[2] * shape.b[3]).toFixed(1)}" cy="${((shape.b[1] - p.dest.lat) * shape.b[3]).toFixed(1)}" r="${Math.max(shape.w, shape.h) / 30}"/></svg>` : '';
  const budget = S.q.stay.budget;
  const stopsN = p.days.reduce((n, d) => n + dayStops(d).length, 0);
  const fo = o.flight.out.legs[0]; const fr = o.flight.back.legs[0];
  const bodies = {
    sum: () => `<div class="wcard pill"><h3>Twój plan w pigułce</h3>${shapeSvg}
      <div class="pr">${I.plane}<div><b>Przelot: ${shortD(fo.dep)} – ${shortD(fr.dep)}</b><small>${esc(o.fromName)} (${o.from}) ↔ ${esc(o.toName)} (${o.to})</small></div></div>
      <div class="pr">${I.bed}<div><b>Nocleg: ${esc(p.hotel.bestTotal ? p.hotel.name : 'do wyboru')}</b><small>${o.nights} nocy${p.hotel.breakfast ? ', śniadanie w cenie' : ''}</small></div><i>${I.check}</i></div>
      <div class="pr">${I.map}<div><b>Plan zwiedzania: ${p.days.length} dni</b><small>${stopsN} atrakcji, trasy i restauracje w pobliżu</small></div><i>${I.check}</i></div>
      <div class="pr">${I.coin}<div><b>Budżet (szacunkowy): ${zl(p.total)}</b><small>Bez jedzenia na miejscu</small></div><i>${I.check}</i></div></div>
      <button class="aibtn" id="aio">${I.bulb}<span><b>Zapytaj asystenta</b><small>Zmień plan, znajdź oszczędności, co gdy pada</small></span></button>
      <div class="wcard"><div class="rowh"><h3>Plan dnia – skrót</h3><button id="all">Zobacz cały plan ›</button></div>${p.days.slice(0, 3).map(dayRow).join('')}</div>
      ${o.leaveHome ? `<div class="tip">${I.bulb}<p><b>Wyjazd z domu:</b> ${dateL(o.leaveHome)} o ${timeL(o.leaveHome)}.</p></div>` : ''}`,
    loty: () => `<div class="wcard">${passHtml(o.flight.out, 'Tam')}${passHtml(o.flight.back, 'Z powrotem')}${o.flight.separate ? '<p class="hint">To dwa osobne bilety w jedną stronę.</p>' : ''}<div class="linkset">${o.links.map((l) => `<a class="btn line small" href="${url(l.url)}" target="_blank" rel="noopener">${esc(l.site)}</a>`).join('')}</div></div>
      <div class="wcard"><h3>Droga tam</h3>${byDay(p.timeline)}</div><div class="wcard"><h3>Droga z powrotem</h3>${byDay(p.return)}</div>`,
    noc: () => `<div class="wcard hotelc">${p.hotel.image ? IMG(p.hotel.image, p.hotel.name) : ''}<h3>${esc(p.hotel.name)}</h3>${p.hotel.rating ? `<p><b>${String(p.hotel.rating).replace('.', ',')} / 5</b> <span class="mute">${(p.hotel.reviews || 0).toLocaleString('pl-PL')} opinii</span></p>` : ''}
      <p>${p.hotel.breakfast ? '<span class="sure fact">śniadanie w cenie</span>' : p.hotel.breakfastPaid ? '<span class="sure est">śniadanie płatne</span>' : ''}</p>${(p.hotel.amen || []).length ? `<p class="mute">${esc(p.hotel.amen.join(', '))}</p>` : ''}
      ${p.hotel.prices?.length ? `<div class="pricelist">${p.hotel.prices.map((x, j) => `<a class="pl ${j === 0 ? 'best' : ''}" href="${url(x.url)}" target="_blank" rel="noopener"><span>${esc(x.site)}</span><span>${zl(x.total)}</span></a>`).join('')}</div>` : '<p class="mute">Hotel możesz wybrać później, plan liczymy od centrum.</p>'}</div>`,
    dni: () => `<div class="wcard">${p.days.map(dayRow).join('')}</div>`,
    bud: () => { const max = Math.max(...p.cost.map((x) => x.pln)); return `${LV.budgetHtml(p)}<div class="wcard"><h3>Koszt planowany</h3><p class="big">${zl(p.total)}</p><p class="mute">cały wyjazd bez jedzenia na miejscu, ${zl(p.total / (o.pax.adults + o.pax.children))} na osobę</p>${p.cost.map((i) => `<div class="cost"><div class="kv"><span>${esc(i.label)}</span><span>${zl(i.pln)} <span class="sure ${i.sure}">${SURE[i.sure]}</span></span></div><i style="width:${(i.pln / max) * 100}%"></i></div>`).join('')}</div>${budget && p.hotel.bestTotal > budget ? `<div class="note"><b>Nocleg przekracza Twój budżet o ${zl(p.hotel.bestTotal - budget)}.</b></div>` : ''}`; },
  };
  app.innerHTML = `${planHead(p, { t: `Plan podróży – ${name}`, s: `${dateL(o.dep)} – ${dateL(o.ret)} (${o.nights} nocy)`, r: `<button class="ico" id="shr" aria-label="Udostępnij">${I.share}</button><button class="ico" id="mn" aria-label="Więcej">${I.dots}</button>` })}
    <section class="plan"><div class="band"><img src="${esc(hero?.src || heroNow()?.src || '')}" alt="" onerror="this.onerror=null;this.src='${esc(heroNow()?.src || '')}'"></div>
    <div class="ptabs" role="tablist">${T.map(([k, l, ic]) => `<button role="tab" data-t="${k}" class="${S.tab === k ? 'on' : ''}" aria-selected="${S.tab === k}">${ic}<span>${l}</span></button>`).join('')}</div>
    <div class="pbody">${bodies[S.tab]()}<p class="stamp">Plan z ${esc(p.at.replace('T', ', '))}. Działa bez internetu.</p></div></section>${planNav(S.tab === 'bud' ? 'u' : 'p')}`;
  $('#b').onclick = viewTrips;
  $$('.ptabs button').forEach((b) => { b.onclick = () => { S.tab = b.dataset.t; viewPlan(); }; });
  $$('[data-d]').forEach((b) => { b.onclick = () => { S.day = +b.dataset.d; S.dayTab = 'plan'; viewDay(); }; });
  const aio = $('#aio'); if (aio) aio.onclick = LV.viewAI;
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
async function drawMap(el, pts, opts = {}) {
  try { await leaflet(); } catch { el.innerHTML = '<p class="mute" style="padding:14px">Mapa wymaga internetu.</p>'; return; }
  if (!pts.length || !el.isConnected) return;
  const L = window.L;
  const m = L.map(el, { zoomControl: false, dragging: !!opts.drag, touchZoom: !!opts.drag, scrollWheelZoom: false, doubleClickZoom: !!opts.drag, tap: false, attributionControl: true });
  m.attributionControl.setPrefix('');
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Esri' }).addTo(m);
  L.polyline(pts.map((p) => [p.lat, p.lon]), { color: '#2f6bff', weight: 5, dashArray: '1 10', lineCap: 'round' }).addTo(m);
  pts.forEach((p, i) => L.marker([p.lat, p.lon], { icon: L.divIcon({ className: 'mk', html: `<b>${i + 1}</b><span>${esc(p.name.length > 24 ? p.name.slice(0, 23) + '…' : p.name)}</span>`, iconSize: [30, 30], iconAnchor: [15, 15] }) }).addTo(m));
  m.fitBounds(L.latLngBounds(pts.map((p) => [p.lat, p.lon])).pad(0.22), { maxZoom: 16 });
}
function viewDay() {
  const p = S.plan; const d = p.days[S.day]; const st = dayStops(d); const hb = p.hotel;
  S.dayTab = S.dayTab || 'plan';
  const items = [];
  if (d.kind === 'full' || (d.kind === 'departure')) items.push(`<div class="tr"><time>08:00</time><i>${I.fork}</i><div><span>${hb.breakfast ? 'Śniadanie w hotelu' : 'Śniadanie'}</span></div></div>`);
  d.stops.forEach((s, si) => {
    const dn = `<button class="dn ${s.done ? 'on' : ''}" data-dn="${si}" aria-label="Zaliczone" aria-pressed="${!!s.done}">✓</button>`;
    const nt = s.note ? `<small class="nt">${esc(s.note)}</small>` : '';
    if (s.meal) { const r = s.options?.[0]; items.push(`<div class="tr ${s.done ? 'isd' : ''}"><time>${s.time}</time><i>${I.fork}</i><div class="grow"><small>${s.meal === 'lunch' ? 'Obiad' : 'Kolacja'}${r ? ' – restauracja w pobliżu' : ''}</small>${r ? `<a href="${url(r.map)}" target="_blank" rel="noopener"><b>${esc(r.name)}</b></a>${r.cuisine ? `<small>${esc(r.cuisine)}</small>` : ''}` : `<a href="${url(s.mapSearch)}" target="_blank" rel="noopener"><b>Restauracje w pobliżu</b></a>`}${nt}</div>${dn}</div>`); return; }
    const src = stopSrc(s, 300);
    items.push(`<div class="tr ${s.done ? 'isd' : ''}"><time>${s.time}</time><i>${I.walk}</i><div class="grow"><a href="${url(s.map)}" target="_blank" rel="noopener"><b>${esc(s.name)}</b></a><small>${esc(s.type)}, około ${dur(s.min)}${s.walk ? `, ${s.walk} min dojścia` : ''}</small>${s.web ? `<a class="sm" href="${url(s.web)}" target="_blank" rel="noopener">Godziny i bilety</a>` : '<span class="sure check">sprawdź godziny</span>'}${nt}</div>${src ? IMG(src, s.name, 'th') : ''}${dn}</div>`);
  });
  const bodies = {
    plan: () => `${st.length ? '<div class="dmap" id="dm"></div>' : ''}<div class="wbody">${d.sun ? `<p class="mute">Wschód słońca ${d.sun[0]}, zachód ${d.sun[1]}</p>` : ''}${d.weather ? `<p class="mute">Prognoza: ${Math.round(d.weather.tmin)}–${Math.round(d.weather.tmax)}°C, deszcz ${d.weather.rain ?? '?'}%</p>` : ''}${S.edit && LV.canEdit() ? LV.editHtml(d) : `<div class="tline">${items.join('') || `<p class="mute">${esc(daySub(d, p))}.</p>`}</div>${LV.canEdit() ? '<div class="linkset"><button class="btn line small" id="ed">Zmień plan</button><button class="btn line small" id="addS">Dodaj miejsce</button><button class="btn line small" id="planb">Plan B na deszcz</button></div>' : ''}<div class="tip">${I.bulb}<p><b>Wskazówka:</b> ${esc(tipFor(d, p))}</p></div>`}</div>`,
    mapa: () => `<div class="dmap big" id="dm"></div><div class="wbody">${st.map((s, i) => `<div class="kv"><span><b>${i + 1}.</b> ${esc(s.name)}</span><a href="${url(s.map)}" target="_blank" rel="noopener">Nawiguj</a></div>`).join('')}<p class="hint">Linia pokazuje kolejność, nie dokładną drogę pieszą.</p></div>`,
    atr: () => `<div class="wbody">${st.map((s) => `<div class="acard">${stopSrc(s, 700) ? IMG(stopSrc(s, 700), s.name) : ''}<h3>${esc(s.name)}</h3><p class="mute">${esc(s.type)}, około ${dur(s.min)}</p>${s.info ? `<p>${esc(s.info)}</p><p class="mute" style="font-size:12px">Opis: Wikipedia</p>` : ''}${s.web ? `<a href="${url(s.web)}" target="_blank" rel="noopener">Godziny i bilety</a>` : ''}</div>`).join('') || '<p class="mute">Na ten dzień nie ma atrakcji.</p>'}</div>`,
    gas: () => { const m = d.stops.filter((s) => s.meal); return `<div class="wbody">${m.map((s) => `<h3 class="gh">${s.meal === 'lunch' ? 'Obiad' : 'Kolacja'}, ${s.time}</h3>${(s.options || []).map((r) => `<div class="kv"><span><b>${esc(r.name)}</b><br><small class="mute">${esc(r.cuisine)}</small></span><a href="${url(r.map)}" target="_blank" rel="noopener">Mapa</a></div>`).join('') || '<p class="mute">Brak lokali w bazie dla tej okolicy.</p>'}<a class="sm" href="${url(s.mapSearch)}" target="_blank" rel="noopener">Więcej restauracji i ich oceny</a>`).join('') || '<p class="mute">Na ten dzień nie planujemy posiłków na mieście.</p>'}</div>`; },
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
  const el = $('#dm'); if (el) drawMap(el, st.filter((s) => s.lat != null), { drag: S.dayTab === 'mapa' });
  app.scrollTop = 0;
}
function icsDay(d) {
  const fmt = (day, t) => day.replace(/-/g, '') + 'T' + t.replace(':', '') + '00';
  const ev = dayStops(d).filter((s) => s.time).map((s, i) => { const [h, m] = s.time.split(':').map(Number); const e = h * 60 + m + s.min; return `BEGIN:VEVENT\r\nUID:gt-${d.date}-${i}@globtroter\r\nDTSTAMP:${fmt(d.date, '00:00')}Z\r\nDTSTART:${fmt(d.date, s.time)}\r\nDTEND:${fmt(d.date, `${String(Math.floor(e / 60) % 24).padStart(2, '0')}:${String(e % 60).padStart(2, '0')}`)}\r\nSUMMARY:${s.name.replace(/[,;]/g, ' ')}\r\nEND:VEVENT`; }).join('\r\n');
  const b = new Blob([`BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Globtroter//PL\r\n${ev}\r\nEND:VCALENDAR\r\n`], { type: 'text/calendar' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `dzien-${d.date}.ics`; a.click();
}
function viewTripMap() {
  const p = S.plan; const pts = p.days.flatMap(dayStops).filter((s) => s.lat != null);
  app.innerHTML = `${planHead(p, { t: `Mapa – ${p.dest.name.replace(/\s*\(.*/, '')}`, s: `${pts.length} miejsc w planie` })}<div class="dmap full" id="dm"></div>${planNav('m')}`;
  $('#b').onclick = () => { S.tab = 'sum'; viewPlan(); }; bindPlanNav();
  drawMap($('#dm'), pts, { drag: true });
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
const LV = initLive({ S, app, $, $$, esc, url, zl, toast, api, load, save, I, IMG, commons, dateL, dur, ICON, planHead, planNav, bindPlanNav, API_LINK: location.origin + location.pathname, viewPlan, viewDay, viewDocs });

(async function boot() {
  try { await data(); } catch { toast('Nie udało się wczytać bazy miejsc. Sprawdź internet.'); }
  viewHome();
  const lk = new URLSearchParams(location.hash.slice(1)).get('t');
  if (lk) { history.replaceState(null, '', location.pathname); if (await LV.openLink(lk)) { viewPlan(); startUpdates(); return; } }
  LV.linkPush();
  const job = load('job', null);
  if (job && Date.now() - job.t < 3e6) { S.q = job.q; viewSearch(job.id); }
  startUpdates();
  window.__gt = { S, viewResults, viewOption, viewPlan, viewDay, viewTrips, viewInspire, viewProfile, viewHome, VERSION };
})();
