import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  ChevronsUpDown,
  Search,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCustomers } from '../lib/api'

const PAGE_SIZE = 25

const COLUMNS = [
  { key: 'full_name', label: 'Customer' },
  { key: 'company_name', label: 'Company' },
  { key: 'subscription_plan', label: 'Plan' },
  { key: 'tenure_months', label: 'Tenure', align: 'right' },
  { key: 'monthly_revenue', label: 'Monthly revenue', align: 'right' },
  { key: 'last_active_at', label: 'Last active' },
  { key: null, label: 'Past outcome' },
]

function Missing() {
  return (
    <span className="text-muted" aria-label="not provided">
      —
    </span>
  )
}

function formatMoney(value) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    dateStyle: 'medium',
  })
}

// "churned" is a past outcome from the customer's own data, not a prediction.
// An empty value means unknown, which is different from "stayed".
function outcomeLabel(churned) {
  if (churned === true) return 'Left'
  if (churned === false) return 'Stayed'
  return 'Unknown'
}

function SortableHeader({ column, query, onSort }) {
  const active = query.sortBy === column.key
  const Icon = !active
    ? ChevronsUpDown
    : query.sortDir === 'asc'
      ? ArrowUp
      : ArrowDown
  const ariaSort = !active
    ? 'none'
    : query.sortDir === 'asc'
      ? 'ascending'
      : 'descending'

  return (
    <th
      scope="col"
      aria-sort={ariaSort}
      className={`px-4 py-2.5 font-medium ${column.align === 'right' ? 'text-right' : ''}`}
    >
      <button
        type="button"
        onClick={() => onSort(column.key)}
        className="inline-flex items-center gap-1 hover:text-ink"
      >
        {column.label}
        <Icon
          size={14}
          aria-hidden="true"
          className={active ? 'text-ink' : 'opacity-50'}
        />
      </button>
    </th>
  )
}

