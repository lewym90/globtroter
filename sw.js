// Kod i dane: najpierw siec z pominieciem pamieci przegladarki, max 4 s, potem kopia offline.
// Czcionki i ikony: kopia. Dzieki temu kazde otwarcie daje najnowsza wersje, a bez internetu aplikacja dalej dziala.
const V='gt-v2.0.0';
const SHELL=['./','index.html','css/app.css','js/app.js','js/scene.js','js/flap.js','data/airports.json','data/destinations.json','data/photos.json','data/hero.json','data/shapes.json','vendor/leaflet/leaflet.js','vendor/leaflet/leaflet.css','icons/logo-96.png','manifest.webmanifest','icons/icon-192.png','fonts/big-shoulders-display-latin-wght-normal.woff2','fonts/big-shoulders-display-latin-ext-wght-normal.woff2','fonts/figtree-latin-wght-normal.woff2','fonts/figtree-latin-ext-wght-normal.woff2'];
self.addEventListener('install',e=>e.waitUntil(caches.open(V).then(c=>Promise.all(SHELL.map(u=>fetch(new Request(u,{cache:'reload'})).then(r=>{if(!r.ok)throw new Error(u);return c.put(u,r);})))).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const req=e.request;
  if(req.method!=='GET')return;
  const u=new URL(req.url);
  if(u.origin!==location.origin)return;
  const store=r=>{if(r&&r.ok){const c=r.clone();caches.open(V).then(x=>x.put(req,c));}return r;};
  if(/\.(woff2?|png|svg|ico)$/i.test(u.pathname)){e.respondWith(caches.match(req,{ignoreSearch:true}).then(h=>h||fetch(req).then(store)));return;}
  e.respondWith(new Promise(res=>{
    let done=false;
    const back=()=>caches.match(req,{ignoreSearch:true}).then(h=>h||(req.mode==='navigate'?caches.match('index.html'):Response.error()));
    const t=setTimeout(()=>{if(!done)caches.match(req,{ignoreSearch:true}).then(h=>{if(h&&!done){done=true;res(h);}});},4000);
    fetch(req,{cache:'no-cache'}).then(r=>{store(r);if(!done){done=true;clearTimeout(t);res(r);}}).catch(()=>{if(!done){done=true;clearTimeout(t);back().then(res);}});
  }));
});
