import { AlertCircle, CheckCircle2, FileUp, Loader2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { importCustomersCsv, previewCustomersCsv } from '../lib/api'

// Friendly names for the fields the backend can recognize.
const FIELD_LABELS = {
  external_id: 'Customer ID',
  full_name: 'Name',
  email: 'Email',
  company_name: 'Company',
  subscription_plan: 'Plan',
  tenure_months: 'Tenure (months)',
  monthly_revenue: 'Monthly revenue',
  usage_minutes_last_30d: 'Usage minutes (30 days)',
  logins_last_30d: 'Logins (30 days)',
  active_days_last_30d: 'Active days (30 days)',
  support_ticket_count: 'Support tickets',
  unresolved_ticket_count: 'Unresolved tickets',
  payment_failures: 'Payment failures',
  last_active_at: 'Last active',
  churned: 'Churned (past outcome)',
}

function Notice({ children }) {
  return (
    <div
      role="alert"
      className="mt-6 flex gap-3 rounded-lg border border-ink bg-surface p-4 text-sm"
    >
      <AlertCircle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div>{children}</div>
    </div>
  )
}

function ColumnMapping({ preview }) {
  return (
    <section className="mt-8">
      <h2 className="font-medium">How Nexus reads your columns</h2>
      <div className="mt-3 overflow-x-auto rounded-lg border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Column in your file</th>
              <th className="px-4 py-2 font-medium">How Nexus will use it</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {preview.headers.map((header) => {
              const field = preview.detected_mappings[header]
              return (
                <tr key={header}>
                  <td className="px-4 py-2 font-medium">{header}</td>
                  <td className="px-4 py-2 text-muted">
                    {field
                      ? `Recognized as ${FIELD_LABELS[field] ?? field}`
                      : 'Kept as extra data'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function SampleRows({ preview }) {
  return (
    <section className="mt-8">
      <h2 className="font-medium">
        First {preview.sample_rows.length}{' '}
        {preview.sample_rows.length === 1 ? 'row' : 'rows'}
      </h2>
      <div className="mt-3 overflow-x-auto rounded-lg border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              {preview.headers.map((header) => (
                <th key={header} className="whitespace-nowrap px-4 py-2 font-medium">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {preview.sample_rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {preview.headers.map((header) => (
                  <td key={header} className="whitespace-nowrap px-4 py-2">
                    {row[header] || <span className="text-muted">empty</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
} 


const STATUS_TEXT = {
  completed: 'Import completed',
  partial: 'Import finished, some rows were skipped',
  failed: 'Nothing was imported',
}

function ImportResult({ result }) {
  const shownErrors = result.error_summary.slice(0, 10)
  const hiddenErrors = result.error_summary.length - shownErrors.length

  return (
    <section
      aria-labelledby="result-heading"
      className="mt-8 rounded-lg border border-line bg-surface p-5"
    >
      <h2 id="result-heading" className="flex items-center gap-2 font-medium">
        {result.status === 'completed' && (
          <CheckCircle2 size={18} className="text-accent" aria-hidden="true" />
        )}
        {STATUS_TEXT[result.status] ?? result.status}
      </h2>
      <p className="mt-1 text-sm text-muted">{result.filename}</p>

      <dl className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div>
          <dt className="text-muted">New customers</dt>
          <dd className="mt-1 text-xl font-medium">{result.inserted_count}</dd>
        </div>
        <div>
          <dt className="text-muted">Updated</dt>
          <dd className="mt-1 text-xl font-medium">{result.updated_count}</dd>
        </div>
        <div>
          <dt className="text-muted">Skipped</dt>
          <dd className="mt-1 text-xl font-medium">{result.failed_count}</dd>
        </div>
      </dl>

      {shownErrors.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-medium">Rows that were skipped</h3>
          <p className="mt-1 text-sm text-muted">
            Row numbers are lines in your file. Line 1 is the header.
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {shownErrors.map((item) => (
              <li key={item.row}>
                Row {item.row}: {item.error}
              </li>
            ))}
          </ul>
          {hiddenErrors > 0 && (
            <p className="mt-2 text-sm text-muted">and {hiddenErrors} more.</p>
          )}
        </div>
      )}
    </section>
  )
}

function ImportPage() {
  const inputRef = useRef(null)
  const [state, setState] = useState({ phase: 'idle' })

  async function handleFileChange(event) {
    const input = event.target
    const file = input.files[0]
    if (!file) return

    setState({ phase: 'loading', fileName: file.name })
    try {
      const preview = await previewCustomersCsv(file)
      setState({ phase: 'ready', file, fileName: file.name, preview })
    } catch (error) {
      setState({ phase: 'error', fileName: file.name, message: error.message })
    }
    // Reset so choosing the same file again still triggers a preview.
    input.value = ''
  }

  async function handleImport() {
    const { file, fileName, preview } = state
    setState({ phase: 'importing', file, fileName, preview })
    try {
      const result = await importCustomersCsv(file)
      setState({ phase: 'done', fileName, result })
    } catch (error) {
      // Keep the preview on screen so the person can simply try again.
      setState({
        phase: 'ready',
        file,
        fileName,
        preview,
        importError: error.message,
      })
    }
  }

  const { phase, fileName, preview, result, message, importError } = state
  const busy = phase === 'loading' || phase === 'importing'
  const showPreview = phase === 'ready' || phase === 'importing'
  const hasCustomerId =
    preview && Object.values(preview.detected_mappings).includes('external_id')

  return (
    <div className="max-w-4xl">
      <h1 className="font-display text-3xl font-medium tracking-tight">
        Import customers
      </h1>
      <p className="mt-2 max-w-xl text-muted">
        Choose a CSV file of your customers. You will see how Nexus reads it
        before anything is saved.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          className="sr-only"
          aria-label="Customer CSV file"
          tabIndex={-1}
        />
        <button
          type="button"
          onClick={() => inputRef.current.click()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-medium hover:border-accent disabled:opacity-60"
        >
          <FileUp size={16} aria-hidden="true" />
          Choose CSV file
        </button>
        {fileName && <span className="text-sm text-muted">{fileName}</span>}
      </div>

      {phase === 'loading' && (
        <p role="status" className="mt-6 flex items-center gap-2 text-sm text-muted">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          Reading file…
        </p>
      )}

      {phase === 'error' && <Notice>{message}</Notice>}

      {showPreview && (
        <>
          {!hasCustomerId && (
            <Notice>
              No column can be used as the customer ID, so this file cannot be
              imported yet. Rename one column to something like{' '}
              <code>customer_id</code> and choose the file again.
            </Notice>
          )}
          {importError && <Notice>{importError}</Notice>}

          <div className="mt-6">
            <button
              type="button"
              onClick={handleImport}
              disabled={!hasCustomerId || phase === 'importing'}
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
            >
              {phase === 'importing' && (
                <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              )}
              {phase === 'importing' ? 'Importing…' : 'Import customers'}
            </button>
            <p className="mt-2 max-w-xl text-sm text-muted">
              Customers that already exist in Nexus with the same ID are
              updated. Empty cells never erase values Nexus already has.
            </p>
          </div>

          <ColumnMapping preview={preview} />
          {preview.sample_rows.length > 0 ? (
            <SampleRows preview={preview} />
          ) : (
            <p className="mt-8 text-sm text-muted">
              This file has column headers but no data rows.
            </p>
          )}
        </>
      )}

      {phase === 'done' && <ImportResult result={result} />}
    </div>
  )
}

export default ImportPage