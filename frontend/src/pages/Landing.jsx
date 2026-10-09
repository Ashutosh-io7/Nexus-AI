import { Link } from 'react-router-dom'

function Landing() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="text-center">
        <h1 className="font-display text-5xl font-medium tracking-tight text-ink">
          Nexus AI landing page
        </h1>
        <p className="mt-3 text-muted">
          Placeholder. We build the real page in the next steps.
        </p>
        <Link
          to="/app"
          className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Open Nexus
        </Link>
      </div>
    </main>
  )
}

export default Landing