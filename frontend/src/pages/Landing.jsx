import { Link } from 'react-router-dom'
import Principles from '../components/landing/Principles'
import ReasoningChain from '../components/landing/ReasoningChain'

function Landing() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link
          to="/"
          className="font-display text-2xl font-medium tracking-tight"
        >
          Nexus AI
        </Link>
        <Link
          to="/app"
          className="rounded-lg border border-line bg-surface px-3.5 py-2 text-sm font-medium text-ink hover:border-accent"
        >
          Open Nexus
        </Link>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-20 pt-10 lg:grid-cols-2 lg:pt-16">
          <div>
            <h1 className="max-w-xl font-display text-4xl font-medium leading-[1.05] tracking-tight motion-safe:animate-fade-up sm:text-5xl lg:text-6xl">
              Know which customers are likely to leave, and why.
            </h1>
            <p
              className="mt-6 max-w-lg text-lg leading-relaxed text-muted motion-safe:animate-fade-up"
              style={{ animationDelay: '120ms' }}
            >
              Nexus brings your customer data, churn risk and support history
              together, so your team can see why a customer is at risk and
              decide what to do next.
            </p>
            <Link
              to="/app"
              className="mt-8 inline-block rounded-lg bg-accent px-5 py-3 text-sm font-medium text-white transition duration-150 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:scale-[0.98] motion-safe:animate-fade-up"
              style={{ animationDelay: '240ms' }}
            >
              Open Nexus
            </Link>
            <p
              className="mt-6 max-w-md text-sm text-muted motion-safe:animate-fade-up"
              style={{ animationDelay: '320ms' }}
            >
              Early build: importing customer CSV files works today. Risk
              prediction, support evidence and recommendations are in
              development.
            </p>
          </div>

          <div
            className="motion-safe:animate-fade-up"
            style={{ animationDelay: '300ms' }}
          >
            <ReasoningChain />
          </div>
        </section>

        <Principles />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-6xl px-6 py-8 text-sm text-muted">
          Nexus AI. Customer retention intelligence, built step by step.
        </div>
      </footer>
    </div>
  )
}

export default Landing