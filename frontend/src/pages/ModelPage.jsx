import { AlertCircle, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getChurnModel, runChurnPredictions } from '../lib/api'
import { formatDate, formatPercent } from '../lib/format'

const ALGORITHM_NAMES = {
  logistic_regression: 'Logistic regression',
  xgboost: 'XGBoost',
}

function Notice({ children, action }) {
  return (
    <div
      role="alert"
      className="mt-6 flex flex-wrap items-center gap-3 rounded-lg border border-ink bg-surface p-4 text-sm"
    >
      <AlertCircle size={18} className="shrink-0" aria-hidden="true" />
      <span>{children}</span>
      {action}
    </div>
  )
}

function Fact({ label, value, hint }) {
  return (
    <div className="border-b border-line py-3 last:border-b-0">
      <div className="flex items-baseline justify-between gap-6">
        <dt className="text-sm text-muted">{label}</dt>
        <dd className="text-right text-sm font-medium">{value}</dd>
      </div>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="font-display text-xl font-medium">{title}</h2>
      {children}
    </section>
  )
}

function ModelPage() {
  const [state, setState] = useState({ phase: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [run, setRun] = useState({ phase: 'idle' })

  useEffect(() => {
    let cancelled = false
    getChurnModel()
      .then((model) => {
        if (!cancelled) setState({ phase: 'ready', model })
      })
      .catch((error) => {
        if (!cancelled) setState({ phase: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  function retry() {
    setState({ phase: 'loading' })
    setAttempt((count) => count + 1)
  }

  async function handleScore() {
    setRun({ phase: 'running' })
    try {
      const result = await runChurnPredictions()
      setRun({ phase: 'done', result })
    } catch (error) {
      setRun({ phase: 'error', message: error.message })
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-3xl font-medium tracking-tight">
        Churn model
      </h1>
      <p className="mt-2 max-w-xl text-muted">
        How Nexus estimates which customers may leave, and how well that has
        worked on past customers.
      </p>

      {state.phase === 'loading' && (
        <div role="status" className="mt-6 space-y-3">
          <div className="h-32 rounded-xl bg-line motion-safe:animate-pulse" />
          <div className="h-40 rounded-xl bg-line motion-safe:animate-pulse" />
          <span className="sr-only">Loading model…</span>
        </div>
      )}

      {state.phase === 'error' && (
        <Notice
          action={
            <button
              type="button"
              onClick={retry}
              className="rounded-lg border border-line px-3 py-1.5 font-medium hover:border-accent"
            >
              Try again
            </button>
          }
        >
          {state.message}
        </Notice>
      )}

      {state.phase === 'ready' && !state.model.available && (
        <div className="mt-6 rounded-xl border border-line bg-surface p-5">
          <h2 className="font-display text-xl font-medium">No model yet</h2>
          <p className="mt-2 text-sm text-muted">{state.model.message}</p>
          <p className="mt-2 text-sm text-muted">
            Nexus does not make up risk scores. Until a model is trained on
            customers with known outcomes, risk stays unavailable.
          </p>
        </div>
      )}

      {state.phase === 'ready' && state.model.available && (
        <ModelDetails
          model={state.model}
          run={run}
          onScore={handleScore}
        />
      )}
    </div>
  )
}

function ModelDetails({ model, run, onScore }) {
  const m = model.test_metrics
  const high = formatPercent(model.high_risk_cutoff)
  const medium = formatPercent(model.medium_risk_cutoff)

  return (
    <div className="mt-6 space-y-6">
      <Section title="Current model">
        <dl className="mt-2">
          <Fact
            label="Method"
            value={ALGORITHM_NAMES[model.algorithm] ?? model.algorithm}
          />
          <Fact label="Trained" value={formatDate(model.trained_at)} />
          <Fact
            label="Learned from"
            value={`${model.labeled_customers.toLocaleString()} customers`}
            hint={`Customers with a known outcome. ${formatPercent(model.churn_rate, 1)} of them left.`}
          />
          <Fact label="Version" value={model.version} />
        </dl>
      </Section>

      <Section title="How well it works">
        <p className="mt-1 text-sm text-muted">
          Measured on {model.test_rows.toLocaleString()} customers the model
          did not learn from.
        </p>
        <dl className="mt-2">
          <Fact
            label="Flagged customers who really left"
            value={formatPercent(m.precision)}
            hint={`Of customers estimated at ${formatPercent(m.threshold)} or more, this share did leave.`}
          />
          <Fact
            label="Customers who left that it caught"
            value={formatPercent(m.recall)}
            hint="The rest left without being flagged at that cutoff."
          />
          <Fact
            label="Ranking quality (ROC-AUC)"
            value={m.roc_auc.toFixed(3)}
            hint="0.5 is a coin flip and 1.0 is perfect."
          />
          <Fact
            label="PR-AUC"
            value={m.pr_auc.toFixed(3)}
            hint={`A model with no skill would score about ${m.no_skill_pr_auc.toFixed(3)}.`}
          />
        </dl>
        <p className="mt-3 text-xs text-muted">
          These numbers describe past customers in your data. They are not a
          guarantee for future customers.
        </p>
      </Section>

      <Section title="Risk levels">
        <p className="mt-1 text-sm text-muted">
          <span className="font-medium text-risk-high">High</span>: {high} or
          more. <span className="font-medium text-risk-medium">Medium</span>:{' '}
          {medium} to under {high}. <span className="font-medium">Low</span>:
          under {medium}. These are default cutoffs. A lower cutoff catches
          more customers who leave, but flags more customers who would have
          stayed.
        </p>
      </Section>

      <Section title="Score customers">
        <p className="mt-1 text-sm text-muted">
          Estimates the chance of leaving for every customer who has not
          already left. Customers marked as left are skipped.
        </p>
        <button
          type="button"
          onClick={onScore}
          disabled={run.phase === 'running'}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
        >
          {run.phase === 'running' && (
            <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          )}
          {run.phase === 'running' ? 'Scoring…' : 'Score customers'}
        </button>

        {run.phase === 'done' && (
          <p role="status" className="mt-4 text-sm">
            Scored {run.result.scored.toLocaleString()} customers with this
            model. Skipped {run.result.skipped_already_left.toLocaleString()}{' '}
            who already left.{' '}
            <Link to="/app/customers" className="font-medium underline">
              Open customers
            </Link>
          </p>
        )}
        {run.phase === 'error' && <Notice>{run.message}</Notice>}
      </Section>
    </div>
  )
}

export default ModelPage