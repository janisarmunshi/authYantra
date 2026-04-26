import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { tokenStorage, parseJwtPayload, isTokenExpired } from '@/utils/token'
import type { AuthUser } from '@/types'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (accessToken: string, refreshToken: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = tokenStorage.getAccessToken()
    if (token && !isTokenExpired(token)) {
      const payload = parseJwtPayload(token)
      if (payload) {
        setUser({
          user_id: payload.sub as string,
          org_id: payload.org_id as string,
          email: payload.email as string ?? '',
          roles: (payload.roles as string[]) ?? [],
        })
      }
    }
    setIsLoading(false)
  }, [])

  const login = (accessToken: string, refreshToken: string) => {
    tokenStorage.setAccessToken(accessToken)
    tokenStorage.setRefreshToken(refreshToken)
    const payload = parseJwtPayload(accessToken)
    if (payload) {
      setUser({
        user_id: payload.sub as string,
        org_id: payload.org_id as string,
        email: payload.email as string ?? '',
        roles: (payload.roles as string[]) ?? [],
      })
    }
  }

  const logout = () => {
    tokenStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
