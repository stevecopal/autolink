{% load static %}
// Service Worker AutoLink — cache minimal : page hors ligne uniquement.
// Seuls /offline/ et les ressources dont elle a besoin sont mis en cache.
// Le reste du site passe toujours par le réseau (aucun contenu obsolète).
// Le cache est rafraîchi en arrière-plan au plus une fois par minute.

const CACHE_NAME = 'autolink-offline-v2';
const OFFLINE_URL = '/offline/';

// Page hors ligne + ressources nécessaires à son affichage
// (elle est autonome : ni navbar ni footer, mais le CSS du thème et le logo).
const PRECACHE_URLS = [
    OFFLINE_URL,
    '{% static "css/output.css" %}',
    '{% static "logo.jpg" %}'
];

// Chemins mis en cache : permet de reconnaître les ressources à servir en priorité.
const CACHED_PATHS = PRECACHE_URLS.map(function(url) {
    return new URL(url, self.location.origin).pathname;
});

// Délai minimum entre deux rafraîchissements du cache (1 minute).
const REFRESH_INTERVAL = 60 * 1000;
var lastRefresh = 0;

// Recharge la page hors ligne et ses ressources dans le cache.
// Appelé en arrière-plan : le cache reste à jour sans ralentir la navigation.
function refreshOfflineCache() {
    var now = Date.now();
    if (now - lastRefresh < REFRESH_INTERVAL) {
        return Promise.resolve();
    }
    lastRefresh = now;

    return caches.open(CACHE_NAME).then(function(cache) {
        // addAll remplace les entrées existantes : le cache est actualisé.
        return cache.addAll(PRECACHE_URLS);
    }).catch(function() {
        // Hors ligne : on conserve la version déjà en cache.
    });
}

// Installation : mise en cache de la page hors ligne puis activation immédiate.
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(PRECACHE_URLS);
        }).catch(function() {
            // Réseau indisponible : la page sera mise en cache plus tard.
        }).then(function() {
            return self.skipWaiting();
        })
    );
});

// Activation : suppression des anciens caches puis prise de contrôle des pages.
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    return cacheName === CACHE_NAME ? undefined : caches.delete(cacheName);
                })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', function(event) {
    var request = event.request;

    // Seules les requêtes GET de notre propre domaine sont concernées.
    if (request.method !== 'GET') {
        return;
    }
    if (new URL(request.url).origin !== self.location.origin) {
        return;
    }

    // Navigation : réseau d'abord, page hors ligne en secours si ça échoue.
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(function() {
                return caches.match(OFFLINE_URL).then(function(cached) {
                    return cached || Response.error();
                });
            })
        );
        event.waitUntil(refreshOfflineCache());
        return;
    }

    // Ressources de la page hors ligne : servies depuis le cache (rapide)
    // puis rafraîchies en arrière-plan.
    if (CACHED_PATHS.indexOf(new URL(request.url).pathname) !== -1) {
        event.respondWith(
            caches.open(CACHE_NAME).then(function(cache) {
                return cache.match(request).then(function(cached) {
                    if (cached) {
                        return cached;
                    }
                    return fetch(request).then(function(response) {
                        if (response && response.ok) {
                            cache.put(request, response.clone());
                        }
                        return response;
                    });
                });
            })
        );
        event.waitUntil(refreshOfflineCache());
        return;
    }

    // Tout le reste : aucun cache, la requête passe directement au réseau.
});