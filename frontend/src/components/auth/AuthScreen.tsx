import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authLogin, authSignup, authVerify, setToken } from '@/lib/api'

type Mode = 'login' | 'signup' | 'verify' | 'pending'

interface AuthScreenProps {
  onAuthenticated: (email: string) => void
}

function getApiStatus(err: unknown): number {
  if (err && typeof err === 'object' && 'status' in err) {
    return (err as { status: number }).status
  }
  // parse from message string like "API 403: ..."
  const msg = (err as Error)?.message ?? ''
  const m = msg.match(/^API (\d+)/)
  return m ? parseInt(m[1], 10) : 0
}

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>('login')

  // shared fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [orgName, setOrgName] = useState('')

  // verify state (returned from signup)
  const [verifyToken, setVerifyToken] = useState('')
  const [signupEmail, setSignupEmail] = useState('')

  // ui state
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  function switchMode(next: Mode) {
    setMode(next)
    setError('')
    setInfo('')
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setError('')
    setBusy(true)
    try {
      const res = await authLogin(email.trim(), password)
      setToken(res.access_token)
      onAuthenticated(email.trim())
    } catch (err) {
      const status = getApiStatus(err)
      if (status === 403) {
        setError('Your account is pending admin approval.')
      } else if (status === 401) {
        setError('Wrong email or password.')
      } else {
        setError('Login failed. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setError('')
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    if (!orgName.trim()) {
      setError('Organization name is required.')
      return
    }
    setBusy(true)
    try {
      const res = await authSignup(email.trim(), password, orgName.trim())
      if (res.status === 'active') {
        // Founder of a new org — can log in right away
        setInfo('Account created — you can log in now.')
        const savedEmail = email.trim()
        setPassword('')
        setConfirmPassword('')
        setOrgName('')
        setTimeout(() => {
          setInfo('')
          setEmail(savedEmail)
          switchMode('login')
        }, 1500)
      } else if (res.status === 'pending') {
        // Joined an existing org — needs admin approval
        switchMode('pending')
      } else if (res.verify_token) {
        // Legacy verify flow (fallback)
        setVerifyToken(res.verify_token)
        setSignupEmail(email.trim())
        setMode('verify')
      } else {
        setInfo('Account created — you can log in now.')
        const savedEmail = email.trim()
        setPassword('')
        setConfirmPassword('')
        setOrgName('')
        setTimeout(() => {
          setInfo('')
          setEmail(savedEmail)
          switchMode('login')
        }, 1500)
      }
    } catch (err) {
      const status = getApiStatus(err)
      if (status === 409) {
        setError('An account with that email already exists. Try logging in.')
      } else {
        setError('Sign up failed. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setError('')
    setBusy(true)
    try {
      await authVerify(verifyToken)
      setInfo('Verified! You can now log in.')
      // pre-fill login with the signup email
      setEmail(signupEmail)
      setPassword('')
      setConfirmPassword('')
      setTimeout(() => {
        setInfo('')
        switchMode('login')
      }, 1500)
    } catch {
      setError('Verification failed. The token may be invalid or expired.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-[360px]">
        {/* Logo + brand */}
        <div className="flex flex-col items-center mb-8">
          <div className="mb-4">
            <svg width="44" height="44" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="28" height="28" rx="7" fill="hsl(var(--primary))" />
              <rect x="7" y="6" width="14" height="16" rx="2" fill="white" fillOpacity="0.15" />
              <rect x="7" y="6" width="14" height="16" rx="2" stroke="white" strokeOpacity="0.6" strokeWidth="1.2" />
              <line x1="10" y1="11" x2="18" y2="11" stroke="white" strokeOpacity="0.7" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="10" y1="14" x2="16" y2="14" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="10" y1="17" x2="14" y2="17" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" strokeLinecap="round" />
              <circle cx="20" cy="20" r="5" fill="hsl(var(--primary))" />
              <circle cx="20" cy="20" r="5" stroke="hsl(var(--card))" strokeWidth="1.5" />
              <path d="M17.5 20L19.2 21.7L22.5 18.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight">Invoice Copilot</h1>
          <p className="text-xs text-muted-foreground mt-1">AI accounts-payable assistant</p>
        </div>

        {/* Card */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          {mode === 'login' && (
            <>
              <h2 className="text-sm font-semibold text-foreground mb-4">Log in to your account</h2>
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="login-email">Email</Label>
                  <Input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={busy}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="login-password">Password</Label>
                  <Input
                    id="login-password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={busy}
                    className="h-9"
                  />
                </div>
                {error && (
                  <p className="text-xs text-destructive leading-snug">{error}</p>
                )}
                <Button type="submit" className="w-full" disabled={busy}>
                  {busy ? 'Logging in…' : 'Log in'}
                </Button>
              </form>
              <p className="text-xs text-muted-foreground text-center mt-4">
                No account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signup')}
                  className="text-primary hover:underline font-medium"
                >
                  Sign up
                </button>
              </p>
            </>
          )}

          {mode === 'signup' && (
            <>
              <h2 className="text-sm font-semibold text-foreground mb-4">Create an account</h2>
              <form onSubmit={handleSignup} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="signup-email">Email</Label>
                  <Input
                    id="signup-email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={busy}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="signup-org">Organization</Label>
                  <Input
                    id="signup-org"
                    type="text"
                    autoComplete="organization"
                    placeholder="Acme Corp"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    required
                    disabled={busy}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="signup-password">Password</Label>
                  <Input
                    id="signup-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={busy}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="signup-confirm">Confirm password</Label>
                  <Input
                    id="signup-confirm"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={busy}
                    className="h-9"
                  />
                </div>
                {error && (
                  <p className="text-xs text-destructive leading-snug">{error}</p>
                )}
                {info && (
                  <p className="text-xs text-[hsl(var(--success,142_71%_45%))] leading-snug">{info}</p>
                )}
                <Button type="submit" className="w-full" disabled={busy || !!info}>
                  {busy ? 'Creating account…' : 'Sign up'}
                </Button>
              </form>
              <p className="text-xs text-muted-foreground text-center mt-4">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="text-primary hover:underline font-medium"
                >
                  Log in
                </button>
              </p>
            </>
          )}

          {mode === 'verify' && (
            <>
              <h2 className="text-sm font-semibold text-foreground mb-1">Verify your email</h2>
              <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                We&apos;ve sent a verification link to <span className="font-medium text-foreground">{signupEmail}</span>.{' '}
                <em>Demo: no real email — click the button below to verify instantly.</em>
              </p>
              <form onSubmit={handleVerify} className="space-y-4">
                {error && (
                  <p className="text-xs text-destructive leading-snug">{error}</p>
                )}
                {info && (
                  <p className="text-xs text-[hsl(var(--success,142_71%_45%))] leading-snug">{info}</p>
                )}
                <Button type="submit" className="w-full" disabled={busy || !!info}>
                  {busy ? 'Verifying…' : 'Verify email'}
                </Button>
              </form>
              <p className="text-xs text-muted-foreground text-center mt-4">
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="text-primary hover:underline font-medium"
                >
                  Back to log in
                </button>
              </p>
            </>
          )}

          {mode === 'pending' && (
            <>
              <h2 className="text-sm font-semibold text-foreground mb-3">Account pending approval</h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                Your account is pending your organization admin&apos;s approval. You&apos;ll get access once they approve you.
              </p>
              <p className="text-xs text-muted-foreground text-center">
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="text-primary hover:underline font-medium"
                >
                  Back to log in
                </button>
              </p>
            </>
          )}
        </div>

        {/* Demo hint */}
        <div className="mt-4 text-center">
          <p className="text-xs text-muted-foreground">
            Try the demo:{' '}
            <button
              type="button"
              onClick={() => {
                setEmail('demo@zamp.ai')
                setPassword('demo1234')
                switchMode('login')
              }}
              className="font-mono text-[11px] text-primary hover:underline"
            >
              demo@zamp.ai / demo1234
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
