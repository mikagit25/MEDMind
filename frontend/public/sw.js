// MedMind AI — Service Worker v2
// Navigation: Network-First (serve fresh HTML always, fallback to cache offline)
// Static assets: Stale-While-Revalidate
// API: bypassed (no caching of personalised data)

const CACHE_VERSION = "medmind-v2";
const SHELL_CACHE  = `${CACHE_VERSION}-shell`;
const ASSET_CACHE  = `${CACHE_VERSION}-assets`;

// ── Install — pre-cache offline fallback only ─────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) =>
      cache.add("/offline").catch(() => null)
    )
  );
  self.skipWaiting();
});

// ── Activate — wipe ALL old medmind-* caches ─────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k.startsWith("medmind-") && k !== SHELL_CACHE && k !== ASSET_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and API requests
  if (request.method !== "GET") return;
  if (url.pathname.startsWith("/api/")) return;

  // Next.js immutable static assets — stale-while-revalidate
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
    return;
  }

  // Static files (icons, images, fonts, PDFs)
  if (url.pathname.match(/\.(png|jpg|jpeg|svg|ico|woff2?|ttf|otf|pdf|webp)$/)) {
    event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
    return;
  }

  // HTML navigation — always try network first, cache as fallback when offline
  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigate(request));
    return;
  }
});

// Network-first for HTML: always fetch fresh, serve cache only when offline
async function networkFirstNavigate(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    const offline = await cache.match("/offline");
    return offline || new Response("You are offline", { status: 503 });
  }
}

// Stale-while-revalidate for assets
async function staleWhileRevalidate(request, cacheName) {
  const cache  = await caches.open(cacheName);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);
  return cached || fetchPromise;
}
