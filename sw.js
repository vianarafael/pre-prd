// Service Worker for pre prd PWA
const CACHE_NAME = "pre-prd-v1";
const STATIC_CACHE = "pre-prd-static-v1";

// Assets to cache immediately
const CORE_ASSETS = [
  "/",
  "/assets/global.css",
  "/assets/favicon.svg",
  "/assets/manifest.json",
  "https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css",
  "https://cdn.tailwindcss.com",
  "https://unpkg.com/htmx.org@1.9.12",
  "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
];

// Install event - cache core assets
self.addEventListener("install", (event) => {
  console.log("[SW] Installing service worker");
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => {
        console.log("[SW] Caching core assets");
        return cache.addAll(CORE_ASSETS);
      })
      .then(() => {
        console.log("[SW] Core assets cached");
        return self.skipWaiting();
      })
      .catch((error) => {
        console.log("[SW] Cache installation failed:", error);
      })
  );
});

// Activate event - cleanup old caches
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating service worker");
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE) {
              console.log("[SW] Deleting old cache:", cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log("[SW] Service worker activated");
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache with network fallback
self.addEventListener("fetch", (event) => {
  // Skip non-GET requests
  if (event.request.method !== "GET") {
    return;
  }

  // Skip chrome-extension requests
  if (event.request.url.startsWith("chrome-extension://")) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      // Return cached version if available
      if (cachedResponse) {
        console.log("[SW] Serving from cache:", event.request.url);
        return cachedResponse;
      }

      // Otherwise fetch from network
      console.log("[SW] Fetching from network:", event.request.url);
      return fetch(event.request)
        .then((response) => {
          // Don't cache non-successful responses
          if (
            !response ||
            response.status !== 200 ||
            response.type !== "basic"
          ) {
            return response;
          }

          // Clone response for caching
          const responseToCache = response.clone();

          // Cache the response for future use
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });

          return response;
        })
        .catch((error) => {
          console.log("[SW] Network fetch failed:", error);

          // Return offline page for navigation requests
          if (event.request.mode === "navigate") {
            return caches.match("/");
          }

          throw error;
        });
    })
  );
});

// Background sync for when connectivity returns
self.addEventListener("sync", (event) => {
  if (event.tag === "background-sync") {
    console.log("[SW] Background sync triggered");
    event.waitUntil(
      // Add any background sync logic here
      Promise.resolve()
    );
  }
});

// Push notification support (optional)
self.addEventListener("push", (event) => {
  if (event.data) {
    const options = {
      body: event.data.text(),
      icon: "/assets/favicon.svg",
      badge: "/assets/favicon.svg",
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: 1,
      },
    };

    event.waitUntil(self.registration.showNotification("pre prd", options));
  }
});
