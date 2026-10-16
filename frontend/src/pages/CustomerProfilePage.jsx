import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getCustomer,
  getCustomerExplanation,
  getCustomerPrediction,
  getCustomerCohort,
} from '../lib/api'
import { formatDate, formatMoney, formatPercent, outcomeLabel } from '../lib/format'

const INTELLIGENCE = [
  {
    kind: 'Suggested',
    title: 'Next step',
    text: 'Retention recommendations need risk and evidence first.',
  },
]


function NotProvided() {
  return <span className="font-normal text-muted">Not provided</span>
}

function Row({ label, value }) {
  const empty = value === null || value === undefined || value === ''
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-line py-3 last:border-b-0">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="break-words text-right text-sm font-medium">
        {empty ? <NotProvided /> : value}
      </dd>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="font-display text-xl font-medium">{title}</h2>
      <dl className="mt-2">{children}</dl>
    </section>
  )
}

function BackLink() {
  return (
    <Link
      to="/app/customers"
      className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
    >
      <ArrowLeft size={16} aria-hidden="true" />
      Customers
    </Link>
  )
}


const RISK_STYLE = {
  high: { label: 'High risk', className: 'text-risk-high' },
  medium: { label: 'Medium risk', className: 'text-risk-medium' },
  low: { label: 'Low risk', className: 'text-ink' },
}

