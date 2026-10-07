import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { ApiError, fetchMe, login as apiLogin, register as apiRegister, tokens, type StudentSignup } from '@/lib/api'
import { forgetPush } from '@/lib/pwa'
import type { Me } from '@/lib/types'

interface AuthContextType {
  user: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<Me | null>
  register: (data: StudentSignup) => Promise<void>
  logout: () => void
  /** Ruxsat bo'yicha tekshiruv (CONTRACT.md §10.3) — rol nomi bo'yicha emas. */
  can: (permission: string) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [loading, setLoading] = useState(() => Boolean(tokens.access))

  const loadMe = useCallback(async (): Promise<Me | null> => {
    try {
      const me = await fetchMe()
      setUser(me)
      setLoading(false)
      return me
    } catch (err) {
      if (err instanceof ApiError) {
        tokens.clear()
        setUser(null)
        setLoading(false)
        return null
      }
      // tarmoq yo'q (ilova oflayn ochildi, §22.1) — sessiya saqlanadi, aloqa qaytgach qayta urinamiz;
      // shu orada sahifa "yuklanmoqda" holatida (yuqorida "Internet yo'q" yo'lagi)
      const retry = () => {
        window.removeEventListener('online', retry)
        clearTimeout(timer)
        loadMe().catch(() => undefined)
      }
      window.addEventListener('online', retry)
      const timer = setTimeout(retry, 15_000)
      throw err
    }
  }, [])

  useEffect(() => {
    if (tokens.access) loadMe().catch(() => undefined)
  }, [loadMe])

  const login = async (email: string, password: string) => {
    await apiLogin(email, password)
    return loadMe()
  }

  const register = async (data: StudentSignup) => {
    await apiRegister(data)
    await loadMe()
  }

  const logout = () => {
    void forgetPush(tokens.access)                         // push bu brauzerga endi kelmasin (§22.2)
    tokens.clear()
    setUser(null)
  }

  const can = useCallback((permission: string) => Boolean(user?.permissions.includes(permission)), [user])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, can }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <>{children}</>
}

/** Ruxsatlardan kamida bittasi kerak; yo'q bo'lsa — o'z bosh sahifasiga (backend baribir 403 qaytaradi). */
export function RequirePermission({ permission, children }: { permission: string | string[]; children: React.ReactNode }) {
  const { user, can } = useAuth()
  const allowed = (Array.isArray(permission) ? permission : [permission]).some(can)
  return (
    <RequireAuth>
      {allowed ? children : <Navigate to={homeFor(user)} replace />}
    </RequireAuth>
  )
}

/** Kirgandan keyingi bosh sahifa ruxsatga qarab (CONTRACT.md §11.4). */
export function homeFor(user: Me | null): string {
  const has = (p: string) => Boolean(user?.permissions.includes(p))
  if (has('approve_companies') || has('manage_billing')) return '/admin'
  if (has('view_candidates')) return '/talents'
  if (has('manage_universities')) return '/university'
  if (has('view_org_invoices')) return '/billing'
  return '/simulations'
}
