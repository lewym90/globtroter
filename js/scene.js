// Generator plakatów: każdy kierunek dostaje własną, warstwową scenę w duchu dawnych plakatów linii lotniczych.
// Scena powstaje z ziarna (nazwa miejsca), więc Rzym zawsze wygląda jak Rzym z Globtrotera.

const SKIES = {
  dawn:  { sky: ['#14306f', '#3f5fb0', '#f08a7a', '#ffd08a'], sun: '#fff0c2', far: '#5a6fb8', mid: '#2e4592', near: '#142a63', sea: ['#2b6cb5', '#123c80'] },
  noon:  { sky: ['#0f6fbf', '#2fa8dd', '#8ddcea', '#ffeec4'], sun: '#ffc93c', far: '#6ec4d8', mid: '#148a9a', near: '#0b4f6c', sea: ['#10a5b5', '#075a88'] },
  dusk:  { sky: ['#1b1a5e', '#6a2a8c', '#f0553f', '#ffb627'], sun: '#ffe08a', far: '#7c3b92', mid: '#46207a', near: '#1d1148', sea: ['#c84a5e', '#3c1a6c'] },
  night: { sky: ['#050d2b', '#0a1f54', '#1b3f8b', '#3a6bc0'], sun: '#f5f0d8', far: '#183a80', mid: '#0f2760', near: '#071538', sea: ['#14418c', '#071a45'] },
  snow:  { sky: ['#1560b3', '#4ca6e6', '#b9e4f5', '#fff3dc'], sun: '#ffd25e', far: '#d5ecf8', mid: '#a9d3ec', near: '#ffffff', sea: ['#ffffff', '#d7ecf7'] },
};

