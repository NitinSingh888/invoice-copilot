import { useState } from 'react'
import { Shield, Zap, Brain, ScrollText, CheckCircle2, ArrowRight } from 'lucide-react'
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
  const msg = (err as Error)?.message ?? ''
  const m = msg.match(/^API (\d+)/)
  return m ? parseInt(m[1], 10) : 0
}

// ────────────────────────────────────────────────────────────────────────────
// Left panel — product story
// ────────────────────────────────────────────────────────────────────────────

function ProductPanel() {
  return (
    <div className="hidden lg:flex flex-col justify-between h-full bg-primary px-10 py-10 text-white relative overflow-hidden">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.04]" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
      }} />

      <div className="relative z-10">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-16">
          <svg width="32" height="32" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="7" fill="rgba(255,255,255,0.2)" />
            <rect x="7" y="6" width="14" height="16" rx="2" fill="white" fillOpacity="0.15" />
            <rect x="7" y="6" width="14" height="16" rx="2" stroke="white" strokeOpacity="0.6" strokeWidth="1.2" />
            <line x1="10" y1="11" x2="18" y2="11" stroke="white" strokeOpacity="0.7" strokeWidth="1.2" strokeLinecap="round" />
            <line x1="10" y1="14" x2="16" y2="14" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" strokeLinecap="round" />
            <line x1="10" y1="17" x2="14" y2="17" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" strokeLinecap="round" />
            <circle cx="20" cy="20" r="5" fill="rgba(255,255,255,0.2)" />
            <circle cx="20" cy="20" r="5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
            <path d="M17.5 20L19.2 21.7L22.5 18.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-lg font-semibold tracking-tight">Invoice Copilot</span>
        </div>

        {/* Hero */}
        <h2 className="text-3xl font-bold leading-tight tracking-tight mb-3">
          Your AI accounts-payable
          <br />clerk that never sleeps
        </h2>
        <p className="text-white/70 text-sm leading-relaxed max-w-[380px] mb-10">
          Hand it the invoice batch. It reads each one, matches purchase orders,
          auto-clears the safe ones, and asks you about the rest. Every action
          is logged to a tamper-proof audit trail.
        </p>

        {/* Feature cards */}
        <div className="space-y-3">
          <FeatureRow
            icon={<Zap className="h-4 w-4" />}
            title="Process in seconds"
            desc="60 invoices become a handful of decisions. The safe ones clear themselves."
          />
          <FeatureRow
            icon={<Shield className="h-4 w-4" />}
            title="Deterministic safety"
            desc="The AI reads — deterministic code decides. No LLM on the money path."
          />
          <FeatureRow
            icon={<Brain className="h-4 w-4" />}
            title="Learns from you"
            desc="Correct it the same way 3 times and it proposes a rule you approve."
          />
          <FeatureRow
            icon={<ScrollText className="h-4 w-4" />}
            title="Audit-ready"
            desc="Hash-chained event trail. Every step is provable and tamper-evident."
          />
        </div>
      </div>

      {/* Bottom stats */}
      <div className="relative z-10 flex items-center gap-6 pt-8 border-t border-white/10">
        <Stat value="350+" label="tests" />
        <Stat value="<3 min" label="per batch" />
        <Stat value="100%" label="auditable" />
        <Stat value="$0" label="to try" />
      </div>
    </div>
  )
}

