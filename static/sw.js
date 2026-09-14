const CACHE_NAME = 'autolink-v2';
const STATIC_ASSETS = [
    '/static/icons/pwa-192.svg',
    '/static/icons/pwa-512.svg',
    '/static/icons/pwa-maskable.svg',
    '/static/manifest.json',
    '/static/output.css',
];
const PAGES = [
    '/',
    '/garages',
    '/pieces',
    '/contact',
    '/about',
    '/policy',
    '/recherche',
    '/connexion',
    '/inscription',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        }).catch(() => {})
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Ignorer les requêtes vers d'autres origines
    if (url.origin !== self.location.origin) return;

    const path = url.pathname;

    // Navigation : essayer le réseau, fallback sur page offline
    if (event.request.mode === 'navigate' || event.request.method === 'GET') {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    // Cloner et mettre en cache si c'est une page HTML
                    if (response.ok && response.headers.get('content-type')?.includes('text/html')) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, clone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    return caches.match(event.request).then((cached) => {
                        return cached || caches.match('/');
                    });
                })
        );
        return;
    }

    // Reste : cache-first pour les assets statiques
    event.respondWith(
        caches.match(event.request).then((cached) => {
            return cached || fetch(event.request).catch(() => cached);
        })
    );
});