function CustomersPage() {
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState({
    search: '',
    sortBy: 'created_at',
    sortDir: 'desc',
    page: 0,
  })
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState({
    phase: 'loading',
    data: null,
    forQuery: null,
    message: '',
  })

  // Wait until the person stops typing before searching.
  useEffect(() => {
    const timer = setTimeout(() => {
      const term = searchInput.trim()
      setQuery((current) =>
        current.search === term ? current : { ...current, search: term, page: 0 },
      )
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let cancelled = false
    listCustomers({
      search: query.search,
      sortBy: query.sortBy,
      sortDir: query.sortDir,
      limit: PAGE_SIZE,
      offset: query.page * PAGE_SIZE,
    })
      .then((data) => {
        if (!cancelled) {
          setResult({ phase: 'ready', data, forQuery: query, message: '' })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setResult({
            phase: 'error',
            data: null,
            forQuery: query,
            message: error.message,
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [query, attempt])

  function handleSort(key) {
    setQuery((current) => ({
      ...current,
      sortBy: key,
      sortDir:
        current.sortBy === key && current.sortDir === 'asc' ? 'desc' : 'asc',
      page: 0,
    }))
  }

  function goToPage(page) {
    setQuery((current) => ({ ...current, page }))
  }

  function retry() {
    setResult({ phase: 'loading', data: null, forQuery: null, message: '' })
    setAttempt((count) => count + 1)
  }

  const isCurrent = result.forQuery === query
  const showError = result.phase === 'error' && isCurrent
  const data = result.phase === 'ready' ? result.data : null
  const refreshing = data !== null && !isCurrent

  const total = data ? data.total : 0
  const from = total === 0 ? 0 : query.page * PAGE_SIZE + 1
  const to = Math.min((query.page + 1) * PAGE_SIZE, total)

  return (
    <div className="max-w-6xl">
      <h1 className="font-display text-3xl font-medium tracking-tight">
        Customers
      </h1>
      <p className="mt-2 text-muted" aria-live="polite">
        {data
          ? `${total.toLocaleString()} ${total === 1 ? 'customer' : 'customers'}${query.search ? ' match your search' : ' in Nexus'}`
          : 'Everyone you have imported into Nexus.'}
      </p>

      <div className="relative mt-6 max-w-sm">
        <Search
          size={16}
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          type="search"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search by ID, name, email or company"
          aria-label="Search customers"
          className="w-full rounded-lg border border-line bg-surface py-2.5 pl-9 pr-3 text-sm placeholder:text-muted"
        />
      </div>

      {showError && (
        <div
          role="alert"
          className="mt-6 flex flex-wrap items-center gap-3 rounded-lg border border-ink bg-surface p-4 text-sm"
        >
          <AlertCircle size={18} className="shrink-0" aria-hidden="true" />
          <span>{result.message}</span>
          <button
            type="button"
            onClick={retry}
            className="rounded-lg border border-line px-3 py-1.5 font-medium hover:border-accent"
          >
            Try again
          </button>
        </div>
      )}

      {!showError && data === null && (
        <div role="status" className="mt-6 space-y-2">
          {[0, 1, 2, 3, 4].map((row) => (
            <div
              key={row}
              className="h-12 rounded-lg bg-line motion-safe:animate-pulse"
            />
          ))}
          <span className="sr-only">Loading customers…</span>
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="mt-6 rounded-lg border border-line bg-surface p-8 text-center">
          {query.search ? (
            <p>No customers match “{query.search}”.</p>
          ) : total > 0 ? (
            <>
              <p>There are no customers on this page.</p>
              <button
                type="button"
                onClick={() => goToPage(0)}
                className="mt-3 rounded-lg border border-line px-3 py-1.5 text-sm font-medium hover:border-accent"
              >
                Back to the first page
              </button>
            </>
          ) : (
            <>
              <p className="font-medium">No customers yet.</p>
              <p className="mt-1 text-sm text-muted">
                Import a CSV file of your customers to get started.
              </p>
              <Link
                to="/app/import"
                className="mt-4 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Import customers
              </Link>
            </>
          )}
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div
            aria-busy={refreshing}
            className={`mt-6 overflow-x-auto rounded-lg border border-line bg-surface transition-opacity ${refreshing ? 'opacity-60' : ''}`}
          >
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Customers</caption>
              <thead className="border-b border-line text-muted">
                <tr>
                  {COLUMNS.map((column) =>
                    column.key ? (
                      <SortableHeader
                        key={column.key}
                        column={column}
                        query={query}
                        onSort={handleSort}
                      />
                    ) : (
                      <th
                        key={column.label}
                        scope="col"
                        className="px-4 py-2.5 font-medium"
                      >
                        {column.label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map((customer) => (
                  <tr
                    key={customer.id}
                    className="transition-colors hover:bg-paper"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium">
                        {customer.full_name || customer.external_id}
                      </div>
                      {customer.full_name && (
                        <div className="text-xs text-muted">
                          {customer.external_id}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {customer.company_name || <Missing />}
                    </td>
                    <td className="px-4 py-3">
                      {customer.subscription_plan || <Missing />}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {customer.tenure_months !== null ? (
                        `${customer.tenure_months} mo`
                      ) : (
                        <Missing />
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {customer.monthly_revenue !== null ? (
                        formatMoney(customer.monthly_revenue)
                      ) : (
                        <Missing />
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {customer.last_active_at ? (
                        formatDate(customer.last_active_at)
                      ) : (
                        <Missing />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {outcomeLabel(customer.churned)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
            <span className="text-muted">
              Showing {from.toLocaleString()}–{to.toLocaleString()} of{' '}
              {total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => goToPage(query.page - 1)}
                disabled={query.page === 0}
                className="rounded-lg border border-line bg-surface px-3 py-1.5 font-medium hover:border-accent disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => goToPage(query.page + 1)}
                disabled={to >= total}
                className="rounded-lg border border-line bg-surface px-3 py-1.5 font-medium hover:border-accent disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>

          <p className="mt-4 text-xs text-muted">
            Past outcome comes from your own data. “Unknown” means the file had
            no value. Revenue is shown as stored, because Nexus does not assume
            a currency.
          </p>
        </>
      )}
    </div>
  )
}

export default CustomersPage