function rng(seed) {
  let h = 2166136261;
  for (const c of String(seed)) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return () => {
    h += 0x6d2b79f5;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function ridge(r, base, amp, step, w = 400, h = 800) {
  let d = `M-20 ${h}L-20 ${base}`;
  let x = -20;
  let y = base;
  while (x < w + 20) {
    x += step * (0.6 + r() * 0.8);
    y = base - r() * amp;
    d += `L${x.toFixed(0)} ${y.toFixed(0)}`;
  }
  return d + `L${w + 20} ${h}Z`;
}

function hills(r, base, amp, w = 400, h = 800) {
  const n = 4;
  let d = `M-20 ${base}`;
  for (let i = 0; i < n; i++) {
    const x1 = -20 + ((i + 0.5) * (w + 40)) / n;
    const x2 = -20 + ((i + 1) * (w + 40)) / n;
    d += `Q${x1.toFixed(0)} ${(base - amp * (0.4 + r() * 0.9)).toFixed(0)} ${x2.toFixed(0)} ${(base - r() * amp * 0.3).toFixed(0)}`;
  }
  return d + `L${w + 20} ${h}L-20 ${h}Z`;
}

function rays(cx, cy, color) {
  let s = '';
  const n = 16;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const b = a + Math.PI / n;
    const R = 900;
    s += `<path d="M${cx} ${cy}L${cx + R * Math.cos(a)} ${cy + R * Math.sin(a)}L${cx + R * Math.cos(b)} ${cy + R * Math.sin(b)}Z"/>`;
  }
  return `<g class="sc-rays" style="transform-origin:${cx}px ${cy}px" fill="${color}" opacity=".1">${s}</g>`;
}

function cloud(x, y, s, fill, cls) {
  return `<g class="${cls}" transform="translate(${x} ${y}) scale(${s})"><path fill="${fill}" d="M0 30h120c12 0 12-16 0-16h-8c2-14-20-22-30-10-6-16-34-14-36 4-6-6-22-4-22 8H6c-10 0-16 14-6 14z"/></g>`;
}

function palm(x, y, s, c) {
  const fr = [-150, -115, -80, -45, -15, 20].map((a) => {
    const L = 62;
    const rad = (a * Math.PI) / 180;
    const ex = L * Math.cos(rad);
    const ey = L * Math.sin(rad) + 26;
    return `<path d="M0 0Q${ex * 0.5} ${ey - 40} ${ex} ${ey}Q${ex * 0.45} ${ey - 26} 0 0Z"/>`;
  }).join('');
  return `<g transform="translate(${x} ${y}) scale(${s})" fill="${c}"><path d="M-4 150Q6 70 -2 0l6 0Q18 74 7 150Z"/>${fr}</g>`;
}

// Sylwetki miast. Rysowane prostymi bryłami, żeby trzymały plakatową stylistykę.
const LANDMARKS = {
  rzym: (b, c) => {
    let a = '';
    for (let i = 0; i < 7; i++) a += `<path d="M${112 + i * 26} ${b}v-24a10 10 0 0 1 20 0v24z" fill="#ffffff22"/>`;
    for (let i = 0; i < 7; i++) a += `<path d="M${112 + i * 26} ${b - 42}v-14a10 10 0 0 1 20 0v14z" fill="#ffffff22"/>`;
    return `<path fill="${c}" d="M100 ${b}V${b - 66}Q190 ${b - 92} 290 ${b - 58}V${b}Z"/>${a}<path fill="${c}" d="M18 ${b}v-34h12q2-30 24-34v-12h4v12q22 4 24 34h12v34z"/>`;
  },
  paryz: (b, c) => `<path fill="${c}" d="M196 ${b - 260}h8l4 60 12 64 26 136h-22q-24-66-28-66t-28 66h-22l26-136 12-64z"/><path fill="${c}" d="M168 ${b - 76}h64v8h-64zM180 ${b - 140}h40v6h-40z"/>`,
  barcelona: (b, c) => [150, 176, 214, 240].map((x, i) => `<path fill="${c}" d="M${x} ${b}V${b - 120 - (i % 3) * 34}q9-44 18 0V${b}z"/>`).join('') + `<path fill="${c}" d="M128 ${b}V${b - 70}h154v70z"/>`,
  londyn: (b, c) => `<path fill="${c}" d="M186 ${b}V${b - 190}l14-44 14 44V${b}z"/><circle cx="200" cy="${b - 158}" r="9" fill="#fff4df"/><path fill="${c}" d="M60 ${b}V${b - 54}h126v54zM214 ${b}V${b - 54}h126v54z"/>`,
  ateny: (b, c) => {
    let a = `<path fill="${c}" d="M92 ${b - 66}L200 ${b - 104}L308 ${b - 66}Z"/><rect x="92" y="${b - 64}" width="216" height="8" fill="${c}"/><rect x="84" y="${b - 8}" width="232" height="8" fill="${c}"/>`;
    for (let i = 0; i < 9; i++) a += `<rect x="${98 + i * 24}" y="${b - 56}" width="11" height="48" fill="${c}"/>`;
    return a;
  },
};

function skyline(r, base, c, unique) {
  let s = '';
  let x = -10;
  while (x < 410) {
    const w = 18 + r() * 30;
    const h = 28 + r() * 70;
    const k = r();
    if (k > 0.78) s += `<path fill="${c}" d="M${x} ${base}V${base - h}q${w / 2}-${w * 0.9} ${w} 0V${base}z"/>`;
    else if (k > 0.55) s += `<path fill="${c}" d="M${x} ${base}V${base - h}l${w / 2}-16 ${w / 2} 16V${base}z"/>`;
    else s += `<rect fill="${c}" x="${x}" y="${base - h}" width="${w}" height="${h}"/>`;
    x += w + r() * 5;
  }
  return s + (unique || '');
}

export function themeOf(tags = []) {
  if (tags.includes('ski')) return 'ski';
  if (tags.includes('beach')) return 'beach';
  if (tags.includes('nature')) return 'nature';
  if (tags.includes('party')) return 'night';
  if (tags.includes('city') || tags.includes('culture')) return 'city';
  return 'sky';
}

export function scene({ seed = 'globtroter', theme = 'sky', time, animated = false, landmark, plane = false } = {}) {
  const r = rng(seed);
  const pick = time || (theme === 'ski' ? 'snow' : theme === 'night' ? 'night' : ['dawn', 'noon', 'dusk'][Math.floor(r() * 3)]);
  const P = SKIES[pick];
  const id = 'g' + Math.floor(r() * 1e9).toString(36);
  const sx = 90 + r() * 220;
  const sy = theme === 'sky' ? 330 : 400 + r() * 40;
  let g = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">${P.sky.map((c, i) => `<stop offset="${[0, 0.38, 0.62, 0.8][i]}" stop-color="${c}"/>`).join('')}</linearGradient>
  <linearGradient id="${id}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${P.sea[0]}"/><stop offset="1" stop-color="${P.sea[1]}"/></linearGradient></defs>`;
  g += `<rect width="400" height="800" fill="url(#${id})"/>`;
  if (pick === 'night') for (let i = 0; i < 70; i++) g += `<circle class="${i % 5 ? '' : 'sc-tw'}" cx="${(r() * 400).toFixed(0)}" cy="${(r() * 460).toFixed(0)}" r="${(0.5 + r()).toFixed(1)}" fill="#fff" opacity="${(0.4 + r() * 0.6).toFixed(2)}"/>`;
  g += rays(sx, sy, P.sun);
  g += `<circle class="sc-sun" cx="${sx}" cy="${sy}" r="58" fill="${P.sun}"/><circle cx="${sx}" cy="${sy}" r="84" fill="${P.sun}" opacity=".16"/>`;
  g += cloud(-40 + r() * 80, 110 + r() * 60, 1.2, '#ffffff', 'sc-c1');
  g += cloud(210 + r() * 80, 210 + r() * 60, 0.9, '#ffffffcc', 'sc-c2');
  g += cloud(40 + r() * 100, 300 + r() * 40, 0.6, '#ffffff88', 'sc-c3');

  if (theme === 'beach') {
    g += `<path d="${hills(r, 520, 60)}" fill="${P.far}"/>`;
    g += `<rect y="520" width="400" height="280" fill="url(#${id}s)"/>`;
    for (let i = 0; i < 6; i++) {
      const y = 540 + i * 30;
      g += `<path class="sc-wave sc-w${i % 3}" d="M-60 ${y}q15-8 30 0t30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0 30 0" fill="none" stroke="#ffffff" stroke-opacity="${0.5 - i * 0.05}" stroke-width="3"/>`;
    }
    g += `<path d="M-20 800V690Q110 650 230 700T420 680V800Z" fill="#ffd9a0"/>`;
    g += palm(330, 590, 1.3, P.near) + palm(60, 650, 0.9, P.near);
  } else if (theme === 'ski') {
    g += `<path d="${ridge(r, 470, 200, 66)}" fill="${P.far}"/>`;
    g += `<path d="${ridge(r, 570, 180, 80)}" fill="${P.mid}"/>`;
    g += `<path d="M-20 800V640Q140 560 420 700V800Z" fill="#ffffff"/>`;
    for (let i = 0; i < 9; i++) {
      const x = r() * 400;
      const y = 650 + r() * 120;
      const s = 18 + r() * 24;
      g += `<path fill="#0f3d5e" d="M${x} ${y - s * 2}l${s * 0.7} ${s * 1.1}h-${s * 0.34}l${s * 0.62} ${s}h-${s * 2}l${s * 0.62}-${s}h-${s * 0.34}z"/>`;
    }
    for (let i = 0; i < 40; i++) g += `<circle class="sc-snow sc-s${i % 3}" cx="${(r() * 400).toFixed(0)}" cy="${(r() * 800).toFixed(0)}" r="${(1 + r() * 2).toFixed(1)}" fill="#fff"/>`;
  } else if (theme === 'nature') {
    g += `<path d="${ridge(r, 480, 150, 70)}" fill="${P.far}"/>`;
    g += `<path d="${hills(r, 590, 130)}" fill="${P.mid}"/>`;
    g += `<rect y="630" width="400" height="60" fill="url(#${id}s)"/>`;
    g += `<path d="${hills(r, 720, 70)}" fill="${P.near}"/>`;
  } else if (theme === 'city' || theme === 'night') {
    const b = 640;
    const lm = landmark && LANDMARKS[landmark] ? LANDMARKS[landmark](b, P.mid) : '';
    g += `<g>${skyline(r, 590, P.far)}</g>`;
    g += lm ? lm : skyline(r, b, P.mid);
    g += `<g>${skyline(r, 720, P.near)}</g><rect y="718" width="400" height="90" fill="${P.near}"/>`;
    if (pick === 'night') for (let i = 0; i < 60; i++) g += `<rect x="${(r() * 400).toFixed(0)}" y="${(630 + r() * 85).toFixed(0)}" width="3" height="4" fill="#ffd25e" opacity="${(0.4 + r() * 0.6).toFixed(2)}"/>`;
  } else {
    g += cloud(-60, 620, 3.4, '#ffffff', 'sc-c2') + cloud(180, 670, 3, '#ffffffee', 'sc-c1') + cloud(-90, 730, 4, '#ffffff', 'sc-c3');
    g += `<rect y="772" width="400" height="30" fill="#fff"/>`;
  }
  if (plane) {
    g += `<defs><linearGradient id="${id}t"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".85"/></linearGradient></defs>
      <g class="sc-jet"><rect x="-250" y="-1.5" width="226" height="3" rx="1.5" fill="url(#${id}t)"/><path fill="#fff" d="M30 0 8-4 -6-24h-8l6 19-16 1-7-9h-6l3 13-3 13h6l7-9 16 1-6 19h8L8 4 30 0Q36 0 30 0Z"/></g>`;
  }
  return `<svg class="scene ${animated ? 'is-live' : ''}" viewBox="0 0 400 800" preserveAspectRatio="xMidYMax slice" aria-hidden="true">${g}</svg>`;
}

export function landmarkOf(id) {
  return { rzym: 'rzym', paryz: 'paryz', barcelona: 'barcelona', londyn: 'londyn', ateny: 'ateny' }[id];
}
