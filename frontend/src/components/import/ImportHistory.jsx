import { AlertCircle, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listImports } from '../../lib/api'

const STATUS_LABEL = {
  completed: 'Completed',
  partial: 'Some rows skipped',
  failed: 'Nothing imported',
  processing: 'Did not finish',
}

function formatWhen(isoString) {
  return new Date(isoString).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function ImportHistory({ refreshKey }) {
  const [state, setState] = useState({ phase: 'loading' })
  const [attempt, setAttempt] = useState(0)

  // Load the list when the page opens, after each import (refreshKey
  // changes), and when "Try again" is clicked (attempt changes).
  useEffect(() => {
    let cancelled = false
    listImports()
      .then((imports) => {
        if (!cancelled) setState({ phase: 'ready', imports })
      })
      .catch((error) => {
        if (!cancelled) setState({ phase: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey, attempt])

  function retry() {
    setState({ phase: 'loading' })
    setAttempt((count) => count + 1)
  }

  return (
    <section aria-labelledby="history-heading" className="mt-14">
      <h2 id="history-heading" className="font-display text-2xl font-medium">
        Import history
      </h2>

      {state.phase === 'loading' && (
        <p role="status" className="mt-4 flex items-center gap-2 text-sm text-muted">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          Loading history…
        </p>
      )}

      {state.phase === 'error' && (
        <div
          role="alert"
          className="mt-4 flex flex-wrap items-center gap-3 rounded-lg border border-ink bg-surface p-4 text-sm"
        >
          <AlertCircle size={18} className="shrink-0" aria-hidden="true" />
          <span>{state.message}</span>
          <button
            type="button"
            onClick={retry}
            className="rounded-lg border border-line px-3 py-1.5 font-medium hover:border-accent"
          >
            Try again
          </button>
        </div>
      )}

      {state.phase === 'ready' && state.imports.length === 0 && (
        <p className="mt-4 text-sm text-muted">
          No imports yet. Your imports will appear here.
        </p>
      )}

      {state.phase === 'ready' && state.imports.length > 0 && (
        <div className="mt-4 overflow-x-auto rounded-lg border border-line bg-surface">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Most recent customer imports</caption>
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">File</th>
                <th className="px-4 py-2 font-medium">When</th>
                <th className="px-4 py-2 font-medium">Result</th>
                <th className="px-4 py-2 text-right font-medium">New</th>
                <th className="px-4 py-2 text-right font-medium">Updated</th>
                <th className="px-4 py-2 text-right font-medium">Skipped</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {state.imports.map((item) => (
                <tr key={item.id}>
                  <td className="px-4 py-2 font-medium">{item.filename}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-muted">
                    {formatWhen(item.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2">
                    {STATUS_LABEL[item.status] ?? item.status}
                  </td>
                  <td className="px-4 py-2 text-right">{item.inserted_count}</td>
                  <td className="px-4 py-2 text-right">{item.updated_count}</td>
                  <td className="px-4 py-2 text-right">{item.failed_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default ImportHistory