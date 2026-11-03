const V='gt-v1.0.0';
const SHELL=['./','index.html','css/app.css','js/app.js','js/scene.js','js/flap.js','data/airports.json','data/destinations.json','manifest.webmanifest','icons/icon-192.png','fonts/big-shoulders-display-latin-wght-normal.woff2','fonts/big-shoulders-display-latin-ext-wght-normal.woff2','fonts/figtree-latin-wght-normal.woff2','fonts/figtree-latin-ext-wght-normal.woff2'];
self.addEventListener('install',e=>e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.origin!==location.origin)return;
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).catch(()=>caches.match('index.html'))));
});
