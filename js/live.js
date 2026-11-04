// Wyjazd po wybraniu: edycja planu, wspolny dostep, wydatki, skarbiec, pakowanie, atrakcje, powiadomienia, asystent.
// Na gorze czyste funkcje (testy w Node), nizej widoki podlaczane przez initLive.
export const CATS = [['trans', 'Transport'], ['stay', 'Noclegi'], ['food', 'Wyżywienie'], ['fun', 'Atrakcje'], ['local', 'Transport lokalny'], ['shop', 'Zakupy'], ['other', 'Pozostałe']];
export const emptyS = () => ({ exp: {}, vault: {}, pack: {}, ck: {}, days: {}, meta: {} });
export function mergeS(a, b) {
  const r = emptyS();
  for (const k of Object.keys(r)) {
    r[k] = { ...(a?.[k] || {}) };
    for (const [id, it] of Object.entries(b?.[k] || {})) if (!r[k][id] || it.u >= r[k][id].u) r[k][id] = it;
  }
  return r;
}
export function settle(list, people) {
  // Kto komu oddaje: najmniej przelewow, kwoty w zlotych
  const bal = people.map(() => 0);
  list.forEach((e) => {
    const f = e.for?.length ? e.for.filter((i) => i < people.length) : people.map((_, i) => i);
    if (!f.length || !(e.by < people.length)) return;
    bal[e.by] += e.pln; f.forEach((i) => { bal[i] -= e.pln / f.length; });
  });
  const P = bal.map((v, i) => [v, i]).filter((x) => x[0] > 0.5).sort((a, b) => b[0] - a[0]);
  const N = bal.map((v, i) => [-v, i]).filter((x) => x[0] > 0.5).sort((a, b) => b[0] - a[0]);
  const out = []; let i = 0; let j = 0;
  while (i < P.length && j < N.length) {
    const m = Math.min(P[i][0], N[j][0]);
    out.push({ from: N[j][1], to: P[i][1], pln: Math.round(m) });
    P[i][0] -= m; N[j][0] -= m;
    if (P[i][0] < 0.5) i++;
    if (N[j][0] < 0.5) j++;
  }
  return { bal: bal.map(Math.round), out };
}
const dist = (a, b) => { const p = Math.PI / 180; const x = Math.sin((b.lat - a.lat) * p / 2) ** 2 + Math.cos(a.lat * p) * Math.cos(b.lat * p) * Math.sin((b.lon - a.lon) * p / 2) ** 2; return 12742 * Math.asin(Math.sqrt(x)); };
const hm = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
export function retime(stops, start) {
  // Godziny po zmianie kolejnosci: czas na miejscu plus dojscie
  let cur = null;
  const first = start || stops[0]?.time || '09:30';
  const [h, m] = first.split(':').map(Number); cur = h * 60 + m;
  stops.forEach((s, i) => {
    const prev = stops[i - 1];
    if (prev) {
      const w = prev.lat != null && s.lat != null ? Math.min(45, Math.round(dist(prev, s) / 4.5 * 60)) : 10;
      cur += (prev.min || 30) + w;
    }
    s.time = hm(cur);
  });
  return stops;
}
export function packList(p) {
  const c = p.climate || {}; const t = c.tmax; const n = p.option.nights; const L = [];
  const add = (id, t2) => L.push({ id: 'g:' + id, t: t2 });
  add('doc', p.country?.docs ? `${p.country.docs}` : 'Dokument tożsamości'); add('pay', 'Portfel, karty, trochę gotówki'); add('tel', 'Ładowarka i powerbank'); add('med', 'Leki, które bierzesz na stałe');
  add('und', `Bielizna i skarpety: ${Math.min(n + 1, 7)} kompletów`); add('tsh', `Koszulki: ${Math.min(n, 6)}`); add('shoe', 'Wygodne buty do chodzenia'); add('hyg', 'Kosmetyczka, płyny do 100 ml w bagażu podręcznym');
  if (t != null && t >= 24) { add('sun', 'Krem z filtrem'); add('glass', 'Okulary przeciwsłoneczne'); add('hat', 'Czapka albo kapelusz'); }
  if (t != null && t < 15) { add('jack', 'Ciepła kurtka'); add('sw', 'Bluza albo sweter'); }
  if (t != null && t >= 15 && t < 24) add('lay', 'Lekka kurtka na wieczór');
  if (c.sea != null && c.sea >= 18) { add('swim', 'Strój kąpielowy'); add('tow', 'Ręcznik plażowy'); add('flip', 'Klapki'); }
  if (c.rain != null && c.rain >= 60) add('rain', 'Parasol albo kurtka przeciwdeszczowa');
  if (p.country && !p.country.plugs.includes('C')) add('plug', `Adapter do gniazdek ${p.country.plugs}`);
  if (p.option.pax?.children) add('kid', 'Rzeczy dla dziecka: przekąski, zabawka, ulubiony kocyk');
  return L;
}

