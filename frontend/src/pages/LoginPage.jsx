import { AlertCircle, ArrowRight, Loader2, Lock, ShieldCheck, User } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState('')

  // If already logged in, redirect to app
  if (user) {
    return <Navigate to="/app/customers" replace />
  }

  async function handleSubmit(e) {
    if (e) e.preventDefault()
    if (!email || !password) {
      setError('Please enter both email and password.')
      return
    }

    setIsBusy(true)
    setError('')
    try {
      await login(email, password)
      navigate('/app/customers', { replace: true })
    } catch (err) {
      setError(err.message || 'Invalid credentials.')
    } finally {
      setIsBusy(false)
    }
  }

  function handleDemoLogin() {
    setEmail('csm@nexus.ai')
    setPassword('Password123!')
    setIsBusy(true)
    setError('')
    login('csm@nexus.ai', 'Password123!')
      .then(() => navigate('/app/customers', { replace: true }))
      .catch((err) => setError(err.message))
      .finally(() => setIsBusy(false))
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center">
          <Link to="/" className="font-display text-3xl font-medium tracking-tight text-ink">
            Nexus AI
          </Link>
          <p className="mt-1 text-sm text-muted">
            Agentic Customer Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-line bg-surface p-8 shadow-xs">
          <h1 className="font-display text-xl font-medium text-ink">
            Sign in to your account
          </h1>
          <p className="mt-1 text-xs text-muted">
            Enter your credentials to access customer intelligence & retention workflows.
          </p>

          {/* Quick Demo Login Pill */}
          <div className="mt-4 rounded-lg border border-accent/20 bg-accent/5 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs font-medium text-accent">
                <ShieldCheck size={16} />
                <span>Default Demo Account</span>
              </div>
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isBusy}
                className="inline-flex items-center gap-1 rounded bg-accent px-2.5 py-1 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                1-Click Sign In
                <ArrowRight size={12} />
              </button>
            </div>
            <p className="mt-1 text-[11px] text-muted">
              Pre-filled with seeded manager credentials: <code className="text-ink">csm@nexus.ai</code>
            </p>
          </div>

          {error && (
            <div role="alert" className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-900">
              <AlertCircle size={15} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-ink">
                Email address
              </label>
              <div className="relative mt-1">
                <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="csm@nexus.ai"
                  className="w-full rounded-lg border border-line bg-paper py-2 pl-9 pr-3 text-sm text-ink outline-hidden focus:border-accent"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-ink">
                Password
              </label>
              <div className="relative mt-1">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full rounded-lg border border-line bg-paper py-2 pl-9 pr-3 text-sm text-ink outline-hidden focus:border-accent"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isBusy}
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-ink py-2.5 text-sm font-medium text-paper shadow-2xs hover:bg-neutral-800 disabled:opacity-50"
            >
              {isBusy ? <Loader2 size={16} className="animate-spin" /> : null}
              {isBusy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        {/* Footer info */}
        <p className="text-center text-xs text-muted">
          Protected by signed JWT bearer tokens · 24-hour session
        </p>
      </div>
    </div>
  )
}