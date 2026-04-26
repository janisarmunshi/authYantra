const ACCESS_TOKEN_KEY = 'authyantra_access_token'
const REFRESH_TOKEN_KEY = 'authyantra_refresh_token'
const ORG_ID_KEY = 'authyantra_org_id'

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  setAccessToken: (token: string) => localStorage.setItem(ACCESS_TOKEN_KEY, token),
  removeAccessToken: () => localStorage.removeItem(ACCESS_TOKEN_KEY),

  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setRefreshToken: (token: string) => localStorage.setItem(REFRESH_TOKEN_KEY, token),
  removeRefreshToken: () => localStorage.removeItem(REFRESH_TOKEN_KEY),

  getOrgId: () => localStorage.getItem(ORG_ID_KEY),
  setOrgId: (orgId: string) => localStorage.setItem(ORG_ID_KEY, orgId),
  removeOrgId: () => localStorage.removeItem(ORG_ID_KEY),

  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(ORG_ID_KEY)
  },
}

export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') return true
  return Date.now() / 1000 > payload.exp - 30 // 30s buffer
}
