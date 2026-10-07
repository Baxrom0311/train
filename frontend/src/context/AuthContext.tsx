import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { fetchMe, login as apiLogin, register as apiRegister, tokens } from '@/lib/api'
import type { Me } from '@/lib/types'

interface AuthContextType {
  user: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (fullName: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [loading, setLoading] = useState(() => Boolean(tokens.access))

  const loadMe = useCallback(async () => {
    try {
      setUser(await fetchMe())
    } catch {
      tokens.clear()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tokens.access) loadMe()
  }, [loadMe])

  const login = async (email: string, password: string) => {
    await apiLogin(email, password)
    await loadMe()
  }

  const register = async (fullName: string, email: string, password: string) => {
    await apiRegister(fullName, email, password)
    await loadMe()
  }

  const logout = () => {
    tokens.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
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
