import {
  ClipboardCheck,
  Database,
  Gauge,
  MessageSquareText,
  SlidersHorizontal,
} from 'lucide-react'

const STEPS = [
  {
    icon: Database,
    title: 'Customer data',
    kind: 'Measured',
    text: 'Plan, revenue, usage and billing from your own records.',
  },
  {
    icon: Gauge,
    title: 'Churn risk',
    kind: 'Predicted',
    text: 'A model trained on your past customers estimates who may leave.',
  },
  {
    icon: SlidersHorizontal,
    title: 'Why',
    kind: 'Explained',
    text: 'SHAP shows which factors pushed that risk up or down.',
  },
  {
    icon: MessageSquareText,
    title: 'Support history',
    kind: 'Retrieved',
    text: "The customer's real tickets, shown with their sources.",
  },
  {
    icon: ClipboardCheck,
    title: 'Next step',
    kind: 'Suggested',
    text: 'A recommended retention action. Nothing is sent without your approval.',
  },
]

function ReasoningChain() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h2 className="font-display text-xl font-medium">
        How Nexus reaches a recommendation
      </h2>
      <p className="mt-1 text-sm text-muted">
        Every step says where its information comes from.
      </p>

      <ol className="mt-6">
        {STEPS.map((step, index) => {
          const Icon = step.icon
          const isLast = index === STEPS.length - 1

          return (
            <li key={step.title} className="relative pb-7 pl-12 last:pb-0">
              {!isLast && (
                <span
                  aria-hidden="true"
                  className="absolute bottom-1 left-4 top-10 w-px bg-line"
                />
              )}
              <span
                aria-hidden="true"
                className="absolute left-0 top-0 flex size-8 items-center justify-center rounded-full border border-line bg-paper text-accent"
              >
                <Icon size={16} />
              </span>

              <div className="flex items-baseline justify-between gap-3">
                <h3 className="font-medium text-ink">{step.title}</h3>
                <span className="rounded-full bg-paper px-2 py-0.5 text-xs text-muted">
                  {step.kind}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">{step.text}</p>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

export default ReasoningChain