// Backend API mijozi: JWT (access + refresh) localStorage'da, 401 bo'lsa bir marta refresh.
import type { Me } from './types'

const BASE = '/api/v1'
const ACCESS = 'tj_access'
const REFRESH = 'tj_refresh'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS, access)
    localStorage.setItem(REFRESH, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS)
    localStorage.removeItem(REFRESH)
  },
}

let refreshing: Promise<boolean> | null = null

/** Bir vaqtda bir nechta 401 kelsa ham refresh bitta so'rov bo'ladi. */
export function refreshTokens(): Promise<boolean> {
  refreshing ??= (async () => {
    const refresh = localStorage.getItem(REFRESH)
    if (!refresh) return false
    const r = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!r.ok) {
      tokens.clear()
      return false
    }
    const data = await r.json()
    tokens.set(data.access_token, data.refresh_token)
    return true
  })().finally(() => {
    refreshing = null
  })
  return refreshing
}

export function authHeaders(): Record<string, string> {
  const access = tokens.access
  return access ? { Authorization: `Bearer ${access}` } : {}
}

function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join('; ')
  return fallback
}

type Options = Omit<RequestInit, 'body'> & { json?: unknown; body?: BodyInit }

export async function api<T>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const { json, headers, ...rest } = opts
  const init: RequestInit = {
    ...rest,
    headers: {
      ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...authHeaders(),
      ...(headers as Record<string, string> | undefined),
    },
    body: json !== undefined ? JSON.stringify(json) : opts.body,
  }
  const r = await fetch(`${BASE}${path}`, init)
  if (r.status === 401 && !retried && (await refreshTokens())) {
    return api<T>(path, opts, true)
  }
  const body = r.status === 204 ? null : await r.json().catch(() => null)
  if (!r.ok) throw new ApiError(r.status, errorMessage(body, r.statusText))
  return body as T
}

export async function login(email: string, password: string): Promise<void> {
  const form = new URLSearchParams({ username: email, password })
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  })
  const body = await r.json().catch(() => null)
  if (!r.ok) throw new ApiError(r.status, errorMessage(body, r.statusText))
  tokens.set(body.access_token, body.refresh_token)
}

export async function register(fullName: string, email: string, password: string): Promise<void> {
  const body = await api<{ access_token: string; refresh_token: string }>('/auth/register', {
    method: 'POST',
    json: { full_name: fullName, email, password },
  })
  tokens.set(body.access_token, body.refresh_token)
}

export const fetchMe = () => api<Me>('/users/me')

export async function uploadFile(file: File, runId: string) {
  const form = new FormData()
  form.append('file', file)
  form.append('run_id', runId)
  return api<{ id: string; original_name: string }>('/files', { method: 'POST', body: form })
}
