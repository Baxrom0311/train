import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { fetchMe, login as apiLogin, register as apiRegister, tokens } from '@/lib/api'
import type { Me } from '@/lib/types'

interface AuthContextType {
  user: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<Me | null>
  register: (fullName: string, email: string, password: string) => Promise<void>
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
      return me
    } catch {
      tokens.clear()
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tokens.access) loadMe()
  }, [loadMe])

  const login = async (email: string, password: string) => {
    await apiLogin(email, password)
    return loadMe()
  }

  const register = async (fullName: string, email: string, password: string) => {
    await apiRegister(fullName, email, password)
    await loadMe()
  }

  const logout = () => {
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

/** Ruxsat yo'q bo'lsa — bosh sahifaga (backend baribir 403 qaytaradi). */
export function RequirePermission({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { can } = useAuth()
  return (
    <RequireAuth>
      {can(permission) ? children : <Navigate to="/dashboard" replace />}
    </RequireAuth>
  )
}

/** Kirgandan keyingi bosh sahifa: kompaniya xodimi — nomzodlar, talaba — simulyatsiyalar. */
export function homeFor(user: Me | null): string {
  return user?.permissions.includes('view_candidates') ? '/talents' : '/simulations'
}
