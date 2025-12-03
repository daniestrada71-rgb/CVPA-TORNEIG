self.addEventListener("install", e => {
  console.log("Service Worker: Installed");
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  console.log("Service Worker: Activated");
});

self.addEventListener("fetch", e => {
  // Simple offline fallback
  e.respondWith(
    fetch(e.request).catch(() => new Response("Offline"))
  );
});
