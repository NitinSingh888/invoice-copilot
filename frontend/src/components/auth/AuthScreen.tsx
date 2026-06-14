import { useState } from 'react'
import { Shield, ArrowRight, Lock, FileCheck, TrendingUp } from 'lucide-react'
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
// Left panel — dark, premium product story
// ────────────────────────────────────────────────────────────────────────────

function ProductPanel() {
  return (
    <div className="hidden lg:flex flex-col justify-between h-full px-12 py-10 text-white relative overflow-hidden"
      style={{ background: 'linear-gradient(175deg, #0f1117 0%, #161922 50%, #111827 100%)' }}
    >
      {/* Subtle dot pattern for texture */}
      <div className="absolute inset-0 opacity-[0.035]" style={{
        backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }} />

      {/* Soft gradient glow — top-right corner */}
      <div className="absolute -top-32 -right-32 w-[400px] h-[400px] rounded-full opacity-[0.06]"
        style={{ background: 'radial-gradient(circle, #5b8def 0%, transparent 70%)' }} />

      <div className="relative z-10 flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-auto">
          <div className="h-8 w-8 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="2" y="1" width="10" height="13" rx="1.5" stroke="white" strokeOpacity="0.7" strokeWidth="1.2" />
              <line x1="4.5" y1="5" x2="9.5" y2="5" stroke="white" strokeOpacity="0.5" strokeWidth="1" strokeLinecap="round" />
              <line x1="4.5" y1="7.5" x2="8" y2="7.5" stroke="white" strokeOpacity="0.35" strokeWidth="1" strokeLinecap="round" />
              <line x1="4.5" y1="10" x2="7" y2="10" stroke="white" strokeOpacity="0.35" strokeWidth="1" strokeLinecap="round" />
              <circle cx="13" cy="13" r="4" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" />
              <path d="M11.2 13L12.4 14.2L14.8 11.8" stroke="white" strokeOpacity="0.8" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-white/90">Invoice Copilot</span>
        </div>

        {/* Center content — hero + features */}
        <div className="flex-1 flex flex-col justify-center -mt-8">
          <h2 className="text-[28px] font-semibold leading-[1.2] tracking-tight mb-3 text-white/95">
            Accounts payable
            <br />on autopilot.
          </h2>
          <p className="text-[13px] text-white/45 leading-relaxed max-w-[340px] mb-10">
            Invoice Copilot reads every invoice, matches POs, auto-clears safe
            payments, and surfaces the rest for your review. Every action logged
            to a tamper-proof audit trail.
          </p>

          {/* Feature list — clean, compact */}
          <div className="space-y-4">
            <FeatureRow
              icon={<TrendingUp className="h-[14px] w-[14px]" />}
              title="60 invoices, minutes not hours"
              desc="Safe ones clear themselves. You handle the exceptions."
            />
            <FeatureRow
              icon={<Lock className="h-[14px] w-[14px]" />}
              title="Deterministic safety"
              desc="AI reads. Deterministic code decides. No LLM on the money path."
            />
            <FeatureRow
              icon={<FileCheck className="h-[14px] w-[14px]" />}
              title="Audit-ready from day one"
              desc="Hash-chained event trail. Every step provable and tamper-evident."
            />
          </div>
        </div>

        {/* Testimonial / social proof */}
        <div className="relative z-10 pt-8 mt-auto"
          style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <p className="text-[13px] text-white/50 leading-relaxed italic">
            &ldquo;We went from 4 hours of invoice processing to 20 minutes.
            The audit trail alone paid for the switch.&rdquo;
          </p>
          <div className="flex items-center gap-3 mt-4">
            <div className="h-8 w-8 rounded-full flex items-center justify-center text-[11px] font-semibold"
              style={{ background: 'rgba(91,141,239,0.15)', color: 'rgba(91,141,239,0.8)' }}>
              JM
            </div>
            <div>
              <p className="text-[12px] text-white/70 font-medium">Jamie Mitchell</p>
              <p className="text-[11px] text-white/35">Head of Finance, Aero Systems</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function FeatureRow({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="flex gap-3 items-start">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md mt-0.5"
        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.05)' }}>
        <span className="text-white/50">{icon}</span>
      </div>
      <div>
        <p className="text-[13px] font-medium text-white/80 leading-snug">{title}</p>
        <p className="text-[12px] text-white/35 leading-relaxed mt-0.5">{desc}</p>
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Mobile header (shown above form on small screens)
// ────────────────────────────────────────────────────────────────────────────

function MobileHeader() {
  return (
    <div className="lg:hidden flex flex-col items-center mb-8">
      <div className="h-10 w-10 rounded-xl flex items-center justify-center bg-primary mb-3">
        <svg width="20" height="20" viewBox="0 0 18 18" fill="none">
          <rect x="2" y="1" width="10" height="13" rx="1.5" stroke="white" strokeOpacity="0.9" strokeWidth="1.2" />
          <line x1="4.5" y1="5" x2="9.5" y2="5" stroke="white" strokeOpacity="0.7" strokeWidth="1" strokeLinecap="round" />
          <line x1="4.5" y1="7.5" x2="8" y2="7.5" stroke="white" strokeOpacity="0.5" strokeWidth="1" strokeLinecap="round" />
          <circle cx="13" cy="13" r="4" stroke="white" strokeOpacity="0.7" strokeWidth="1.2" />
          <path d="M11.2 13L12.4 14.2L14.8 11.8" stroke="white" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <h1 className="text-lg font-semibold text-foreground tracking-tight">Invoice Copilot</h1>
      <p className="text-[13px] text-muted-foreground mt-1 text-center max-w-[300px]">
        AI-powered accounts payable that processes invoices in minutes.
      </p>
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
      {/* Left — dark product panel (desktop only) */}
      <div className="hidden lg:block lg:w-[480px] xl:w-[520px] shrink-0">
        <ProductPanel />
      </div>

      {/* Right — auth form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 relative">
        {/* Subtle background texture on right side */}
        <div className="absolute inset-0 opacity-[0.02]" style={{
          backgroundImage: 'radial-gradient(circle, hsl(var(--foreground)) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }} />

        <div className="w-full max-w-[380px] relative z-10">
          <MobileHeader />

          {/* Form heading — outside the card for visual hierarchy */}
          {mode === 'login' && (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-foreground tracking-tight">Welcome back</h2>
              <p className="text-[13px] text-muted-foreground mt-1">Sign in to your Invoice Copilot workspace</p>
            </div>
          )}
          {mode === 'signup' && (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-foreground tracking-tight">Create your workspace</h2>
              <p className="text-[13px] text-muted-foreground mt-1">The first account becomes the admin</p>
            </div>
          )}
          {mode === 'verify' && (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-foreground tracking-tight">Verify your email</h2>
              <p className="text-[13px] text-muted-foreground mt-1 leading-relaxed">
                We&apos;ve sent a verification to <span className="font-medium text-foreground">{signupEmail}</span>.{' '}
                <span className="text-muted-foreground/70">Demo: click below to verify instantly.</span>
              </p>
            </div>
          )}
          {mode === 'pending' && (
            <div className="mb-6">
              <div className="h-10 w-10 rounded-full bg-warning/10 flex items-center justify-center mb-3">
                <Shield className="h-5 w-5 text-warning" />
              </div>
              <h2 className="text-xl font-semibold text-foreground tracking-tight">Pending approval</h2>
              <p className="text-[13px] text-muted-foreground mt-1 leading-relaxed max-w-[320px]">
                Your organization admin needs to approve your account before you can access the workspace.
              </p>
            </div>
          )}

          {/* Form area */}
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="login-email" className="text-[13px]">Email</Label>
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={busy}
                  className="h-10 bg-card"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="login-password" className="text-[13px]">Password</Label>
                <Input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={busy}
                  className="h-10 bg-card"
                />
              </div>
              {error && (
                <p className="text-[13px] text-destructive leading-snug">{error}</p>
              )}
              <Button type="submit" className="w-full h-10 mt-2" disabled={busy}>
                {busy ? 'Signing in\u2026' : (
                  <span className="flex items-center gap-2">
                    Sign in <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                )}
              </Button>
            </form>
          )}

          {mode === 'signup' && (
            <form onSubmit={handleSignup} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="signup-email" className="text-[13px]">Work email</Label>
                <Input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={busy}
                  className="h-10 bg-card"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="signup-org" className="text-[13px]">Organization name</Label>
                <Input
                  id="signup-org"
                  type="text"
                  autoComplete="organization"
                  placeholder="Your company name"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                  disabled={busy}
                  className="h-10 bg-card"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="signup-password" className="text-[13px]">Password</Label>
                  <Input
                    id="signup-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="6+ characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={busy}
                    className="h-10 bg-card"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="signup-confirm" className="text-[13px]">Confirm</Label>
                  <Input
                    id="signup-confirm"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Re-enter"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={busy}
                    className="h-10 bg-card"
                  />
                </div>
              </div>
              {error && (
                <p className="text-[13px] text-destructive leading-snug">{error}</p>
              )}
              {info && (
                <p className="text-[13px] text-success leading-snug">{info}</p>
              )}
              <Button type="submit" className="w-full h-10 mt-2" disabled={busy || !!info}>
                {busy ? 'Creating workspace\u2026' : (
                  <span className="flex items-center gap-2">
                    Create workspace <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                )}
              </Button>
            </form>
          )}

          {mode === 'verify' && (
            <form onSubmit={handleVerify} className="space-y-4">
              {error && <p className="text-[13px] text-destructive leading-snug">{error}</p>}
              {info && <p className="text-[13px] text-success leading-snug">{info}</p>}
              <Button type="submit" className="w-full h-10" disabled={busy || !!info}>
                {busy ? 'Verifying\u2026' : 'Verify email'}
              </Button>
            </form>
          )}

          {mode === 'pending' && null}

          {/* Mode switch link */}
          {mode === 'login' && (
            <p className="text-[13px] text-muted-foreground text-center mt-6">
              New to Invoice Copilot?{' '}
              <button
                type="button"
                onClick={() => switchMode('signup')}
                className="text-primary hover:underline font-medium"
              >
                Create an account
              </button>
            </p>
          )}
          {mode === 'signup' && (
            <p className="text-[13px] text-muted-foreground text-center mt-6">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => switchMode('login')}
                className="text-primary hover:underline font-medium"
              >
                Sign in
              </button>
            </p>
          )}
          {(mode === 'verify' || mode === 'pending') && (
            <p className="text-[13px] text-muted-foreground text-center mt-6">
              <button type="button" onClick={() => switchMode('login')} className="text-primary hover:underline font-medium">
                Back to sign in
              </button>
            </p>
          )}

          {/* Trust signals — subtle, integrated */}
          <div className="mt-10 flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground/40">
            <Lock className="h-3 w-3" />
            <span>SOX-ready audit trail</span>
            <span className="mx-1.5">&middot;</span>
            <span>Multi-tenant</span>
            <span className="mx-1.5">&middot;</span>
            <span>No real money moved</span>
          </div>
        </div>
      </div>
    </div>
  )
}
