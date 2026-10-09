import { useEffect, useState } from 'react'
import { getHealth } from '../lib/api'

const DOT_COLORS = {
  up: 'bg-emerald-500',
  down: 'bg-red-500',
  checking: 'bg-amber-400',
  unknown: 'bg-slate-300',
}

const STATUS_LABELS = {
  up: 'Running',
  down: 'Down',
  checking: 'Checking…',
  unknown: 'Unknown',
}

function StatusRow({ label, status }) {
  return (
    <li className="flex items-center justify-between py-3">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="flex items-center gap-2 text-sm font-medium text-slate-900">
        <span
          className={`h-2 w-2 rounded-full ${DOT_COLORS[status]}`}
          aria-hidden="true"
        />
        {STATUS_LABELS[status]}
      </span>
    </li>
  )
}

function StatusPage() {
  const [state, setState] = useState({ phase: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false

    getHealth()
      .then((health) => {
        if (!cancelled) setState({ phase: 'loaded', health })
      })
      .catch(() => {
        if (!cancelled) setState({ phase: 'offline' })
      })

    return () => {
      cancelled = true
    }
  }, [attempt])

  function retry() {
    setState({ phase: 'loading' })
    setAttempt((count) => count + 1)
  }

  let apiStatus = 'checking'
  let dbStatus = 'checking'

  if (state.phase === 'offline') {
    apiStatus = 'down'
    dbStatus = 'unknown'
  } else if (state.phase === 'loaded') {
    apiStatus = 'up'
    dbStatus = state.health.database === 'up' ? 'up' : 'down'
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-semibold tracking-tight">Nexus AI</h1>
        <p className="mt-1 text-slate-600">
          Turn customer signals into intelligent retention actions.
        </p>

        <section
          aria-labelledby="status-heading"
          className="mt-8 rounded-xl border border-slate-200 bg-white px-5 py-4"
        >
          <h2 id="status-heading" className="text-sm font-medium text-slate-900">
            System status
          </h2>
          <ul className="mt-2 divide-y divide-slate-100">
            <StatusRow label="API" status={apiStatus} />
            <StatusRow label="Database" status={dbStatus} />
          </ul>

          {state.phase === 'offline' && (
            <p className="mt-3 text-sm text-slate-600">
              Can't reach the Nexus API. Make sure the backend is running, then
              retry.
            </p>
          )}

          {state.phase !== 'loading' && (
            <button
              type="button"
              onClick={retry}
              className="mt-4 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
            >
              Check again
            </button>
          )}
        </section>
      </div>
    </main>
  )
}

export default StatusPage  