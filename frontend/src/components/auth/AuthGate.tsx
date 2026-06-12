import { useEffect, useState, type ReactNode } from 'react'
import { authMe, clearToken, getToken } from '@/lib/api'
import { AuthScreen } from './AuthScreen'
import type { OrgRole } from '@/lib/types'

export interface UserInfo {
  email: string
  orgName: string | null
  orgRole: OrgRole | null
}

interface AuthGateProps {
  children: (user: UserInfo) => ReactNode
}

type State = 'checking' | 'authenticated' | 'unauthenticated'

export function AuthGate({ children }: AuthGateProps) {
  const [state, setState] = useState<State>('checking')
  const [userInfo, setUserInfo] = useState<UserInfo>({ email: '', orgName: null, orgRole: null })

  useEffect(() => {
    let cancelled = false

    async function checkAuth() {
      const token = getToken()
      if (!token) {
        if (!cancelled) setState('unauthenticated')
        return
      }
      try {
        const me = await authMe()
        if (!cancelled) {
          setUserInfo({
            email: me.email,
            orgName: me.org_name ?? null,
            orgRole: (me.role as OrgRole | null) ?? null,
          })
          setState('authenticated')
        }
      } catch {
        clearToken()
        if (!cancelled) setState('unauthenticated')
      }
    }

    void checkAuth()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    function onUnauthorized() {
      clearToken()
      setUserInfo({ email: '', orgName: null, orgRole: null })
      setState('unauthenticated')
    }
    window.addEventListener('ic-unauthorized', onUnauthorized)
    return () => window.removeEventListener('ic-unauthorized', onUnauthorized)
  }, [])

  async function handleAuthenticated(email: string) {
    // Fetch full me info after login
    try {
      const me = await authMe()
      setUserInfo({
        email: me.email,
        orgName: me.org_name ?? null,
        orgRole: (me.role as OrgRole | null) ?? null,
      })
    } catch {
      setUserInfo({ email, orgName: null, orgRole: null })
    }
    setState('authenticated')
  }

  if (state === 'checking') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <svg
            className="animate-spin h-4 w-4 text-primary"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Loading…
        </div>
      </div>
    )
  }

  if (state === 'unauthenticated') {
    return <AuthScreen onAuthenticated={handleAuthenticated} />
  }

  // Pass user info down to children via render prop
  return <>{children(userInfo)}</>
}