export function shortest(stops, start) {
  // Najkrotsza kolejnosc pieszo: najblizszy sasiad od hotelu. Posilki i punkty bez mapy zostaja na swoich miejscach.
  const moving = stops.filter((s) => !s.meal && s.lat != null); const out = []; let cur = start; const left = [...moving];
  while (left.length) { let b = 0; left.forEach((s, i) => { if (dist(cur, s) < dist(cur, left[b])) b = i; }); cur = left.splice(b, 1)[0]; out.push(cur); }
  let i = 0;
  return stops.map((s) => (!s.meal && s.lat != null ? out[i++] : s));
}
export function swapDay(days, i) {
  // Deszczowy dzien z atrakcjami na zewnatrz: wskazuje suchy dzien do zamiany
  const OUT = new Set(['park', 'nature', 'beach', 'ruins', 'zoo', 'street', 'square', 'bridge', 'monument']);
  const d = days[i]; if ((d.weather?.rain ?? 0) < 60 || !d.stops.some((s) => OUT.has(s.kind))) return -1;
  return days.findIndex((y, j) => j !== i && y.kind === 'full' && y.weather && (y.weather.rain ?? 100) < 30);
}
export function initLive(x) {
  const { S, app, $, $$, esc, url, zl, toast, api, load, save, I, IMG, commons, dateL, dur, ICON, planHead, planNav, bindPlanNav, API_LINK } = x;
  const rid = () => Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
  const device = () => { let d = load('device', null); if (!d) { d = rid() + rid(); save('device', d); } return d; };
  const L = (p = S.plan) => { p.live ||= { s: emptyS(), dirty: emptyS(), rev: 0, role: 'edit', own: true }; p.live.dirty ||= emptyS(); return p.live; };
  const canEdit = (p = S.plan) => L(p).role !== 'view';
  const alive = (o) => Object.values(o || {}).filter((v) => !v.x);
  function applyDays(p) {
    const l = L(p); const o = l.s.days; p.days.forEach((d) => { if (o[d.date]) d.stops = o[d.date].stops; });
    const h = l.s.meta.hotel?.hotel;
    if (h) { p.hotel = h; if (h.bestTotal) { p.cost = [...p.cost.filter((c) => !c.label.startsWith('Nocleg')), { label: `Nocleg: ${h.name}`, pln: h.bestTotal, sure: 'est' }]; p.total = p.cost.reduce((n, c) => n + c.pln, 0); } }
  }
  function savePlan(p = S.plan) {
    const c = { ...p, option: { ...p.option, calendar: [], alternatives: [], compare: undefined } };
    const t = load('trips', []).filter((y) => y.option.id !== p.option.id); t.unshift(c);
    if (!save('trips', t.slice(0, 12))) toast('Telefon nie pozwolił zapisać planu offline.');
  }
  const people = (p = S.plan) => L(p).s.meta.people?.list || Array.from({ length: p.option.pax.adults + p.option.pax.children }, (_, i) => (i ? `Osoba ${i + 1}` : 'Ty'));
  const meIdx = (p = S.plan) => load('me.' + p.option.id, 0);
  const meName = (p = S.plan) => people(p)[meIdx(p)] || 'Ktoś';
  function scrub(p) {
    const lab = p.home?.label; let j = { ...p, live: undefined, home: { label: 'Dom' }, option: { ...p.option, calendar: [], alternatives: [], compare: undefined } };
    j = JSON.parse(lab ? JSON.stringify(j).split(lab).join('Dom') : JSON.stringify(j));
    if (j.timeline?.[0]) delete j.timeline[0].map;
    return j;
  }
  async function ensureRemote(p = S.plan) {
    const l = L(p); if (l.k) return l.k;
    if (ensureRemote.busy) return null;
    ensureRemote.busy = true;
    try {
      const r = await api('/api/trip/new', { plan: scrub(p), s: l.s });
      l.k = r.edit; l.view = r.view; l.rev = r.rev; savePlan(p); linkPush(); if (Object.values(l.dirty).some((v) => Object.keys(v).length)) syncNow(p).catch(() => {});
      return l.k;
    } finally { ensureRemote.busy = false; }
  }
  let timer = null; let note = null;
  function put(sec, id, item, n, p = S.plan) {
    const l = L(p); const it = { ...item, u: Date.now() }; l.s[sec][id] = it; l.dirty[sec][id] = it; savePlan(p);
    if (n) note = n;
    clearTimeout(timer); timer = setTimeout(() => syncNow(p).catch(() => {}), 700);
  }
  async function syncNow(p = S.plan, redraw) {
    if (!p) return; const l = L(p);
    if (!l.k) { if (l.role === 'view') return; await ensureRemote(p); }
    if (!l.k) return;
    const sent = JSON.stringify(l.dirty); const n = note; note = null;
    const r = await api('/api/trip/sync', { k: l.k, s: l.role === 'view' ? undefined : l.dirty, device: device(), note: n });
    const fresh = r.rev !== l.rev;
    l.rev = r.rev; l.role = r.role;
    if (JSON.stringify(l.dirty) === sent) l.dirty = emptyS();
    l.s = mergeS(r.s, l.dirty); applyDays(p); savePlan(p);
    if (fresh && redraw && !document.activeElement?.matches('input,textarea,select')) redraw();
  }
  async function openLink(k) {
    try {
      const r = await api('/api/trip?k=' + encodeURIComponent(k));
      const p = r.plan; p.live = { k, view: r.view, role: r.role, rev: r.rev, s: mergeS(emptyS(), r.s), dirty: emptyS(), own: false };
      const had = load('trips', []).find((t) => t.option.id === p.option.id);
      if (had?.live?.own) { p.live.own = true; p.home = had.home; }
      applyDays(p); S.plan = p; savePlan(p); S.tab = 'sum'; linkPush();
      toast(r.role === 'edit' ? 'Dołączono do wspólnego wyjazdu.' : 'Podgląd wyjazdu.');
      return true;
    } catch (e) { toast(e.message); return false; }
  }
  /* ---------- Udostepnianie ---------- */
  const pageUrl = (k) => `${API_LINK}#t=${k}`;
  async function viewShare() {
    const p = S.plan; const l = L(p); const back = () => { S.tab = 'sum'; x.viewPlan(); };
    if (!l.k && l.role !== 'view') { try { await ensureRemote(p); } catch (e) { toast(e.message); } }
    const row = (t, d, id) => `<div class="wcard"><h3>${t}</h3><p class="mute">${d}</p><div class="acts"><button class="btn small" id="${id}">Wyślij link</button></div></div>`;
    app.innerHTML = `${planHead(p, { t: 'Wspólny wyjazd', s: p.dest.name })}<section class="dbody"><div class="wbody">
      ${l.k && l.role === 'edit' ? row('Planujcie razem', 'Ta osoba zobaczy plan, wydatki i rezerwacje, i będzie mogła je zmieniać. Link działa też na Twoim drugim telefonie.', 'se') : ''}
      ${l.view ? row('Tylko do oglądania', 'Ta osoba zobaczy cały plan, ale niczego nie zmieni.', 'sv') : ''}
      ${!l.k ? '<p class="warn">Bez internetu nie da się utworzyć linku. Spróbuj, gdy wrócisz do sieci.</p>' : ''}
      <p class="hint">Każdy, kto ma link, ma dostęp, więc wysyłaj go tylko swoim ludziom. Twój adres domowy nie jest w linku.</p>
      <div class="kv"><span>Na tym telefonie jestem</span><span><select id="who">${people(p).map((n, i) => `<option value="${i}" ${i === meIdx(p) ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></span></div>
      </div></section>${planNav('p')}`;
    $('#b').onclick = back; bindPlanNav();
    $('#who').onchange = (e) => save('me.' + p.option.id, +e.target.value);
    const send = (k, t) => { const u = pageUrl(k); if (navigator.share) navigator.share({ title: `Wyjazd: ${p.dest.name}`, text: t, url: u }).catch(() => {}); else navigator.clipboard?.writeText(u).then(() => toast('Link skopiowany.')); };
    const a = $('#se'); if (a) a.onclick = () => send(l.k, 'Planujmy razem wyjazd:');
    const b = $('#sv'); if (b) b.onclick = () => send(l.view, 'Plan wyjazdu:');
  }
  /* ---------- Edycja dnia ---------- */
  const stopOf = (a) => ({ time: '', name: a.name, type: a.type, kind: a.kind, min: a.min, lat: a.lat, lon: a.lon, img: a.img, web: a.web, info: a.info, map: a.map, q: a.q, hours: a.hours });
  function dayChanged(i, n, p = S.plan) { const d = p.days[i]; put('days', d.date, { stops: d.stops }, n === undefined ? `${meName(p)} zmienia plan na ${dateL(d.date)}` : n, p); }
  function editHtml(d) {
    const p = S.plan;
    return `<div class="acts"><button class="btn line small" id="sho">Ułóż najkrótszą kolejność</button></div><div class="edl">${d.stops.map((s, i) => `<div class="ed"><div class="edh"><b>${esc(s.meal ? (s.meal === 'lunch' ? 'Obiad' : 'Kolacja') + (s.options?.[0] ? `: ${s.options[0].name}` : '') : s.name)}</b><small>${s.time}, około ${dur(s.min || 30)}</small></div>
      <div class="edb"><button data-up="${i}" aria-label="Wyżej" ${i ? '' : 'disabled'}>↑</button><button data-dw="${i}" aria-label="Niżej" ${i < d.stops.length - 1 ? '' : 'disabled'}>↓</button><select data-mv="${i}" aria-label="Przenieś na dzień"><option value="">Przenieś</option>${p.days.map((y, j) => (y === d ? '' : `<option value="${j}">Dzień ${j + 1}</option>`)).join('')}</select><button data-rm="${i}" aria-label="Usuń">✕</button></div>
      <input data-nt="${i}" placeholder="Twoja notatka" maxlength="200" value="${esc(s.note || '')}"></div>`).join('') || '<p class="mute">Ten dzień jest pusty.</p>'}</div>
      <label class="lab" for="st0" style="margin-top:12px">Pierwszy punkt o godzinie</label><input id="st0" type="time" value="${esc(d.stops[0]?.time || '09:30')}">
      <div class="acts"><button class="btn line small" id="cus">Dodaj własny punkt</button><button class="btn small" id="edok">Gotowe</button></div>`;
  }
  function bindDay(redraw) {
    const p = S.plan; const i = S.day; const d = p.days[i];
    const ch = () => { retime(d.stops); dayChanged(i); redraw(); };
    const mv = (a, b) => { const t = d.stops[a]; d.stops[a] = d.stops[b]; d.stops[b] = t; ch(); };
    $$('[data-up]').forEach((b) => { b.onclick = () => mv(+b.dataset.up, +b.dataset.up - 1); });
    $$('[data-dw]').forEach((b) => { b.onclick = () => mv(+b.dataset.dw, +b.dataset.dw + 1); });
    $$('[data-rm]').forEach((b) => { b.onclick = () => { d.stops.splice(+b.dataset.rm, 1); ch(); }; });
    $$('[data-mv]').forEach((b) => { b.onchange = () => { if (b.value === '') return; const j = +b.value; const [s] = d.stops.splice(+b.dataset.mv, 1); p.days[j].stops.push(s); retime(p.days[j].stops); dayChanged(j, null); ch(); }; });
    $$('[data-nt]').forEach((b) => { b.onchange = () => { d.stops[+b.dataset.nt].note = b.value.trim(); dayChanged(i, null); }; });
    $$('[data-dn]').forEach((b) => { b.onclick = (e) => { e.preventDefault(); if (!canEdit()) return; const s = d.stops[+b.dataset.dn]; s.done = !s.done; dayChanged(i, null); redraw(); }; });
    const a = $('#st0'); if (a) a.onchange = () => { if (a.value) { retime(d.stops, a.value); dayChanged(i, null); redraw(); } };
    const c = $('#cus'); if (c) c.onclick = () => { const n = prompt('Co chcesz dodać?'); if (n?.trim()) { d.stops.push({ time: '', name: n.trim().slice(0, 80), type: 'Własny punkt', kind: 'own', min: 60, map: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(n + ' ' + p.dest.name)}` }); ch(); } };
    const sh = $('#sho'); if (sh) sh.onclick = () => { d.stops = shortest(d.stops, p.hotel); ch(); toast('Kolejność ułożona od hotelu.'); };
    const sw = $('#swp'); if (sw) sw.onclick = () => { const j = +sw.dataset.j; const y = p.days[j]; const t = d.stops; d.stops = y.stops; y.stops = t; retime(d.stops, '09:30'); retime(y.stops, '09:30'); dayChanged(j, null); dayChanged(i); toast(`Zamienione z dniem ${j + 1}.`); redraw(); };
    const o = $('#edok'); if (o) o.onclick = () => { S.edit = false; redraw(); };
    const e = $('#ed'); if (e) e.onclick = () => { S.edit = true; redraw(); };
    const add = $('#addS'); if (add) add.onclick = () => viewExplore({ day: i });
    const pb = $('#planb'); if (pb) pb.onclick = () => viewExplore({ day: i, indoor: true });
  }
  /* ---------- Atrakcje i restauracje ---------- */
  const GROUPS = [['all', 'Wszystko', null], ['indoor', 'Pod dachem', null], ['sight', 'Zabytki', ['sight', 'monument', 'ruins', 'castle', 'palace', 'bridge', 'square', 'street']], ['museum', 'Muzea', ['museum']], ['church', 'Świątynie', ['church']], ['green', 'Parki i natura', ['park', 'nature']], ['beach', 'Plaże', ['beach']], ['family', 'Dla rodzin', ['zoo', 'park', 'beach']], ['show', 'Teatry', ['theatre']], ['market', 'Targi', ['food']]];
  async function explore(id) {
    S.ex ||= {};
    if (!S.ex[id]) S.ex[id] = await api('/api/explore?dest=' + encodeURIComponent(id));
    return S.ex[id];
  }
  async function viewExplore(o = {}) {
    const p = S.plan; const st = S.exS = { tab: 'a', g: o.indoor ? 'indoor' : 'all', q: '', c: '', day: o.day ?? 0 };
    app.innerHTML = `${planHead(p, { t: 'Odkrywaj', s: p.dest.name })}<section class="dbody"><div class="wbody"><p class="mute">Wczytuję miejsca…</p></div></section>${planNav('m')}`;
    $('#b').onclick = () => { S.dayTab = 'plan'; x.viewDay(); }; bindPlanNav();
    if (p.dest.id.startsWith('x-')) { $('.wbody').innerHTML = '<p class="mute">Dla tego miejsca nie mamy listy atrakcji. Własne punkty dodasz w Zmień plan.</p>'; return; }
    let D; try { D = await explore(p.dest.id); } catch (e) { $('.wbody').innerHTML = `<p class="warn">${esc(e.message)}</p>`; return; }
    const cuis = [...new Set(D.restaurants.flatMap((r) => r.cuisine.split(/[;,]/).map((c) => c.trim()).filter(Boolean)))].slice(0, 14);
    const draw = () => {
      const q = st.q.toLowerCase();
      const A = D.attractions.filter((a) => (st.g === 'all' || (st.g === 'indoor' ? a.indoor : GROUPS.find((g) => g[0] === st.g)[2].includes(a.kind))) && (!q || a.name.toLowerCase().includes(q))).slice(0, 40);
      const R = D.restaurants.filter((r) => (!st.c || r.cuisine.includes(st.c)) && (!q || r.name.toLowerCase().includes(q))).slice(0, 40);
      const canAdd = canEdit();
      const list = st.tab === 'a' ? (A.map((a, i) => `<div class="acard">${a.img ? IMG(commons(a.img, 700), a.name) : ''}<h3>${esc(a.name)}</h3><p class="mute">${esc(a.type)}, około ${dur(a.min)}${a.indoor ? ', pod dachem' : ''}</p>${a.info ? `<p>${esc(a.info)}</p>${a.infoEn ? '<p class="mute" style="font-size:12px">Opis po angielsku, Wikivoyage</p>' : ''}` : ''}${a.hours ? `<p class="mute">Godziny wg OpenStreetMap: ${esc(a.hours)}. Sprawdź przed wyjściem.</p>` : ''}<div class="linkset">${a.web ? `<a class="btn line small" href="${url(a.web)}" target="_blank" rel="noopener">Strona</a>` : ''}<a class="btn line small" href="${url(a.map)}" target="_blank" rel="noopener">Mapa</a>${canAdd ? `<button class="btn small" data-aa="${i}">Dodaj do dnia ${st.day + 1}</button>` : ''}</div></div>`).join('') || '<p class="mute">Nic nie pasuje do tego filtra.</p>')
        : (R.map((r, i) => `<div class="acard"><h3>${esc(r.name)}</h3><p class="mute">${esc(r.cuisine || 'kuchnia nieopisana')}</p>${r.hours ? `<p class="mute">Godziny wg OpenStreetMap: ${esc(r.hours)}</p>` : ''}<div class="linkset"><a class="btn line small" href="${url(r.map)}" target="_blank" rel="noopener">Mapa i oceny</a>${r.web ? `<a class="btn line small" href="${url(r.web)}" target="_blank" rel="noopener">Strona</a>` : ''}${canAdd ? `<button class="btn small" data-ar="${i}">Dodaj do dnia ${st.day + 1}</button>` : ''}</div></div>`).join('') || `<p class="mute">${D.restaurants.length ? 'Nic nie pasuje do tego filtra.' : 'Dla tego miasta nie mamy jeszcze listy restauracji.'}</p>`);
      $('#exl').innerHTML = list;
      $('#exf').innerHTML = st.tab === 'a' ? GROUPS.filter((g) => g[0] === 'all' || g[0] === 'indoor' || D.attractions.some((a) => g[2].includes(a.kind))).map((g) => `<button class="chip" data-g="${g[0]}" aria-pressed="${st.g === g[0]}">${g[1]}</button>`).join('') : [['', 'Każda kuchnia'], ...cuis.map((c) => [c, c])].map(([k, l]) => `<button class="chip" data-c="${esc(k)}" aria-pressed="${st.c === k}">${esc(l)}</button>`).join('');
      $$('[data-g]').forEach((b) => { b.onclick = () => { st.g = b.dataset.g; draw(); }; });
      $$('[data-c]').forEach((b) => { b.onclick = () => { st.c = b.dataset.c; draw(); }; });
      $$('[data-aa]').forEach((b) => { b.onclick = () => { const d = p.days[st.day]; d.stops.push(stopOf(A[+b.dataset.aa])); retime(d.stops); dayChanged(st.day); toast(`Dodano do dnia ${st.day + 1}.`); }; });
      $$('[data-ar]').forEach((b) => { b.onclick = () => { const r = R[+b.dataset.ar]; const d = p.days[st.day]; const free = d.stops.find((s) => s.meal && !s.picked); const opt = { name: r.name, cuisine: r.cuisine, hours: r.hours, web: r.web, map: r.map }; if (free) { free.options = [opt, ...(free.options || [])]; free.picked = true; } else { d.stops.push({ meal: d.stops.some((s) => s.meal === 'lunch') ? 'dinner' : 'lunch', time: '', lat: r.lat, lon: r.lon, min: 60, options: [opt], picked: true, mapSearch: r.map }); retime(d.stops); } dayChanged(st.day); toast(`Dodano do dnia ${st.day + 1}.`); }; });
    };
    $('.wbody').innerHTML = `<div class="seg" id="ext"><button data-t2="a" aria-pressed="true">Atrakcje (${D.attractions.length})</button><button data-t2="r" aria-pressed="false">Restauracje (${D.restaurants.length})</button></div>
      <input id="exq" placeholder="Szukaj po nazwie" aria-label="Szukaj"><label class="lab" for="exd" style="margin:0">Dodawaj do</label><select id="exd">${p.days.map((d, i) => `<option value="${i}" ${i === st.day ? 'selected' : ''}>Dzień ${i + 1}, ${dateL(d.date)}</option>`).join('')}</select><div class="chips" id="exf"></div><div id="exl" style="display:grid;gap:10px"></div>`;
    $$('[data-t2]').forEach((b) => { b.onclick = () => { st.tab = b.dataset.t2; $$('[data-t2]').forEach((y) => y.setAttribute('aria-pressed', y === b)); draw(); }; });
    $('#exq').oninput = (e) => { st.q = e.target.value; draw(); };
    $('#exd').onchange = (e) => { st.day = +e.target.value; S.day = st.day; draw(); };
    draw();
  }
  /* ---------- Budzet ---------- */
  function budgetHtml(p) {
    const l = L(p); const E = alive(l.s.exp).sort((a, b) => (b.date || '').localeCompare(a.date || '') || b.u - a.u);
    const spent = E.reduce((n, e) => n + e.pln, 0); const limit = l.s.meta.limit?.v ?? p.total; const left = limit - spent;
    const P = people(p); const st = settle(E, P);
    const byCat = CATS.map(([k, n]) => [n, E.filter((e) => e.cat === k).reduce((a, e) => a + e.pln, 0)]).filter((c) => c[1] > 0); const mx = Math.max(1, ...byCat.map((c) => c[1]));
    return `<div class="wcard"><h3>Wydatki w trakcie</h3><div class="sum3"><div><small>Budżet</small><b>${zl(limit)}</b></div><div><small>Wydane</small><b>${zl(spent)}</b></div><div><small>${left < 0 ? 'Ponad budżet' : 'Zostało'}</small><b class="${left < 0 ? 'neg' : ''}">${zl(Math.abs(left))}</b></div></div>
      ${left < 0 ? '<p class="warn">Budżet przekroczony.</p>' : ''}
      ${byCat.map(([n, v]) => `<div class="cost"><div class="kv"><span>${esc(n)}</span><span>${zl(v)}</span></div><i style="width:${(v / mx) * 100}%"></i></div>`).join('')}
      ${canEdit() ? '<div class="acts"><button class="btn small" id="xadd">Dodaj wydatek</button><button class="btn line small" id="xlim">Zmień budżet</button></div>' : ''}</div>
      ${chartsHtml(p, E)}
      <div class="wcard"><h3>Rozliczenie</h3>${st.out.length ? st.out.map((t) => `<div class="kv"><span>${esc(P[t.from])} → ${esc(P[t.to])}</span><b>${zl(t.pln)}</b></div>`).join('') : '<p class="mute">Na razie wszyscy są kwita.</p>'}
      <p class="mute" style="margin-top:8px">Uczestnicy: ${P.map(esc).join(', ')}</p>${canEdit() ? '<div class="acts"><button class="btn line small" id="xppl">Zmień imiona</button></div>' : ''}</div>
      ${E.length ? `<div class="wcard"><h3>Lista wydatków</h3>${E.map((e) => `<button class="kvb" data-xe="${e.id}"><span>${esc(e.title)}<small class="mute" style="display:block">${dateL(e.date)}, płacił(a) ${esc(P[e.by] || '?')}</small></span><b>${zl(e.pln)}${e.cur !== 'PLN' ? `<small class="mute" style="display:block;font-weight:500">${e.amount} ${esc(e.cur)}</small>` : ''}</b></button>`).join('')}</div>` : ''}`;
  }
  function chartsHtml(p, E) {
    if (!E.length) return '';
    const days = {}; E.forEach((e) => { days[e.date] = (days[e.date] || 0) + e.pln; });
    const K = Object.keys(days).sort(); const mx = Math.max(...Object.values(days));
    const avg = Math.round(E.reduce((n, e) => n + e.pln, 0) / K.length);
    const planOf = (re) => (p.cost || []).filter((c) => re.test(c.label)).reduce((n, c) => n + c.pln, 0);
    const rows = [['Transport', planOf(/Bilety|Paliwo|Parking|Autostrady|Bagaż|Transport/), 'trans'], ['Noclegi', planOf(/^Nocleg/), 'stay']].map(([n, pl, c]) => [n, pl, E.filter((e) => e.cat === c).reduce((a, e) => a + e.pln, 0)]).filter((r) => r[1] || r[2]);
    const m2 = Math.max(1, ...rows.flatMap((r) => [r[1], r[2]]));
    return `<div class="wcard"><h3>Wydatki dzień po dniu</h3><p class="mute">Średnio ${zl(avg)} dziennie</p><div class="vbars" role="img" aria-label="Wydatki w kolejnych dniach">${K.map((k) => `<div title="${dateL(k)}: ${zl(days[k])}"><b>${Math.round(days[k])}</b><i style="height:${Math.max(4, (days[k] / mx) * 100)}%"></i><small>${k.slice(8)}.${k.slice(5, 7)}</small></div>`).join('')}</div></div>
    ${rows.length ? `<div class="wcard"><h3>Plan i rzeczywistość</h3>${rows.map(([n, pl, re]) => `<div class="pvr"><span>${n}</span><div><i class="pl" style="width:${(pl / m2) * 100}%"></i><em>plan ${zl(pl)}</em></div><div><i class="re" style="width:${(re / m2) * 100}%"></i><em>wydane ${zl(re)}</em></div></div>`).join('')}</div>` : ''}`;
  }
  function bindBudget(p) {
    const a = $('#xadd'); if (a) a.onclick = () => viewExpense();
    const b = $('#xlim'); if (b) b.onclick = () => { const v = prompt('Budżet całego wyjazdu w złotych', Math.round(L(p).s.meta.limit?.v ?? p.total)); if (v != null && +v > 0) { put('meta', 'limit', { v: Math.round(+v) }); x.viewPlan(); } };
    const c = $('#xppl'); if (c) c.onclick = () => { const v = prompt('Imiona po przecinku', people(p).join(', ')); if (v) { const list = v.split(',').map((n) => n.trim().slice(0, 24)).filter(Boolean).slice(0, 12); if (list.length) { put('meta', 'people', { list }); x.viewPlan(); } } };
    $$('[data-xe]').forEach((e) => { e.onclick = () => canEdit() && viewExpense(e.dataset.xe); });
  }
  async function rateOf(cur, p) {
    if (cur === 'PLN') return 1;
    if (cur === p.country?.currency && p.country.rate) return p.country.rate;
    const c = load('fx', {}); if (c[cur]) return c[cur];
    try { const r = await api('/api/fx?c=' + cur); c[cur] = r.rate; save('fx', c); return r.rate; } catch { return null; }
  }
  async function viewExpense(id) {
    const p = S.plan; const l = L(p); const e = id ? l.s.exp[id] : null; const P = people(p);
    const curs = [...new Set(['PLN', p.country?.currency, 'EUR'].filter(Boolean))];
    const f = e ? { ...e } : { title: '', amount: '', cur: p.country?.currency && p.country.currency !== 'PLN' ? p.country.currency : 'PLN', cat: 'food', by: meIdx(p), for: P.map((_, i) => i), date: new Date().toISOString().slice(0, 10) };
    const draw = async () => {
      const r = await rateOf(f.cur, p);
      app.innerHTML = `${planHead(p, { t: e ? 'Wydatek' : 'Nowy wydatek', s: p.dest.name })}<section class="dbody"><div class="wbody">
      <label class="lab" for="et">Na co</label><input id="et" maxlength="80" value="${esc(f.title)}" placeholder="np. Kolacja, bilety do muzeum">
      <div class="grid2"><div><label class="lab" for="ea">Kwota</label><input id="ea" type="number" inputmode="decimal" step="0.01" min="0" value="${esc(f.amount)}"></div><div><label class="lab" for="ec">Waluta</label><select id="ec">${curs.map((c) => `<option ${c === f.cur ? 'selected' : ''}>${c}</option>`).join('')}</select></div></div>
      ${f.cur !== 'PLN' ? `<label class="lab" for="er">Kurs ${r ? '(NBP)' : '(wpisz sam, brak internetu)'}: 1 ${esc(f.cur)} w złotych</label><input id="er" type="number" inputmode="decimal" step="0.0001" value="${r ?? ''}">` : ''}
      <label class="lab" for="eg">Kategoria</label><select id="eg">${CATS.map(([k, n]) => `<option value="${k}" ${k === f.cat ? 'selected' : ''}>${n}</option>`).join('')}</select>
      <label class="lab" for="ed2">Dzień</label><input id="ed2" type="date" value="${esc(f.date)}">
      <label class="lab" for="eb">Kto płacił</label><select id="eb">${P.map((n, i) => `<option value="${i}" ${i === f.by ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select>
      <span class="lab">Dzielone na</span><div class="chips">${P.map((n, i) => `<button class="chip" data-fp="${i}" aria-pressed="${f.for.includes(i)}">${esc(n)}</button>`).join('')}</div>
      <div class="acts"><button class="btn" id="eok">Zapisz</button>${e ? '<button class="btn line small" id="edel">Usuń</button>' : ''}</div></div></section>${planNav('u')}`;
      const g = () => { f.title = $('#et').value; f.amount = $('#ea').value; f.cat = $('#eg').value; f.date = $('#ed2').value; f.by = +$('#eb').value; f.rate = $('#er') ? +$('#er').value : 1; };
      $('#b').onclick = () => { S.tab = 'bud'; x.viewPlan(); }; bindPlanNav();
      $('#ec').onchange = (v) => { g(); f.cur = v.target.value; draw(); };
      $$('[data-fp]').forEach((b) => { b.onclick = () => { g(); const i = +b.dataset.fp; f.for = f.for.includes(i) ? f.for.filter((y) => y !== i) : [...f.for, i]; draw(); }; });
      $('#eok').onclick = () => {
        g(); const am = +f.amount;
        if (!f.title.trim() || !(am > 0)) return toast('Wpisz nazwę i kwotę.');
        if (!f.for.length) return toast('Wybierz, na kogo dzielić.');
        if (f.cur !== 'PLN' && !(f.rate > 0)) return toast('Wpisz kurs waluty.');
        const nid = id || rid();
        put('exp', nid, { id: nid, title: f.title.trim(), amount: am, cur: f.cur, rate: f.rate, pln: Math.round(am * (f.cur === 'PLN' ? 1 : f.rate) * 100) / 100, cat: f.cat, by: f.by, for: f.for, date: f.date }, e ? null : `${meName(p)} dodaje wydatek: ${f.title.trim()}, ${am} ${f.cur}`);
        S.tab = 'bud'; x.viewPlan();
      };
      const d = $('#edel'); if (d) d.onclick = () => { put('exp', id, { x: 1, id }); S.tab = 'bud'; x.viewPlan(); };
    };
    draw();
  }
  /* ---------- Skarbiec i pakowanie ---------- */
  const VK = { res: 'Rezerwacja', tic: 'Bilet', adr: 'Adres', tel: 'Kontakt', not: 'Notatka' };
  function docsHtml(p) {
    const l = L(p); const V = alive(l.s.vault).sort((a, b) => a.u - b.u); const gen = packList(p); const own = alive(l.s.pack).filter((i) => i.own);
    const all = [...gen, ...own.map((i) => ({ id: i.id, t: i.t }))]; const done = all.filter((i) => l.s.pack[i.id]?.v).length;
    return `<h3 class="gh">Skarbiec wyjazdu</h3><p class="mute">Numery rezerwacji, adresy i telefony. Działa bez internetu. Nie wpisuj tu numerów dokumentów ani kart.</p>
      ${V.map((v) => `<div class="vault"><div><small class="mute">${esc(VK[v.kind] || 'Wpis')}</small><b>${esc(v.title)}</b>${v.code ? `<button class="code" data-cp="${esc(v.code)}">${esc(v.code)}</button>` : ''}${v.text ? `<p>${esc(v.text)}</p>` : ''}</div>${canEdit() ? `<button data-vd="${v.id}" aria-label="Usuń">✕</button>` : ''}</div>`).join('') || '<p class="mute">Jeszcze pusto.</p>'}
      ${canEdit() ? `<details class="add"><summary>Dodaj wpis</summary><select id="vk">${Object.entries(VK).map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select><input id="vt" maxlength="80" placeholder="Nazwa, np. Hotel Arts"><input id="vc" maxlength="80" placeholder="Numer rezerwacji albo telefon"><textarea id="vx" maxlength="500" rows="2" placeholder="Adres albo uwagi"></textarea><button class="btn small" id="vok">Zapisz</button></details>` : ''}
      <h3 class="gh">Lista pakowania <small class="mute">${done} z ${all.length}</small></h3><div class="checks">${all.map((i) => `<label><input type="checkbox" data-pk="${esc(i.id)}" ${l.s.pack[i.id]?.v ? 'checked' : ''} ${canEdit() ? '' : 'disabled'}><span>${esc(i.t)}</span></label>`).join('')}</div>
      ${canEdit() ? '<div class="addr"><input id="pa" maxlength="80" placeholder="Dodaj swoją rzecz"><button class="btn small" id="pok">Dodaj</button></div>' : ''}`;
  }
  function bindDocs(p) {
    const r = () => x.viewDocs();
    $$('[data-pk]').forEach((c) => { c.onchange = () => { const i = c.dataset.pk; const o = L(p).s.pack[i] || {}; put('pack', i, { ...o, id: i, v: c.checked }); }; });
    $$('[data-vd]').forEach((c) => { c.onclick = () => { put('vault', c.dataset.vd, { x: 1, id: c.dataset.vd }); r(); }; });
    $$('[data-cp]').forEach((c) => { c.onclick = () => navigator.clipboard?.writeText(c.dataset.cp).then(() => toast('Skopiowano.')); });
    const v = $('#vok'); if (v) v.onclick = () => { const t = $('#vt').value.trim(); if (!t) return toast('Wpisz nazwę.'); const id = rid(); put('vault', id, { id, kind: $('#vk').value, title: t, code: $('#vc').value.trim(), text: $('#vx').value.trim() }, `${meName(p)} dodaje do skarbca: ${t}`); r(); };
    const k = $('#pok'); if (k) k.onclick = () => { const t = $('#pa').value.trim(); if (!t) return; const id = 'c:' + rid(); put('pack', id, { id, t, own: 1, v: false }); r(); };
  }
  /* ---------- Powiadomienia ---------- */
  const b64 = (s) => { const raw = atob((s + '='.repeat((4 - (s.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')); return Uint8Array.from(raw, (c) => c.charCodeAt(0)); };
  const pushOK = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  const pushOn = () => !!load('push', false);
  const myKeys = () => load('trips', []).map((t) => t.live?.k).filter(Boolean);
  async function linkPush() {
    if (!pushOn() || !pushOK()) return;
    try { const r = await navigator.serviceWorker.ready; const sub = await r.pushManager.getSubscription(); if (sub) await api('/api/push/sub', { device: device(), subscription: sub.toJSON(), keys: myKeys() }); } catch { /* sprobuje przy nastepnym otwarciu */ }
  }
  async function pushEnable() {
    if (!pushOK()) throw new Error('Na iPhonie dodaj Globtrotera do ekranu początkowego i otwórz go stamtąd.');
    if (await Notification.requestPermission() !== 'granted') throw new Error('Zezwól na powiadomienia w ustawieniach telefonu.');
    for (const t of load('trips', [])) { if (!t.live?.k) { try { await ensureRemote(t); } catch { /* bez sieci */ } } }
    const { key } = await api('/api/push/key'); const r = await navigator.serviceWorker.ready;
    let sub = await r.pushManager.getSubscription();
    if (!sub) sub = await r.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) });
    await api('/api/push/sub', { device: device(), subscription: sub.toJSON(), keys: myKeys() }); save('push', true);
  }
  async function pushDisable() {
    try { const r = await navigator.serviceWorker.ready; const sub = await r.pushManager.getSubscription(); await sub?.unsubscribe(); await api('/api/push/off', { device: device() }); } catch { /* nic */ }
    save('push', false);
  }
  const pushHtml = () => `<div class="wcard"><h3>Powiadomienia</h3><p class="mute">Dochodzą z serwera, także przy zamkniętej aplikacji: zadania przed wyjazdem, dzień przed lotem, wyjazd z domu, plan na dziś, zmiany we wspólnym wyjeździe.</p><div class="acts"><button class="btn small" id="pu">${pushOn() ? 'Wyłącz' : 'Włącz powiadomienia'}</button>${pushOn() ? '<button class="btn line small" id="pt">Wyślij próbne</button>' : ''}</div></div>`;
  function bindPush(redraw) {
    $('#pu').onclick = async () => { try { if (pushOn()) await pushDisable(); else { await pushEnable(); toast('Powiadomienia włączone.'); } redraw(); } catch (e) { toast(e.message); } };
    const t = $('#pt'); if (t) t.onclick = async () => { try { await api('/api/push/test', { device: device() }); toast('Wysłane. Powinno dojść za chwilę.'); } catch (e) { toast(e.message); } };
  }
  /* ---------- Asystent ---------- */
  async function askSentence(text) {
    const r = await api('/api/ai/parse', { text }); const f = r.fields; const q = S.q; const did = [];
    if (f.destIds?.length) { q.dest = { mode: 'city', ids: f.destIds, countries: [], style: null }; did.push('cel'); } else if (f.countries?.length) { q.dest = { mode: 'country', ids: [], countries: f.countries, style: f.style || null }; did.push('kraj'); } else if (f.style) { q.dest = { mode: 'style', style: f.style, ids: [], countries: [] }; did.push('styl'); }
    if (f.month) { const n = new Date(); const y = f.month > n.getMonth() + 1 ? n.getFullYear() : n.getFullYear() + 1; q.when = { ...q.when, mode: 'month', month: f.month, year: y }; did.push('termin'); }
    if (f.nights) { q.when = { ...q.when, nights: [Math.min(30, f.nights)] }; did.push('długość'); }
    if (f.adults) { q.pax = { ...q.pax, adults: Math.min(9, f.adults) }; did.push('osoby'); }
    if (f.children != null) q.pax = { ...q.pax, children: Math.min(6, f.children) };
    if (f.budget) did.push('budżet na cały wyjazd');
    if (f.budget) { q.tripBudget = f.budget; q.stay = { ...q.stay, budget: Math.max(300, Math.round(f.budget * 0.45 / 50) * 50) }; }
    save('prefs', q);
    return did;
  }
  function tripContext(p) {
    const l = L(p); const E = alive(l.s.exp); const o = p.option;
    return { miejsce: p.dest.name, wylot: o.dep, powrot: o.ret, noce: o.nights, osoby: people(p), lotnisko: o.from, hotel: p.hotel?.name, sniadanie: p.hotel?.breakfast, kosztPlanowany: p.total, budzet: l.s.meta.limit?.v ?? p.total, wydane: E.reduce((n, e) => n + e.pln, 0), klimat: p.climate, days: p.days.map((d) => ({ date: d.date, pogoda: d.weather, nazwy: d.stops.filter((s) => s.name).map((s) => s.name), punkty: d.stops.map((s) => (s.meal ? `${s.meal}: ${s.options?.[0]?.name || 'bez wybranego lokalu'}` : `${s.time} ${s.name}`)) })) };
  }
  function viewAI() {
    const p = S.plan; S.ai ||= {}; const M = (S.ai[p.option.id] ||= []);
    const draw = () => {
      app.innerHTML = `${planHead(p, { t: 'Asystent', s: p.dest.name })}<section class="dbody"><div class="wbody chat"><p class="hint">Zna ten wyjazd. Ceny i godziny bierze tylko z danych aplikacji, a czego nie wie, to powie. Niczego nie rezerwuje.</p>
      ${M.map((m, i) => `<div class="msg ${m.me ? 'me' : ''}">${esc(m.t)}${m.actions?.length ? `<ul>${m.actions.map((a) => `<li>${a.op === 'add' ? `Dodaj: ${esc(a.name)} (${dateL(a.date)})` : a.op === 'remove' ? `Usuń: ${esc(a.name)} (${dateL(a.date)})` : `Przenieś: ${esc(a.name)} na ${dateL(a.to)}`}</li>`).join('')}</ul>${canEdit() && !m.used ? `<button class="btn small" data-app="${i}">Wprowadź te zmiany</button>` : ''}` : ''}</div>`).join('') || `<div class="chips">${['Co zmienić, żeby było taniej?', 'Ułóż lżejszy pierwszy dzień', 'Co robić, jeśli będzie padać?'].map((t) => `<button class="chip" data-sg="${esc(t)}">${esc(t)}</button>`).join('')}</div>`}
      ${S.aiBusy ? '<p class="mute">Myślę…</p>' : ''}<div class="addr"><input id="aq" maxlength="500" placeholder="Zapytaj o ten wyjazd"><button class="btn small" id="as">Wyślij</button></div></div></section>${planNav('p')}`;
      $('#b').onclick = () => { S.tab = 'sum'; x.viewPlan(); }; bindPlanNav();
      $('#as').onclick = () => go($('#aq').value);
      $$('[data-sg]').forEach((b) => { b.onclick = () => go(b.dataset.sg); });
      $$('[data-app]').forEach((b) => { b.onclick = () => apply(+b.dataset.app); });
      app.scrollTop = app.scrollHeight;
    };
    const go = async (t) => {
      t = t.trim(); if (!t || S.aiBusy) return; M.push({ me: 1, t }); S.aiBusy = true; draw();
      try { const r = await api('/api/ai/chat', { dest: p.dest.id, trip: tripContext(p), messages: M.map((m) => ({ me: m.me, t: m.t })) }); M.push({ t: r.reply, actions: r.actions }); } catch (e) { M.push({ t: e.message }); }
      S.aiBusy = false; draw();
    };
    const apply = async (i) => {
      const acts = M[i].actions; let D; try { D = await explore(p.dest.id); } catch (e) { return toast(e.message); }
      const touched = new Set();
      for (const a of acts) {
        const d = p.days.find((y) => y.date === a.date); if (!d) continue; const di = p.days.indexOf(d);
        const low = (a.name || '').replace(/^\d\d:\d\d\s+/, '').toLowerCase(); const idx = d.stops.findIndex((s) => s.name?.toLowerCase() === low);
        if (a.op === 'add') { const f = D.attractions.find((y) => y.name.toLowerCase() === low); if (f) { d.stops.push(stopOf(f)); touched.add(di); } }
        if (a.op === 'remove' && idx >= 0) { d.stops.splice(idx, 1); touched.add(di); }
        if (a.op === 'move' && idx >= 0) { const t = p.days.find((y) => y.date === a.to); if (t) { t.stops.push(d.stops.splice(idx, 1)[0]); touched.add(di); touched.add(p.days.indexOf(t)); } }
      }
      touched.forEach((di) => { retime(p.days[di].stops); dayChanged(di, null); });
      M[i].used = true; toast(touched.size ? 'Plan zmieniony.' : 'Nie znalazłem tych punktów w planie.'); draw();
    };
    draw();
  }
  /* ---------- Pogoda na zywo ---------- */
  async function refreshWeather(p) {
    const today = new Date().toISOString().slice(0, 10); const o = p.option;
    if (o.ret < today || (new Date(o.dep) - Date.now()) / 864e5 > 15) return false;
    const k = 'wx.' + o.id; if (Date.now() - load(k, 0) < 3 * 36e5) return false;
    try {
      const u = `https://api.open-meteo.com/v1/forecast?latitude=${p.dest.lat}&longitude=${p.dest.lon}&daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max,precipitation_probability_max,wind_speed_10m_max,cloud_cover_mean,weather_code&timezone=auto&forecast_days=16`;
      const r = await fetch(u); const j = (await r.json()).daily; if (!j?.time) return false;
      j.time.forEach((day, i) => { const d = p.days.find((y) => y.date === day); if (d) d.weather = { tmax: j.temperature_2m_max[i], tmin: j.temperature_2m_min[i], feels: j.apparent_temperature_max[i], rain: j.precipitation_probability_max[i], wind: j.wind_speed_10m_max[i], cloud: j.cloud_cover_mean[i], code: j.weather_code[i], kind: 'forecast' }; });
      save(k, Date.now()); savePlan(p); return true;
    } catch { return false; }
  }
  /* ---------- Wlasny wyjazd ---------- */
  function viewNew(pre = {}) {
    const f = S.newT ||= { dest: null, q: '', from: '', to: '', mode: 'car', arrive: '15:00', leave: '10:00', hotel: '', hotelCost: '', transportCost: '' };
    Object.assign(f, pre);
    const pick = (v) => { const d = S.dests.find((y) => y.name.toLowerCase() === v.trim().toLowerCase()); f.dest = d ? { id: d.id, name: d.name } : null; };
    const draw = () => {
      app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Własny wyjazd</h2></div><section class="page"><div class="wcard form2">
      <p class="mute">Gdy jedziesz autem, pociągiem albo masz już bilety. Dostaniesz plan dni, listy, budżet i wspólny dostęp.</p>
      <label class="lab" for="nq">Dokąd</label><input id="nq" list="ndl" value="${esc(f.dest?.name || f.q)}" placeholder="Miasto"><datalist id="ndl">${S.dests.map((d) => `<option value="${esc(d.name)}">`).join('')}</datalist>
      ${f.dest ? `<p class="hint">Wybrane: ${esc(f.dest.name)}</p>` : '<button class="btn line small" id="ngeo">Znajdź to miejsce</button><div id="ngl" style="display:grid;gap:6px"></div>'}
      <div class="grid2"><div><label class="lab" for="nf">Wyjazd</label><input id="nf" type="date" value="${esc(f.from)}"></div><div><label class="lab" for="nt">Powrót</label><input id="nt" type="date" value="${esc(f.to)}"></div></div>
      <span class="lab">Czym</span><div class="seg">${[['car', 'Auto'], ['train', 'Pociąg'], ['plane', 'Samolot'], ['other', 'Inaczej']].map(([k, l]) => `<button data-nm="${k}" aria-pressed="${f.mode === k}">${l}</button>`).join('')}</div>
      <div class="grid2"><div><label class="lab" for="na">Na miejscu o</label><input id="na" type="time" value="${esc(f.arrive)}"></div><div><label class="lab" for="nl">Powrót o</label><input id="nl" type="time" value="${esc(f.leave)}"></div></div>
      ${f.mode !== 'car' ? `<label class="lab" for="nc">Koszt biletów, jeśli znasz (zł)</label><input id="nc" type="number" inputmode="numeric" value="${esc(f.transportCost)}">` : '<p class="hint">Trasę i paliwo policzę z Twojego miejsca startu.</p>'}
      <label class="lab" for="nh">Nocleg, jeśli masz</label><input id="nh" maxlength="80" value="${esc(f.hotel)}"><label class="lab" for="nhc">Koszt noclegu (zł)</label><input id="nhc" type="number" inputmode="numeric" value="${esc(f.hotelCost)}">
      <button class="btn" id="nok">Utwórz wyjazd</button></div></section>`;
      const g = () => { f.q = $('#nq').value; f.from = $('#nf').value; f.to = $('#nt').value; f.arrive = $('#na').value; f.leave = $('#nl').value; f.hotel = $('#nh').value; f.hotelCost = $('#nhc').value; f.transportCost = $('#nc')?.value || ''; };
      $('#b').onclick = () => x.viewTrips();
      $('#nq').onchange = (e) => { g(); pick(e.target.value); draw(); };
      $$('[data-nm]').forEach((b) => { b.onclick = () => { g(); f.mode = b.dataset.nm; draw(); }; });
      const ge = $('#ngeo'); if (ge) ge.onclick = async () => {
        g(); if (!f.q.trim()) return toast('Wpisz miejsce.');
        try {
          const r = await (await fetch(`https://geocoding-api.open-meteo.com/v1/search?count=5&language=pl&name=${encodeURIComponent(f.q.trim())}`)).json();
          const L2 = r.results || []; $('#ngl').innerHTML = L2.map((y, i) => `<button class="kvb" data-gg="${i}"><span>${esc(y.name)}</span><b>${esc(y.admin1 || y.country || '')}</b></button>`).join('') || '<p class="mute">Nic nie znalazłem. Wpisz inaczej.</p>';
          $$('[data-gg]').forEach((b) => { b.onclick = () => { const y = L2[+b.dataset.gg]; f.dest = { name: y.name, cc: y.country_code, lat: y.latitude, lon: y.longitude }; g(); draw(); }; });
        } catch { toast('Wyszukiwanie miejsc wymaga internetu.'); }
      };
      $('#nok').onclick = async () => {
        g(); if (!f.dest) return toast('Wybierz miejsce.');
        if (!f.from || !f.to || f.to <= f.from) return toast('Sprawdź daty.');
        if (f.mode === 'car' && !S.q.origin) return toast('Ustaw miejsce wyjazdu na ekranie startowym.');
        $('#nok').disabled = true; toast('Układam plan…');
        try {
          const p = await api('/api/plan/manual', { dest: f.dest, from: f.from, to: f.to, mode: f.mode, arrive: f.arrive, leave: f.leave, hotel: f.hotel, hotelCost: f.hotelCost, transportCost: f.transportCost, home: S.q.origin, pax: S.q.pax, transport: S.q.transport, prefs: S.q.plan || {} });
          S.plan = p; S.newT = null; savePlan(p); ensureRemote(p).catch(() => {}); S.tab = 'sum'; x.viewPlan();
        } catch (e) { $('#nok').disabled = false; toast(e.message); }
      };
    };
    draw();
  }
  /* ---------- Wlasna rezerwacja ---------- */
  function viewOwnHotel(o, done, back) {
    const f = S.ownH ||= { name: '', address: '', ci: o.dep, co: o.ret, checkin: '15:00', breakfast: false, cost: '', code: '', phone: '', hit: null };
    app.innerHTML = `<div class="topbar"><button class="round" id="b" aria-label="Wstecz">${ICON.back}</button><h2>Własna rezerwacja</h2></div><section class="page"><div class="wcard form2">
      <p class="mute">Wpisz nocleg zarezerwowany gdziekolwiek. Plan ułożymy tak samo jak dla hotelu z listy, dojazdy policzymy od tego adresu.</p>
      <label class="lab" for="hn">Nazwa obiektu</label><input id="hn" maxlength="100" value="${esc(f.name)}">
      <label class="lab" for="ha">Adres, z ulicą i miastem</label><input id="ha" maxlength="160" value="${esc(f.address)}" placeholder="np. Via Carulli 62, Bari">
      <button class="btn line small" id="hg">Sprawdź adres na mapie</button><p class="hint" id="hgr">${f.hit ? `Znaleziono: ${esc(f.hit.label)}` : ''}</p>
      <div class="grid2"><div><label class="lab" for="hci">Zameldowanie</label><input id="hci" type="date" value="${esc(f.ci)}"></div><div><label class="lab" for="hco">Wymeldowanie</label><input id="hco" type="date" value="${esc(f.co)}"></div></div>
      <label class="lab" for="hct">Zameldowanie od godziny</label><input id="hct" type="time" value="${esc(f.checkin)}">
      <label class="switch">Śniadanie w cenie<input type="checkbox" id="hb" ${f.breakfast ? 'checked' : ''}></label>
      <label class="lab" for="hp">Cena za cały pobyt (zł)</label><input id="hp" type="number" inputmode="decimal" value="${esc(f.cost)}">
      <label class="lab" for="hc">Numer rezerwacji</label><input id="hc" maxlength="60" value="${esc(f.code)}">
      <label class="lab" for="ht">Telefon do obiektu</label><input id="ht" type="tel" maxlength="30" value="${esc(f.phone)}">
      <button class="btn" id="hok">Ułóż plan z tym noclegiem</button></div></section>`;
    const g = () => { f.name = $('#hn').value.trim(); f.address = $('#ha').value.trim(); f.ci = $('#hci').value; f.co = $('#hco').value; f.checkin = $('#hct').value; f.breakfast = $('#hb').checked; f.cost = $('#hp').value; f.code = $('#hc').value.trim(); f.phone = $('#ht').value.trim(); };
    const near = [o.dest.lat, o.dest.lon];
    const find = async () => { g(); const r = await api('/api/geocode', { q: f.address, near }); f.hit = r.hit; $('#hgr').textContent = r.hit ? `Znaleziono: ${r.hit.label}` : 'Nie znalazłem tego adresu przy tym celu. Wpisz ulicę i miasto, np. po angielsku lub włosku.'; return r.hit; };
    $('#b').onclick = () => { S.ownH = null; back(); };
    $('#ha').oninput = () => { f.hit = null; };
    $('#hg').onclick = () => find().catch((e) => toast(e.message));
    $('#hok').onclick = async () => {
      g(); if (!f.name) return toast('Wpisz nazwę obiektu.');
      if (!f.address) return toast('Wpisz adres.');
      if (!f.ci || !f.co || f.co <= f.ci) return toast('Sprawdź daty.');
      let hit = f.hit; try { hit ||= await find(); } catch (e) { return toast(e.message); }
      if (!hit) return toast('Popraw adres, żeby dało się policzyć dojazdy.');
      const hotel = { key: 'own', own: true, name: f.name, address: f.address, lat: hit.lat, lon: hit.lon, ci: f.ci, co: f.co, checkin: f.checkin, breakfast: f.breakfast, bestTotal: Math.round(+f.cost) || 0, code: f.code, phone: f.phone, prices: [] };
      S.ownH = null; S.pendingVault = hotel; done(hotel);
    };
  }
  function ownToVault(p) {
    const h = S.pendingVault; if (!h) return; S.pendingVault = null;
    put('vault', 'own-hotel', { id: 'own-hotel', kind: 'res', title: h.name, code: h.code || h.phone, text: [h.address, h.phone, `${h.ci} – ${h.co}`].filter(Boolean).join('\n') }, null, p);
  }
  /* ---------- Kopia i ceny ---------- */
  function exportAll() {
    const b = new Blob([JSON.stringify({ app: 'globtroter', t: Date.now(), trips: load('trips', []), fav: load('fav', []), prefs: S.q }, null, 1)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `globtroter-kopia-${new Date().toISOString().slice(0, 10)}.json`; a.click();
  }
  async function importAll(file) {
    const j = JSON.parse(await file.text()); if (j.app !== 'globtroter' || !Array.isArray(j.trips)) throw new Error('To nie jest kopia Globtrotera.');
    const have = load('trips', []); const ids = new Set(have.map((t) => t.option.id)); const add = j.trips.filter((t) => t?.option?.id && !ids.has(t.option.id));
    save('trips', [...have, ...add].slice(0, 30)); save('fav', [...new Set([...load('fav', []), ...(j.fav || [])])]);
    return add.length;
  }
  async function watchAdd(o, P) {
    if (!pushOn()) return toast('Włącz najpierw powiadomienia w Profilu.');
    try { await api('/api/watch/add', { device: device(), from: o.from, to: o.to, ym: o.dep.slice(0, 7), nights: o.nights, name: o.dest.name.split(' (')[0], price: Math.round(o.tickets / P) }); toast('Obserwuję. Napiszę, gdy cena spadnie o co najmniej 5% i 30 zł.'); } catch (e) { toast(e.message); }
  }
  async function watchDraw(el) {
    if (!pushOn()) { el.innerHTML = ''; return; }
    try {
      const { list } = await api('/api/watch?device=' + encodeURIComponent(device()));
      el.innerHTML = list.length ? `<div class="wcard"><h3>Obserwowane ceny</h3><p class="mute">Sprawdzam raz na dobę, nad ranem.</p>${list.map((w) => `<div class="kv"><span>${esc(w.name)}, ${w.from} → ${w.to}<small class="mute" style="display:block">${w.ym}, ${w.nights} nocy, teraz ${zl(w.last)}/os.</small></span><button data-wd2="${w.id}" aria-label="Przestań obserwować">✕</button></div>`).join('')}</div>` : '';
      $$('[data-wd2]', el).forEach((b) => { b.onclick = async () => { await api('/api/watch/del', { device: device(), id: b.dataset.wd2 }); watchDraw(el); }; });
    } catch { el.innerHTML = ''; }
  }
  return { viewOwnHotel, ownToVault, refreshWeather, viewNew, exportAll, importAll, watchAdd, watchDraw, exploreData: explore, L, canEdit, applyDays, savePlan, syncNow, openLink, viewShare, editHtml, bindDay, viewExplore, budgetHtml, bindBudget, docsHtml, bindDocs, put, pushHtml, bindPush, linkPush, askSentence, viewAI, ensureRemote };
}
