// MedMind AI — Service Worker
// Strategy:
//   - App shell (HTML, CSS, JS) → Cache-First, fallback to network
//   - API requests → Network-First (no caching of auth/personalised data)
//   - Static assets (images, fonts) → Stale-While-Revalidate

const CACHE_VERSION = "medmind-v1";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const ASSET_CACHE = `${CACHE_VERSION}-assets`;
const LESSON_CACHE = `${CACHE_VERSION}-lessons`;

// App shell routes to pre-cache on install
const SHELL_URLS = [
  "/",
  "/dashboard",
  "/modules",
  "/ai-tutor",
  "/flashcards",
  "/login",
  "/offline",
];

// ── Install ───────────────────────────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => {
      // Attempt to cache shell routes; failures are non-fatal
      return Promise.allSettled(
        SHELL_URLS.map((url) => cache.add(url).catch(() => null))
      );
    })
  );
  self.skipWaiting();
});

// ── Activate — clean up old caches ────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("medmind-") && key !== SHELL_CACHE && key !== ASSET_CACHE && key !== LESSON_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, cross-origin non-asset, and API requests (personalised data)
  if (request.method !== "GET") return;
  if (url.pathname.startsWith("/api/") || url.pathname.includes("/api/v1/")) return;

  // Lesson content pages — cache for offline reading
  if (url.pathname.startsWith("/modules/") || url.pathname.startsWith("/lessons/")) {
    event.respondWith(staleWhileRevalidate(request, LESSON_CACHE));
    return;
  }

  // Static assets (images, fonts, icons, _next/static)
  if (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.match(/\.(png|jpg|jpeg|svg|ico|woff2?|ttf|otf)$/)
  ) {
    event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
    return;
  }

  // App shell navigation requests — cache-first, offline fallback
  if (request.mode === "navigate") {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        }).catch(() => caches.match("/offline").then((r) => r || new Response("Offline", { status: 503 })));
      })
    );
    return;
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
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
