// Questionize service worker: the app opens offline and starts fast, while every visit online
// still gets the newest version. API calls, live updates and uploads always go to the network.
const VERSION = "v2";
// "/" always returns the app shell (it is not tied to an HTML Accept header like the client routes).
const SHELL = `shell-${VERSION}`;
const ASSETS = `assets-${VERSION}`;
const PRECACHE = ["/", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png", "/apple-touch-icon.png", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== ASSETS).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // The research console has its own shell and must never replace the learner's offline app.
  if (url.pathname === "/admin" || url.pathname.startsWith("/admin/")) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/cable") || url.pathname === "/sw.js") return;

  // Pages: the network first (so a deploy shows up right away), the saved shell when offline.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) caches.open(SHELL).then((cache) => cache.put("/", response.clone()));
          return response;
        })
        .catch(() => caches.match("/")),
    );
    return;
  }

  // Built assets have content hashes in their names, so a cached copy never goes stale.
  if (url.pathname.startsWith("/web-assets/")) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) caches.open(ASSETS).then((cache) => cache.put(request, response.clone()));
            return response;
          }),
      ),
    );
    return;
  }

  if (PRECACHE.includes(url.pathname)) event.respondWith(caches.match(request).then((hit) => hit || fetch(request)));
});
