import { useState } from 'react'
import heroImg from './assets/hero.png'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight">Nexus AI</h1>
        <p className="mt-2 text-slate-400">
          Turn customer signals into intelligent retention actions.
        </p>
      </div>
    </main>
    </>
  )
}

export default App
