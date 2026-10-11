import { AlertCircle, ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCustomer } from '../lib/api'
import { formatDate, formatMoney, outcomeLabel } from '../lib/format'

const INTELLIGENCE = [
  {
    kind: 'Predicted',
    title: 'Churn risk',
    text: 'Needs a model trained on past customers with known outcomes.',
  },
  {
    kind: 'Explained',
    title: 'Why',
    text: 'Explanations come from the churn model, so they follow it.',
  },
  {
    kind: 'Retrieved',
    title: 'Support history',
    text: "Needs this customer's support tickets, which are not imported yet.",
  },
  {
    kind: 'Suggested',
    title: 'Next step',
    text: 'Recommendations need risk and evidence first.',
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
            These appear as Nexus gains the data and models to support them.
            Nothing here is estimated.
          </p>
          <ul className="mt-4 divide-y divide-line">
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