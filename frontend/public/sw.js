// TryJob service worker (CONTRACT.md §22.1–22.2) — kutubxonasiz.
// Qoidalar: /api/* va boshqa domenlar HECH QACHON keshlanmaydi (shaxsiy ma'lumot);
// /assets/* (Vite hash'li fayllar) — cache-first; sahifalar — network-first,
// tarmoq yo'q bo'lsa keshdagi ilova qobig'i (index.html).
const VERSION = 'v1'
const SHELL = `tryjob-shell-${VERSION}`
const ASSETS = `tryjob-assets-${VERSION}`
const SHELL_FILES = ['/', '/manifest.webmanifest', '/favicon.svg', '/icons/icon-192.png']

// har deploy yangi hash'li fayllar beradi — eskilari cheksiz to'planmasin (eng eskisi birinchi o'chadi)
const MAX_ASSETS = 60
async function trim(cache) {
  const keys = await cache.keys()
  for (const key of keys.slice(0, Math.max(0, keys.length - MAX_ASSETS))) await cache.delete(key)
}

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = new Set([SHELL, ASSETS])
    for (const key of await caches.keys()) if (!keep.has(key)) await caches.delete(key)
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return

  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const res = await fetch(req)
        if (res.ok) (await caches.open(SHELL)).put('/', res.clone())
        return res
      } catch {
        return (await caches.match('/')) ?? Response.error()
      }
    })())
    return
  }

  if (url.pathname.startsWith('/assets/')) {
    event.respondWith((async () => {
      const cached = await caches.match(req)
      if (cached) return cached
      const res = await fetch(req)
      if (res.ok) {
        const cache = await caches.open(ASSETS)
        await cache.put(req, res.clone())
        await trim(cache)
      }
      return res
    })())
  }
})

// ── Push ──────────────────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { body: event.data ? event.data.text() : '' }
  }
  event.waitUntil(self.registration.showNotification(data.title || 'TryJob', {
    body: data.body || '',
    tag: data.tag,
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    data: { link: data.link || '/' },
  }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.link || '/', self.location.origin)
  // faqat o'z domenimiz ichidagi havola ochiladi
  if (target.origin !== self.location.origin) return
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const open = windows.find((w) => new URL(w.url).origin === self.location.origin)
    if (open) {
      // navigate() faqat shu SW boshqaradigan oynada ishlaydi — bo'lmasa yangi oyna
      const moved = await open.navigate(target.href).catch(() => null)
      if (moved) return moved.focus()
    }
    return self.clients.openWindow(target.href)
  })())
})