function FeatureRow({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="flex gap-3 items-start">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-white/80 mt-0.5">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-white">{title}</p>
        <p className="text-xs text-white/60 leading-relaxed">{desc}</p>
      </div>
    </div>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="text-lg font-bold text-white">{value}</p>
      <p className="text-[10px] text-white/50 uppercase tracking-wider">{label}</p>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Mobile product summary (shown above form on small screens)
// ────────────────────────────────────────────────────────────────────────────

function MobileHero() {
  return (
    <div className="lg:hidden text-center mb-8">
      <div className="flex justify-center mb-4">
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
      <h1 className="text-xl font-bold text-foreground tracking-tight">Invoice Copilot</h1>
      <p className="text-sm text-muted-foreground mt-1.5 max-w-[320px] mx-auto leading-relaxed">
        AI accounts-payable assistant that reads invoices, clears the safe ones,
        and asks you about the rest.
      </p>
      <div className="flex justify-center gap-4 mt-4 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-primary" /> Deterministic safety</span>
        <span className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-primary" /> Audit trail</span>
        <span className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-primary" /> Learns from you</span>
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Main component
// ────────────────────────────────────────────────────────────────────────────

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>('login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [orgName, setOrgName] = useState('')

  const [verifyToken, setVerifyToken] = useState('')
  const [signupEmail, setSignupEmail] = useState('')

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
        switchMode('pending')
      } else if (res.verify_token) {
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
    <div className="min-h-screen flex bg-background">
      {/* Left — product panel (desktop only) */}
      <div className="hidden lg:block lg:w-[480px] xl:w-[540px] shrink-0">
        <ProductPanel />
      </div>

      {/* Right — auth form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-[400px]">
          <MobileHero />

          {/* Form card */}
          <div className="bg-card border border-border rounded-xl p-7 shadow-sm">
            {mode === 'login' && (
              <>
                <h2 className="text-lg font-semibold text-foreground mb-1">Welcome back</h2>
                <p className="text-xs text-muted-foreground mb-5">Sign in to your Invoice Copilot workspace</p>
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      disabled={busy}
                      className="h-10"
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
                      className="h-10"
                    />
                  </div>
                  {error && (
                    <p className="text-xs text-destructive leading-snug">{error}</p>
                  )}
                  <Button type="submit" className="w-full h-10" disabled={busy}>
                    {busy ? 'Signing in…' : (
                      <span className="flex items-center gap-2">
                        Sign in <ArrowRight className="h-3.5 w-3.5" />
                      </span>
                    )}
                  </Button>
                </form>
                <p className="text-xs text-muted-foreground text-center mt-5">
                  New to Invoice Copilot?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('signup')}
                    className="text-primary hover:underline font-medium"
                  >
                    Create an account
                  </button>
                </p>
              </>
            )}

            {mode === 'signup' && (
              <>
                <h2 className="text-lg font-semibold text-foreground mb-1">Get started</h2>
                <p className="text-xs text-muted-foreground mb-5">Create your workspace — the first account becomes admin</p>
                <form onSubmit={handleSignup} className="space-y-3.5">
                  <div className="space-y-1.5">
                    <Label htmlFor="signup-email">Work email</Label>
                    <Input
                      id="signup-email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      disabled={busy}
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="signup-org">Organization name</Label>
                    <Input
                      id="signup-org"
                      type="text"
                      autoComplete="organization"
                      placeholder="Your company name"
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      required
                      disabled={busy}
                      className="h-10"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
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
                        className="h-10"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="signup-confirm">Confirm</Label>
                      <Input
                        id="signup-confirm"
                        type="password"
                        autoComplete="new-password"
                        placeholder="••••••••"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        disabled={busy}
                        className="h-10"
                      />
                    </div>
                  </div>
                  {error && (
                    <p className="text-xs text-destructive leading-snug">{error}</p>
                  )}
                  {info && (
                    <p className="text-xs text-[hsl(var(--success,142_71%_45%))] leading-snug">{info}</p>
                  )}
                  <Button type="submit" className="w-full h-10" disabled={busy || !!info}>
                    {busy ? 'Creating workspace…' : (
                      <span className="flex items-center gap-2">
                        Create workspace <ArrowRight className="h-3.5 w-3.5" />
                      </span>
                    )}
                  </Button>
                </form>
                <p className="text-xs text-muted-foreground text-center mt-5">
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('login')}
                    className="text-primary hover:underline font-medium"
                  >
                    Sign in
                  </button>
                </p>
              </>
            )}

            {mode === 'verify' && (
              <>
                <h2 className="text-lg font-semibold text-foreground mb-1">Verify your email</h2>
                <p className="text-xs text-muted-foreground mb-5 leading-relaxed">
                  We&apos;ve sent a verification to <span className="font-medium text-foreground">{signupEmail}</span>.{' '}
                  <em>Demo: click below to verify instantly.</em>
                </p>
                <form onSubmit={handleVerify} className="space-y-4">
                  {error && <p className="text-xs text-destructive leading-snug">{error}</p>}
                  {info && <p className="text-xs text-[hsl(var(--success,142_71%_45%))] leading-snug">{info}</p>}
                  <Button type="submit" className="w-full h-10" disabled={busy || !!info}>
                    {busy ? 'Verifying…' : 'Verify email'}
                  </Button>
                </form>
                <p className="text-xs text-muted-foreground text-center mt-4">
                  <button type="button" onClick={() => switchMode('login')} className="text-primary hover:underline font-medium">
                    Back to sign in
                  </button>
                </p>
              </>
            )}

            {mode === 'pending' && (
              <>
                <div className="text-center py-4">
                  <div className="flex justify-center mb-3">
                    <div className="h-10 w-10 rounded-full bg-warning/10 flex items-center justify-center">
                      <Shield className="h-5 w-5 text-[hsl(var(--warning))]" />
                    </div>
                  </div>
                  <h2 className="text-lg font-semibold text-foreground mb-2">Pending approval</h2>
                  <p className="text-xs text-muted-foreground leading-relaxed max-w-[280px] mx-auto">
                    Your organization admin needs to approve your account before you can access the workspace.
                  </p>
                </div>
                <p className="text-xs text-muted-foreground text-center mt-4">
                  <button type="button" onClick={() => switchMode('login')} className="text-primary hover:underline font-medium">
                    Back to sign in
                  </button>
                </p>
              </>
            )}
          </div>

          {/* Demo hint */}
          <div className="mt-5 text-center">
            <p className="text-[11px] text-muted-foreground">
              Try the demo:{' '}
              <button
                type="button"
                onClick={() => {
                  setEmail('demo@example.com')
                  setPassword('demo1234')
                  switchMode('login')
                }}
                className="font-mono text-[11px] text-primary hover:underline"
              >
                demo@example.com / demo1234
              </button>
            </p>
          </div>

          {/* Trust signals */}
          <div className="mt-6 flex justify-center gap-6 text-[10px] text-muted-foreground/60">
            <span>SOX-ready audit</span>
            <span>Multi-tenant</span>
            <span>No real money moved</span>
          </div>
        </div>
      </div>
    </div>
  )
}
