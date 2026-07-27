import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  getCurrentFaculty,
  loginFaculty,
  logoutFaculty,
  registerFaculty,
} from '../../api/auth'
import {
  clearStoredAccessToken,
  getStoredAccessToken,
  setStoredAccessToken,
} from '../../api/authToken'
import type {
  FacultyUserResponse,
  LoginRequest,
  RegisterRequest,
} from '../../types/api'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  status: AuthStatus
  user: FacultyUserResponse | null
  login: (payload: LoginRequest) => Promise<void>
  register: (payload: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [initialAccessToken] = useState(() => getStoredAccessToken())
  const [status, setStatus] = useState<AuthStatus>(() =>
    initialAccessToken ? 'loading' : 'anonymous',
  )
  const [user, setUser] = useState<FacultyUserResponse | null>(null)

  useEffect(() => {
    if (!initialAccessToken) return

    let cancelled = false
    getCurrentFaculty()
      .then((currentUser) => {
        if (cancelled) return
        setUser(currentUser)
        setStatus('authenticated')
      })
      .catch(() => {
        if (cancelled) return
        clearStoredAccessToken()
        setUser(null)
        setStatus('anonymous')
      })
    return () => {
      cancelled = true
    }
  }, [initialAccessToken])

  const login = useCallback(async (payload: LoginRequest): Promise<void> => {
    const session = await loginFaculty(payload)
    setStoredAccessToken(session.access_token)
    setUser(session.user)
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (payload: RegisterRequest): Promise<void> => {
    const session = await registerFaculty(payload)
    setStoredAccessToken(session.access_token)
    setUser(session.user)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async (): Promise<void> => {
    try {
      if (getStoredAccessToken()) await logoutFaculty()
    } finally {
      clearStoredAccessToken()
      setUser(null)
      setStatus('anonymous')
    }
  }, [])

  const value = useMemo(
    () => ({ status, user, login, register, logout }),
    [status, user, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider.')
  return value
}

export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext)
}
