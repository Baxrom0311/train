// Brauzer xatolarini serverga yuborish (CONTRACT.md §32.4). Hech qachon o'zi xato tashlamaydi.
import { ApiError } from './api'

export type ClientErrorKind = 'error' | 'unhandledrejection' | 'render'

const ENDPOINT = '/api/v1/client-errors'
const MAX_PER_PAGE = 10
const MESSAGE_MAX = 500
const STACK_MAX = 8000

const seen = new Set<string>()

function describe(error: unknown): { message: string; stack: string } {
  if (error instanceof Error) {
    return { message: `${error.name}: ${error.message}`, stack: error.stack ?? '' }
  }
  if (typeof error === 'string') return { message: error, stack: '' }
  try {
    return { message: JSON.stringify(error) ?? String(error), stack: '' }
  } catch {
    return { message: String(error), stack: '' }
  }
}

/** Bir sahifa yuklanishida bir xil xato bir marta, jami ≤ 10 ta; kengaytmalar xatosi yuborilmaydi. */
export function reportError(kind: ClientErrorKind, error: unknown, extraStack = ''): void {
  try {
    const { message, stack: own } = describe(error)
    const stack = [own, extraStack].filter(Boolean).join('\n')
    if (!message.trim() || /-extension:\/\//.test(stack)) return
    const key = `${kind}|${message}|${stack.split('\n', 2)[1] ?? ''}`
    if (seen.has(key) || seen.size >= MAX_PER_PAGE) return
    seen.add(key)
    void fetch(ENDPOINT, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kind,
        message: message.slice(0, MESSAGE_MAX),
        stack: stack.slice(0, STACK_MAX),
        path: window.location.pathname.slice(0, 300),
      }),
    }).catch(() => {})
  } catch {
    // kuzatuv ilovani hech qachon buzmaydi
  }
}

export function setupMonitoring(): void {
  window.addEventListener('error', (e: ErrorEvent) => {
    // boshqa domendagi skript — brauzer tafsilotni yashiradi, foydasiz
    if (!e.error && (!e.message || e.message === 'Script error.')) return
    reportError('error', e.error ?? e.message)
  })
  window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
    // server javobi xatosi — 5xx backend'da yig'ilgan, 4xx kutilgan holat
    if (e.reason instanceof ApiError) return
    reportError('unhandledrejection', e.reason)
  })
}
