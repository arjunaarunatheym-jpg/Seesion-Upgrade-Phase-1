// Service Worker for MDDRC Training Portal PWA — Enhanced v2
/* global clients */
const CACHE_VERSION = 'v2';
const STATIC_CACHE = `mddrc-static-${CACHE_VERSION}`;
const DATA_CACHE = `mddrc-data-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline.html';

// Core shell assets to precache on install
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// API paths safe for stale-while-revalidate (read-only, non-sensitive)
const CACHEABLE_API_PATHS = [
  '/api/programs',
  '/api/companies',
  '/api/settings',
];

// Install — precache core shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
      .catch((err) => console.warn('SW install cache failed:', err))
  );
});

// Activate — purge old cache versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE && k !== DATA_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Helper: is this a cacheable API request?
function isCacheableAPI(url) {
  return CACHEABLE_API_PATHS.some((path) => url.pathname.startsWith(path));
}

// Helper: is this a static asset?
function isStaticAsset(url) {
  return /\.(js|css|png|jpg|jpeg|svg|woff2?|ttf|ico|webp)(\?.*)?$/.test(url.pathname);
}

// Fetch strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Strategy 1: Cacheable API — stale-while-revalidate
  if (url.pathname.startsWith('/api/') && isCacheableAPI(url)) {
    event.respondWith(
      caches.open(DATA_CACHE).then((cache) =>
        cache.match(request).then((cached) => {
          const networkFetch = fetch(request)
            .then((response) => {
              if (response.ok) {
                cache.put(request, response.clone());
              }
              return response;
            })
            .catch(() => cached); // network fail → serve stale
          return cached || networkFetch;
        })
      )
    );
    return;
  }

  // Skip non-cacheable API requests (always network)
  if (url.pathname.startsWith('/api/')) return;

  // Strategy 2: Static assets — cache-first
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then((c) => c.put(request, clone));
          }
          return response;
        }).catch(() =>
          new Response('', { status: 503, statusText: 'Offline' })
        );
      })
    );
    return;
  }

  // Strategy 3: Navigation — network-first, offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then((c) => c.put(request, clone));
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  // Default: network-first with cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then((c) => c.put(request, clone));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});

// Push notifications
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'MDDRC', {
      body: data.body || 'New notification',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png',
      vibrate: [100, 50, 100],
      data: { url: data.url || '/' },
      actions: data.actions || [],
    })
  );
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});

// Background sync (future use)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending') {
    event.waitUntil(Promise.resolve());
  }
});
