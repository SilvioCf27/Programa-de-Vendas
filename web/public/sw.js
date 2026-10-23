// Cache apenas da interface. Login, consultas e dados financeiros ficam fora.
const CACHE = 'feira-interface-v4';
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) =>
        cache.addAll([
          '/',
          '/icon-192.png',
          '/icon-512.png',
          '/manifest.webmanifest',
        ])
      )
  );
});
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith('feira-interface-') && k !== CACHE)
            .map((k) => caches.delete(k))
        )
      )
  );
});
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/')));
  } else if (
    url.pathname.startsWith('/assets/') ||
    ['/icon-192.png', '/icon-512.png', '/manifest.webmanifest'].includes(
      url.pathname
    )
  ) {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        const existente = await cache.match(request);
        if (existente) return existente;
        const resposta = await fetch(request);
        if (resposta.ok) await cache.put(request, resposta.clone());
        return resposta;
      })
    );
  }
});
