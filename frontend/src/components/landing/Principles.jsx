import Reveal from '../ui/Reveal'

const PRINCIPLES = [
  {
    title: 'No data, no guess.',
    text: 'If there is not enough labeled history to train a model, Nexus says prediction is unavailable. It never makes up a score.',
  },
  {
    title: 'Facts and guesses are kept apart.',
    text: 'Measured numbers, model predictions, retrieved tickets and AI interpretation are labeled differently, so you can see what each claim rests on.',
  },
  {
    title: 'Tickets are treated as text, not orders.',
    text: 'Support messages are used as evidence only. Instructions written inside a ticket cannot change what Nexus does.',
  },
  {
    title: 'You approve every action.',
    text: 'Nexus drafts and recommends. It never sends an email, offers a discount or changes a plan on its own.',
  },
]

function Principles() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="grid gap-6 lg:grid-cols-2 lg:items-end lg:gap-16">
          <h2 className="font-display text-3xl font-medium leading-tight tracking-tight sm:text-4xl">
            Every answer shows what it is based on.
          </h2>
          <p className="max-w-md leading-relaxed text-muted">
            Retention decisions affect real customers. These are the rules
            Nexus is built to follow, and each one applies as its feature
            ships.
          </p>
        </Reveal>

        <dl className="mt-14 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {PRINCIPLES.map((item, index) => (
            <Reveal
              key={item.title}
              delay={index * 100}
              className="border-t border-line pt-5"
            >
              <dt className="font-medium text-ink">{item.title}</dt>
              <dd className="mt-2 leading-relaxed text-muted">{item.text}</dd>
            </Reveal>
          ))}
        </dl>
      </div>
    </section>
  )
}

export default Principles