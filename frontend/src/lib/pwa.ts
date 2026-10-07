// PWA (CONTRACT.md §22): service worker, "ilovani o'rnatish" taklifi, tarmoq holati
// va push obunasi. Brauzer API'lari bo'lmasa (eski brauzer, SSR emas) — jim o'chadi.
import { useSyncExternalStore } from 'react'
import { api } from './api'

const SUBSCRIPTIONS = '/users/me/push-subscriptions'

// ── O'rnatish taklifi ────────────────────────────────────────────────

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

let installEvent: BeforeInstallPromptEvent | null = null
const installListeners = new Set<() => void>()
const emitInstall = () => installListeners.forEach((l) => l())

/** Ilova yuklanganda bir marta: SW ro'yxatdan o'tadi, o'rnatish taklifi ushlab qolinadi. */
export function setupPwa() {
  // brauzer taklifni sahifa yuklanishi bilan beradi — keyinroq ulangan hook uni o'tkazib yubormasin
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    installEvent = e as BeforeInstallPromptEvent
    emitInstall()
  })
  window.addEventListener('appinstalled', () => {
    installEvent = null
    emitInstall()
  })
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch((err) => console.warn('service worker', err))
    })
  }
}

export function isStandalone(): boolean {
  return window.matchMedia?.('(display-mode: standalone)').matches || (navigator as { standalone?: boolean }).standalone === true
}

/** iPhone/iPad (iPadOS o'zini Mac deb tanishtiradi — sensor ekran bo'yicha ajratiladi). */
export function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

/** O'rnatish mumkin bo'lsa — taklifni ochadigan funksiya, aks holda `null`. */
export function useInstallPrompt(): (() => Promise<void>) | null {
  const available = useSyncExternalStore(
    (l) => {
      installListeners.add(l)
      return () => installListeners.delete(l)
    },
    () => installEvent !== null,
  )
  if (!available || isStandalone()) return null
  return async () => {
    const e = installEvent
    if (!e) return
    installEvent = null                                    // taklif faqat bir marta ishlatiladi
    emitInstall()
    await e.prompt()
  }
}

// ── Tarmoq holati ────────────────────────────────────────────────────

export function useOnline(): boolean {
  return useSyncExternalStore(
    (l) => {
      window.addEventListener('online', l)
      window.addEventListener('offline', l)
      return () => {
        window.removeEventListener('online', l)
        window.removeEventListener('offline', l)
      }
    },
    () => navigator.onLine,
  )
}

// ── Push ─────────────────────────────────────────────────────────────

/**
 * Shu brauzerdagi holat:
 * - `install` — iOS Safari: push faqat bosh ekranga qo'shilgan ilovada ishlaydi;
 * - `unsupported` — brauzer Web Push bilmaydi; `server-off` — VAPID sozlanmagan;
 * - `denied` — ruxsat rad etilgan (faqat brauzer sozlamasidan qaytariladi);
 * - `off` / `on` — shu qurilma obuna emas / obuna.
 */
export type PushState = 'install' | 'unsupported' | 'server-off' | 'denied' | 'off' | 'on'

interface PushConfig {
  enabled: boolean
  public_key: string | null
}

function supported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const pad = '='.repeat((4 - (base64url.length % 4)) % 4)
  const raw = atob((base64url + pad).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

/** Obuna joriy server kaliti bilan qilinganmi (kalit almashtirilsa — qayta obuna kerak). */
function sameKey(sub: PushSubscription, key: string): boolean {
  const current = sub.options.applicationServerKey
  if (!current) return false
  const a = new Uint8Array(current)
  const b = keyBytes(key)
  return a.length === b.length && a.every((x, i) => x === b[i])
}

/**
 * Brauzer push xizmatiga (masalan, FCM) yetolmasa `subscribe()` uzoq osilib qoladi —
 * tugma abadiy aylanmasin. Kech kelgan obuna yo'qolmaydi: keyingi `pushState()` uni saqlaydi.
 */
const SUBSCRIBE_TIMEOUT_MS = 20_000

function withTimeout<T>(promise: Promise<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('push subscribe timeout')), SUBSCRIBE_TIMEOUT_MS)
    promise.then(resolve, reject).finally(() => clearTimeout(timer))
  })
}

async function currentSubscription(): Promise<PushSubscription | null> {
  const reg = await navigator.serviceWorker.getRegistration()
  return (await reg?.pushManager.getSubscription()) ?? null
}

function save(sub: PushSubscription) {
  const { endpoint, keys } = sub.toJSON()
  return api<void>(SUBSCRIPTIONS, { method: 'POST', json: { endpoint, keys: { p256dh: keys?.p256dh, auth: keys?.auth } } })
}

export async function pushState(): Promise<PushState> {
  const config = await api<PushConfig>('/push/config')
  if (!config.enabled || !config.public_key) return 'server-off'
  if (!supported()) return isIos() && !isStandalone() ? 'install' : 'unsupported'
  if (Notification.permission === 'denied') return 'denied'
  const sub = await currentSubscription()
  if (!sub || Notification.permission !== 'granted' || !sameKey(sub, config.public_key)) return 'off'
  await save(sub)                                          // shu brauzerda boshqa akkaunt kirgan bo'lishi mumkin
  return 'on'
}

/** Ruxsat so'raydi va shu qurilmani obuna qiladi. Natija — yangi holat. */
export async function enablePush(): Promise<PushState> {
  const config = await api<PushConfig>('/push/config')
  if (!config.enabled || !config.public_key) return 'server-off'
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return permission === 'denied' ? 'denied' : 'off'

  const reg = await navigator.serviceWorker.ready
  let sub = await reg.pushManager.getSubscription()
  if (sub && !sameKey(sub, config.public_key)) {
    await sub.unsubscribe()
    sub = null
  }
  sub ??= await withTimeout(
    reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(config.public_key) }),
  )
  await save(sub)
  return 'on'
}

/** Faqat shu qurilmani uzadi (boshqa qurilmalar va hisob sozlamasi o'zgarmaydi). */
export async function disablePush(): Promise<PushState> {
  const sub = await currentSubscription()
  if (sub) {
    await api<void>(SUBSCRIPTIONS, { method: 'DELETE', json: { endpoint: sub.endpoint } })
    await sub.unsubscribe()
  }
  return 'off'
}

/**
 * Chiqishda (§22.2): bu brauzer endi shu akkauntga push olmasligi kerak.
 * Token oldindan olinadi — chiqish token'ni darhol o'chiradi, so'rov esa orqada ketadi.
 */
export async function forgetPush(access: string | null) {
  if (!supported()) return
  try {
    const sub = await currentSubscription()
    if (!sub) return
    if (access) {
      await fetch(`/api/v1${SUBSCRIPTIONS}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${access}` },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      }).catch(() => undefined)
    }
    await sub.unsubscribe()
  } catch (err) {
    console.warn('push unsubscribe', err)
  }
}
