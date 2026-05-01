import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { tokenStorage, parseJwtPayload, isTokenExpired } from '@/utils/token'
import type { AuthUser, OrgSummary } from '@/types'

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  // Set after login when the user has multiple orgs and no default
  pendingOrgSelection: OrgSummary[] | null
  login: (accessToken: string, refreshToken: string) => void
  completeOrgSelection: (accessToken: string, refreshToken: string) => void
  setPendingOrgs: (orgs: OrgSummary[]) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function userFromToken(token: string): AuthUser | null {
  const payload = parseJwtPayload(token)
  if (!payload) return null
  return {
    user_id: payload.sub as string,
    org_id: (payload.org_id as string) ?? null,
    email: (payload.email as string) ?? '',
    roles: (payload.roles as string[]) ?? [],
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [pendingOrgSelection, setPendingOrgSelectionState] = useState<OrgSummary[] | null>(null)

  useEffect(() => {
    const token = tokenStorage.getAccessToken()
    if (token && !isTokenExpired(token)) {
      setUser(userFromToken(token))
    }
    setIsLoading(false)
  }, [])

  const login = (accessToken: string, refreshToken: string) => {
    tokenStorage.setAccessToken(accessToken)
    tokenStorage.setRefreshToken(refreshToken)
    setUser(userFromToken(accessToken))
    setPendingOrgSelectionState(null)
  }

  const completeOrgSelection = (accessToken: string, refreshToken: string) => {
    tokenStorage.setAccessToken(accessToken)
    tokenStorage.setRefreshToken(refreshToken)
    setUser(userFromToken(accessToken))
    setPendingOrgSelectionState(null)
  }

  const setPendingOrgs = (orgs: OrgSummary[]) => {
    setPendingOrgSelectionState(orgs)
  }

  const logout = () => {
    tokenStorage.clear()
    setUser(null)
    setPendingOrgSelectionState(null)
  }

  return (
    <AuthContext.Provider value={{
      user, isAuthenticated: !!user, isLoading,
      pendingOrgSelection,
      login, completeOrgSelection, setPendingOrgs, logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
