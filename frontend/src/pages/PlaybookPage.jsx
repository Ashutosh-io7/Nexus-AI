import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FileText,
  FileUp,
  Loader2,
  Search,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { getPlaybookStatus, searchPlaybook, uploadPlaybookPdf } from '../lib/api'

function Notice({ children, isError = false }) {
  return (
    <div
      role="alert"
      className={`mt-4 flex items-center gap-3 rounded-lg border p-4 text-sm ${
        isError ? 'border-red-200 bg-red-50 text-red-900' : 'border-line bg-surface text-ink'
      }`}
    >
      <AlertCircle size={18} className="shrink-0 text-muted" aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}

function PlaybookPage() {
  const fileInputRef = useRef(null)

  // Status & Upload State
  const [statusState, setStatusState] = useState({ phase: 'loading' })
  const [uploadState, setUploadState] = useState({ phase: 'idle' })

  // Interactive Policy Search State
  const [searchQuery, setSearchQuery] = useState('')
  const [searchState, setSearchState] = useState({ phase: 'idle', results: [] })

  function loadStatus() {
    setStatusState({ phase: 'loading' })
    getPlaybookStatus()
      .then((data) => setStatusState({ phase: 'ready', data }))
      .catch((err) => setStatusState({ phase: 'error', message: err.message }))
  }

  useEffect(() => {
    loadStatus()
  }, [])

  async function handleFileSelected(event) {
    const file = event.target.files[0]
    if (!file) return

    setUploadState({ phase: 'uploading', fileName: file.name })
    try {
      const res = await uploadPlaybookPdf(file)
      setUploadState({ phase: 'done', message: res.message })
      loadStatus()
    } catch (err) {
      setUploadState({ phase: 'error', message: err.message })
    }
    event.target.value = ''
  }

  async function handleSearch(e) {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setSearchState({ phase: 'searching', results: [] })
    try {
      const res = await searchPlaybook(searchQuery)
      setSearchState({ phase: 'ready', results: res.matches })
    } catch (err) {
      setSearchState({ phase: 'error', message: err.message, results: [] })
    }
  }

  const isBusy = uploadState.phase === 'uploading'

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-medium tracking-tight text-ink">
          Retention playbook
        </h1>
        <p className="mt-1 text-sm text-muted">
          Upload your company’s customer retention and save policy PDF. Nexus uses pgvector to cite these exact rules in retention strategies.
        </p>
      </div>

      {/* Active Policy Status Card */}
      <section aria-labelledby="status-heading" className="rounded-xl border border-line bg-surface p-5">
        <h2 id="status-heading" className="text-sm font-medium uppercase tracking-wider text-muted">
          Active company policy
        </h2>

        {statusState.phase === 'loading' && (
          <div className="mt-3 flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Loading active policy status…
          </div>
        )}

        {statusState.phase === 'error' && (
          <Notice isError>{statusState.message}</Notice>
        )}

        {statusState.phase === 'ready' && (
          <div className="mt-3">
            {statusState.data.available ? (
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-paper text-accent">
                    <FileText size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-ink">{statusState.data.document_title}</span>
                      <span className="rounded-md bg-paper px-2 py-0.5 text-xs text-muted">
                        v{statusState.data.version}
                      </span>
                    </div>
                    <p className="text-xs text-muted">
                      {statusState.data.chunks_stored} policy sections indexed in pgvector with Gemini embeddings
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-700">
                  <CheckCircle2 size={16} />
                  Vector search active
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted">
                <p>No retention policy PDF has been uploaded yet.</p>
                <p className="mt-1 text-xs">Upload your company guidelines below to activate evidence-backed RAG.</p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Upload Zone */}
      <section aria-labelledby="upload-heading" className="rounded-xl border border-line bg-surface p-5">
        <h2 id="upload-heading" className="text-sm font-medium uppercase tracking-wider text-muted">
          Upload or update policy PDF
        </h2>
        <p className="mt-1 text-xs text-muted">
          Upload any corporate guidelines PDF (discount authority, contract terms, SLA breach remedies).
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelected}
            className="sr-only"
            aria-label="Upload Playbook PDF"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current.click()}
            disabled={isBusy}
            className="inline-flex items-center gap-2 rounded-lg border border-line bg-paper px-4 py-2 text-sm font-medium text-ink shadow-2xs hover:border-accent hover:text-accent disabled:opacity-60"
          >
            {isBusy ? <Loader2 size={16} className="animate-spin" /> : <FileUp size={16} />}
            {isBusy ? 'Processing and embedding PDF…' : 'Choose PDF file'}
          </button>
          <span className="text-xs text-muted">Only .pdf documents are supported</span>
        </div>

        {uploadState.phase === 'error' && (
          <Notice isError>{uploadState.message}</Notice>
        )}

        {uploadState.phase === 'done' && (
          <div className="mt-3 flex items-center gap-2 text-sm text-emerald-700">
            <CheckCircle2 size={16} />
            {uploadState.message}
          </div>
        )}
      </section>

      {/* Interactive Policy Search & RAG Test Tool */}
      <section aria-labelledby="test-heading" className="rounded-xl border border-line bg-surface p-5">
        <h2 id="test-heading" className="text-sm font-medium uppercase tracking-wider text-muted">
          Test vector policy retrieval (RAG)
        </h2>
        <p className="mt-1 text-xs text-muted">
          Ask a policy question to test how pgvector retrieves passages from your uploaded PDF.
        </p>

        <form onSubmit={handleSearch} className="mt-4 flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. What discount is allowed for high MRR?"
              className="w-full rounded-lg border border-line bg-paper py-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-accent focus:bg-surface focus:outline-hidden"
            />
          </div>
          <button
            type="submit"
            disabled={searchState.phase === 'searching' || !searchQuery.trim()}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
          >
            {searchState.phase === 'searching' ? 'Searching…' : 'Search policy'}
          </button>
        </form>

        {/* Results */}
        {searchState.phase === 'searching' && (
          <div className="mt-4 flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Running pgvector cosine similarity search…
          </div>
        )}

        {searchState.phase === 'error' && (
          <Notice isError>{searchState.message}</Notice>
        )}

        {searchState.phase === 'ready' && (
          <div className="mt-6 space-y-4">
            <h3 className="text-xs font-medium uppercase tracking-wider text-muted">
              Retrieved policy passages ({searchState.results.length} matches)
            </h3>

            {searchState.results.length === 0 ? (
              <p className="text-sm text-muted">No matching policy passages found.</p>
            ) : (
              searchState.results.map((match) => (
                <div key={match.chunk_id} className="rounded-lg border border-line bg-paper p-4 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line pb-2">
                    <span className="font-medium text-ink">{match.section_title}</span>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-surface px-2 py-0.5 text-xs text-muted">
                        Page {match.page_number}
                      </span>
                      <span className="font-mono text-xs font-medium text-accent">
                        {Math.round(match.similarity * 100)}% match
                      </span>
                    </div>
                  </div>
                  <p className="mt-2.5 whitespace-pre-line text-xs leading-relaxed text-muted">
                    {match.content}
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </section>
    </div>
  )
}

export default PlaybookPage