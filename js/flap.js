// Tablica klapkowa z dworców i lotnisk. Każda litera dochodzi do celu, przerzucając kilka klapek.
const ABC = ' ABCDEFGHIJKLMNOPQRSTUVWXYZĄĆĘŁŃÓŚŹŻ';
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

export function flapRow(n) {
  const el = document.createElement('div');
  el.className = 'brow';
  const cells = Array.from({ length: n }, () => {
    const c = document.createElement('span');
    c.className = 'fl';
    c.textContent = ' ';
    el.append(c);
    return c;
  });
  const timers = [];
  return {
    el,
    set(text) {
      timers.splice(0).forEach(clearInterval);
      const t = text.slice(0, n).padEnd(n, ' ');
      cells.forEach((c, i) => {
        if (reduce) { c.textContent = t[i]; return; }
        let k = 3 + (i % 5) + Math.floor(Math.random() * 3);
        const id = setInterval(() => {
          k -= 1;
          c.textContent = k <= 0 ? t[i] : ABC[Math.floor(Math.random() * ABC.length)];
          c.classList.remove('flip');
          void c.offsetWidth;
          c.classList.add('flip');
          if (k <= 0) clearInterval(id);
        }, 75);
        timers.push(id);
      });
    },
  };
}
