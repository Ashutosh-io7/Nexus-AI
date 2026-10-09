import { Link } from 'react-router-dom'

function Landing() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight">
          Nexus AI landing page
        </h1>
        <p className="mt-2 text-slate-600">
          Placeholder. We build the real page in the next steps.
        </p>
        <Link
          to="/app"
          className="mt-6 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
        >
          Open Nexus
        </Link>
      </div>
    </main>
  )
}

export default Landing