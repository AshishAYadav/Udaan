import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authService, setUnauthorizedHandler, tokenStore } from '../services/api'

const AuthContext = createContext(null)

// Reads the (unverified) JWT payload for display and UI gating; the backend enforces access.
function decode(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return payload.exp * 1000 > Date.now() ? payload : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [claims, setClaims] = useState(() => decode(tokenStore.get() || ''))

  const logout = useCallback(() => {
    tokenStore.clear()
    setClaims(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!claims) tokenStore.clear()
  }, [claims, logout])

  const login = useCallback(async (username, password) => {
    const { access_token: token } = await authService.login(username, password)
    tokenStore.set(token)
    setClaims(decode(token))
  }, [])

  const value = useMemo(() => {
    const scopes = claims?.scope?.split(' ') || []
    return {
      user: claims && { id: claims.sub, username: claims.username, name: claims.name, role: claims.role, tier: claims.tier },
      scopes,
      hasScope: (scope) => scopes.includes(scope),
      isAdmin: claims?.role === 'ADMIN',
      login,
      logout,
    }
  }, [claims, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
