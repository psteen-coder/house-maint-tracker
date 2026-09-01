self.addEventListener("install", (event) => {
  event.waitUntil(caches.open("house-maint-v1").then((c) => c.addAll(["/"])));
});
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request).then((r) => r || caches.match("/")))
  );
});
