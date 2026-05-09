// Wally Trader minimal SW — offline cache for static assets
const CACHE = 'wally-v1';
const ASSETS = ['/', '/static/style.css', '/static/app.js', '/manifest.json'];

self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener('fetch', e => {
    // Network-first for API, cache-first for static
    if (e.request.url.includes('/api/')) {
        e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    } else {
        e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
    }
});
