// ═══════════════════════════════════════════════════════════════
// BandiRadar — Service Worker (Fase 5.3)
//
// Strategia:
//  - data/*  → network-first con fallback cache (vedi sempre dati freschi
//              se hai connessione; offline usa l'ultima copia)
//  - HTML/CSS/JS statici → stale-while-revalidate (cache veloce, aggiorna
//              in background, banner "nuova versione" se cambia index.html)
//  - tutto il resto → solo rete (no cache)
//
// Aggiornare CACHE_VERSION ogni volta che si rilasciano modifiche grosse
// per forzare la rigenerazione del cache.
// ═══════════════════════════════════════════════════════════════

const CACHE_VERSION = 'bandiradar-v4'; // v4 (2026-06-12): banner fonti con stato BLOCCATO (WAF) + fix fonti
const PRECACHE = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './glossario.html',
  './status.html',
  './report.html',
  './404.html',
  './manifest.json',
];

// Installazione: precarica i file statici
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then((cache) => cache.addAll(PRECACHE).catch(() => {/* ok se qualcosa manca */}))
      .then(() => self.skipWaiting())
  );
});

// Attivazione: pulisce vecchie cache
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch: strategia per tipologia
self.addEventListener('fetch', (event) => {
  const req = event.request;
  // Solo GET, solo same-origin (no CDN, no API esterne)
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const path = url.pathname;

  // 1. data/* → network-first
  if (path.includes('/data/')) {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          // Cache la risposta fresca per uso offline
          const copy = resp.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(req, copy)).catch(() => {});
          return resp;
        })
        .catch(() => caches.match(req).then((c) => c || new Response('', { status: 503, statusText: 'Offline' })))
    );
    return;
  }

  // 2. HTML/CSS/JS statici → stale-while-revalidate
  if (path.endsWith('.html') || path.endsWith('.css') || path.endsWith('.js') || path === '/' || path.endsWith('/')) {
    event.respondWith(
      caches.match(req).then((cached) => {
        const fetchPromise = fetch(req)
          .then((resp) => {
            const copy = resp.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(req, copy)).catch(() => {});
            return resp;
          })
          .catch(() => cached || new Response('Offline', { status: 503 }));
        return cached || fetchPromise;
      })
    );
    return;
  }

  // 3. Manifest e icone → cache-first
  if (path.endsWith('manifest.json') || path.includes('icon')) {
    event.respondWith(
      caches.match(req).then((cached) =>
        cached || fetch(req).then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(req, copy)).catch(() => {});
          return resp;
        })
      )
    );
    return;
  }

  // 4. Tutto il resto: rete senza cache (es. fetch ad altri server)
  // (default: il browser gestisce normalmente)
});