function ChurnRiskItem({ customerId }) {
  const [state, setState] = useState({ phase: 'loading' })

  useEffect(() => {
    let cancelled = false
    getCustomerPrediction(customerId)
      .then((data) => {
        if (!cancelled) setState({ phase: 'ready', data })
      })
      .catch((error) => {
        if (!cancelled) setState({ phase: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [customerId])

  let body
  if (state.phase === 'loading') {
    body = <div className="mt-2 h-10 rounded bg-line motion-safe:animate-pulse" />
  } else if (state.phase === 'error') {
    body = (
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">Could not load.</span>{' '}
        {state.message}
      </p>
    )
  } else if (!state.data.available) {
    body = (
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">Not available yet.</span>{' '}
        {state.data.message}
      </p>
    )
  } else {
    const prediction = state.data
    const style = RISK_STYLE[prediction.risk_level] ?? RISK_STYLE.low
    const percent =
      prediction.churn_probability < 0.01
        ? '<1%'
        : formatPercent(prediction.churn_probability)

    body = (
      <div className="mt-2">
        <p className="flex items-baseline gap-2">
          <span className="font-display text-3xl font-medium">{percent}</span>
          <span className={`text-sm font-medium ${style.className}`}>
            {style.label}
          </span>
        </p>
        <p className="mt-1 text-sm text-muted">
          Estimated chance this customer leaves. A model estimate, not a
          certainty.
        </p>
        <p className="mt-1 text-xs text-muted">
          Model {prediction.model_version} · {formatDate(prediction.predicted_at)}
        </p>
        {prediction.in_training_data && (
          <p className="mt-2 text-xs text-muted">
            This customer was part of the data the model learned from, so the
            estimate can look more confident than it should.
          </p>
        )}
      </div>
    )
  }

  return (
    <li className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium">Churn risk</h3>
        <span className="rounded-full bg-paper px-2 py-0.5 text-xs text-muted">
          Predicted
        </span>
      </div>
      {body}
    </li>
  )
}


function percentLabel(probability) {
  return probability < 0.01 ? '<1%' : formatPercent(probability)
}

function WhyItem({ customerId }) {
  const [state, setState] = useState({ phase: 'loading' })

  useEffect(() => {
    let cancelled = false
    getCustomerExplanation(customerId)
      .then((data) => {
        if (!cancelled) setState({ phase: 'ready', data })
      })
      .catch((error) => {
        if (!cancelled) setState({ phase: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [customerId])

  let body
  if (state.phase === 'loading') {
    body = <div className="mt-2 h-24 rounded bg-line motion-safe:animate-pulse" />
  } else if (state.phase === 'error') {
    body = (
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">Could not load.</span>{' '}
        {state.message}
      </p>
    )
  } else if (!state.data.available) {
    body = (
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">Not available yet.</span>{' '}
        {state.data.message}
      </p>
    )
  } else {
    const explanation = state.data
    const maxImpact = Math.max(
      ...explanation.contributions.map((item) => Math.abs(item.impact)),
      0.0001,
    )

    body = (
      <div className="mt-2">
        <p className="text-sm text-muted">
          Across the customers the model learned from, the average estimate is{' '}
          {percentLabel(explanation.average_probability)}. For this customer it
          is {percentLabel(explanation.probability)}. These are the factors
          that moved it:
        </p>

        <ul className="mt-3 space-y-3">
          {explanation.contributions.map((item) => {
            const raises = item.direction === 'raises'
            const Icon = raises ? ArrowUp : ArrowDown
            const width = Math.max(4, (Math.abs(item.impact) / maxImpact) * 100)

            return (
              <li key={item.feature}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span>
                    <span className="font-medium">{item.label}</span>{' '}
                    <span className="text-muted">{item.value}</span>
                  </span>
                  <span
                    className={`inline-flex shrink-0 items-center gap-1 text-xs font-medium ${raises ? 'text-risk-high' : 'text-accent'}`}
                  >
                    <Icon size={12} aria-hidden="true" />
                    {raises ? 'Raises risk' : 'Lowers risk'}
                  </span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-paper" aria-hidden="true">
                  <div
                    className={`h-full rounded-full ${raises ? 'bg-risk-high' : 'bg-accent'}`}
                    style={{ width: `${width}%` }}
                  />
                </div>
              </li>
            )
          })}
        </ul>

        {explanation.other_count > 0 && (
          <p className="mt-3 text-xs text-muted">
            {explanation.other_count} other factors together{' '}
            {explanation.other_impact > 0 ? 'raise' : 'lower'} the estimate.
          </p>
        )}
        <p className="mt-3 text-xs text-muted">
          This shows what the model&apos;s estimate is based on. It does not
          prove why this customer might leave.
        </p>
      </div>
    )
  }

  return (
    <li className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium">Why</h3>
        <span className="rounded-full bg-paper px-2 py-0.5 text-xs text-muted">
          Explained
        </span>
      </div>
      {body}
    </li>
  )
}

function SimilarCohortItem({ customerId }) {
  const [state, setState] = useState({ phase: 'loading' })
  const [expanded, setExpanded] = useState(false)
  useEffect(() => {
    let cancelled = false
    getCustomerCohort(customerId)
      .then((data) => {
        if (!cancelled) setState({ phase: 'ready', data })
      })
      .catch((error) => {
        if (!cancelled) setState({ phase: 'error', message: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [customerId])
  let body
  if (state.phase === 'loading') {
    body = <div className="mt-2 h-20 rounded bg-line motion-safe:animate-pulse" />
  } else if (state.phase === 'error') {
    body = (
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">Could not load cohort.</span>{' '}
        {state.message}
      </p>
    )
  } else if (!state.data.available) {
    body = (
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">Not available yet.</span>{' '}
        {state.data.message}
      </p>
    )
  } else {
    const cohort = state.data
    const churnPct = Math.round(cohort.historical_churn_rate * 100)
    body = (
      <div className="mt-2 space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <p className="font-display text-2xl font-medium text-ink">
            {churnPct}% Churned
          </p>
          <span className="text-xs text-muted">
            {cohort.churned_count} of {cohort.total_similar} similar accounts
          </span>
        </div>
        <p className="text-xs text-muted leading-relaxed">
          Based on the {cohort.total_similar} past accounts with closest usage, tenure, and billing attributes.
          {cohort.avg_tenure_months && ` Avg tenure: ${cohort.avg_tenure_months} mo.`}
          {cohort.avg_monthly_revenue && ` Avg MRR: $${cohort.avg_monthly_revenue}.`}
        </p>
        {cohort.similar_customers.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              {expanded ? 'Hide historical matches' : `View ${cohort.similar_customers.length} nearest accounts`}
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {expanded && (
              <ul className="mt-3 space-y-2 border-t border-line pt-2 text-xs">
                {cohort.similar_customers.slice(0, 8).map((peer) => {
                  const didChurn = peer.churned === true
                  const matchPct = Math.round(peer.similarity_score * 100)
                  return (
                    <li
                      key={peer.id}
                      className="flex items-center justify-between rounded-md bg-paper p-2"
                    >
                      <div className="truncate pr-2">
                        <Link
                          to={`/app/customers/${peer.id}`}
                          className="font-medium text-ink hover:underline"
                        >
                          {peer.name}
                        </Link>
                        <p className="text-[11px] text-muted">
                          {peer.subscription_plan || 'Plan not set'} · {peer.tenure_months ?? 0} mo
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="text-[11px] text-muted">{matchPct}% match</span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                            didChurn
                              ? 'bg-red-50 text-red-700'
                              : 'bg-emerald-50 text-emerald-700'
                          }`}
                        >
                          {didChurn ? 'Churned' : 'Retained'}
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    )
  }
  return (
    <li className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium">Similar past customers</h3>
        <span className="rounded-full bg-paper px-2 py-0.5 text-xs text-muted">
          Cohort
        </span>
      </div>
      {body}
    </li>
  )
}


function CustomerProfilePage() {
  const { customerId } = useParams()
  const idIsValid = /^\d+$/.test(customerId)

  const [result, setResult] = useState({
    phase: idIsValid ? 'loading' : 'notfound',
    customer: null,
    message: '',
  })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!idIsValid) return
    let cancelled = false
    getCustomer(customerId)
      .then((customer) => {
        if (!cancelled) setResult({ phase: 'ready', customer, message: '' })
      })
      .catch((error) => {
        if (cancelled) return
        setResult({
          phase: error.notFound ? 'notfound' : 'error',
          customer: null,
          message: error.message,
        })
      })
    return () => {
      cancelled = true
    }
  }, [customerId, idIsValid, attempt])

  function retry() {
    setResult({ phase: 'loading', customer: null, message: '' })
    setAttempt((count) => count + 1)
  }

  const { phase, customer, message } = result

  if (phase === 'loading') {
    return (
      <div className="max-w-5xl">
        <BackLink />
        <div role="status" className="mt-6 space-y-3">
          <div className="h-9 w-64 rounded-lg bg-line motion-safe:animate-pulse" />
          <div className="h-40 rounded-xl bg-line motion-safe:animate-pulse" />
          <span className="sr-only">Loading customer…</span>
        </div>
      </div>
    )
  }

  if (phase === 'notfound') {
    return (
      <div className="max-w-5xl">
        <BackLink />
        <h1 className="mt-4 font-display text-3xl font-medium tracking-tight">
          Customer not found
        </h1>
        <p className="mt-2 text-muted">
          This customer does not exist in Nexus. It may have been removed.
        </p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="max-w-5xl">
        <BackLink />
        <div
          role="alert"
          className="mt-6 flex flex-wrap items-center gap-3 rounded-lg border border-ink bg-surface p-4 text-sm"
        >
          <AlertCircle size={18} className="shrink-0" aria-hidden="true" />
          <span>{message}</span>
          <button
            type="button"
            onClick={retry}
            className="rounded-lg border border-line px-3 py-1.5 font-medium hover:border-accent"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const extraEntries = Object.entries(customer.source_attributes ?? {})
  const subtitle = [
    customer.full_name ? customer.external_id : null,
    customer.company_name,
    customer.subscription_plan,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="max-w-5xl">
      <BackLink />

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-medium tracking-tight">
            {customer.full_name || customer.external_id}
          </h1>
          {subtitle && <p className="mt-1 text-muted">{subtitle}</p>}
        </div>
        <p className="rounded-full border border-line bg-surface px-3 py-1 text-sm">
          <span className="text-muted">Past outcome: </span>
          <span className="font-medium">{outcomeLabel(customer.churned)}</span>
        </p>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[3fr_2fr] lg:items-start">
        <div className="space-y-6">
          <Section title="Account">
            <Row label="Email" value={customer.email} />
            <Row label="Plan" value={customer.subscription_plan} />
            <Row
              label="Tenure"
              value={
                customer.tenure_months === null
                  ? null
                  : `${customer.tenure_months} months`
              }
            />
            <Row
              label="Monthly revenue"
              value={
                customer.monthly_revenue === null
                  ? null
                  : formatMoney(customer.monthly_revenue)
              }
            />
            <Row
              label="Last active"
              value={
                customer.last_active_at
                  ? formatDate(customer.last_active_at)
                  : null
              }
            />
            <Row label="Added to Nexus" value={formatDate(customer.created_at)} />
          </Section>

          <Section title="Activity, last 30 days">
            <Row label="Logins" value={customer.logins_last_30d} />
            <Row label="Active days" value={customer.active_days_last_30d} />
            <Row
              label="Usage minutes"
              value={
                customer.usage_minutes_last_30d === null
                  ? null
                  : Number(customer.usage_minutes_last_30d).toLocaleString()
              }
            />
          </Section>

          <Section title="Support and billing">
            <Row label="Support tickets" value={customer.support_ticket_count} />
            <Row
              label="Unresolved tickets"
              value={customer.unresolved_ticket_count}
            />
            <Row label="Payment failures" value={customer.payment_failures} />
          </Section>

          {extraEntries.length > 0 && (
            <Section title="Other data from your file">
              {extraEntries.map(([key, value]) => (
                <Row key={key} label={key} value={String(value)} />
              ))}
            </Section>
          )}
        </div>

        <aside
          aria-labelledby="intelligence-heading"
          className="rounded-xl border border-line bg-surface p-5 lg:sticky lg:top-6"
        >
          <h2
            id="intelligence-heading"
            className="font-display text-xl font-medium"
          >
            Intelligence
          </h2>
          <p className="mt-1 text-sm text-muted">
            Each item says where it comes from. Anything Nexus cannot support
            yet says so instead of guessing.
          </p>
          <ul className="mt-4 divide-y divide-line">
            <ChurnRiskItem customerId={customer.id} />
            <WhyItem customerId={customer.id} />
            <SimilarCohortItem customerId={customer.id} />
            {INTELLIGENCE.map((item) => (
              <li key={item.title} className="py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="text-sm font-medium">{item.title}</h3>
                  <span className="rounded-full bg-paper px-2 py-0.5 text-xs text-muted">
                    {item.kind}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted">
                  <span className="font-medium text-ink">Not available yet.</span>{' '}
                  {item.text}
                </p>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  )
}

export default CustomerProfilePage