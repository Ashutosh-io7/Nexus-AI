import { Activity, Upload, Users } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/app/customers', label: 'Customers', icon: Users },
  { to: '/app/import', label: 'Import customers', icon: Upload },
  { to: '/app/status', label: 'System status', icon: Activity },
]

function navLinkClass({ isActive }) {
  return [
    'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium',
    isActive
      ? 'bg-paper text-ink'
      : 'text-muted hover:bg-paper hover:text-ink',
  ].join(' ')
}

function AppLayout() { 
  const location = useLocation()
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="border-b border-line bg-surface lg:sticky lg:top-0 lg:h-screen lg:self-start lg:border-b-0 lg:border-r">
        <div className="px-5 py-4">
          <Link
            to="/"
            className="font-display text-2xl font-medium tracking-tight"
          >
            Nexus AI
          </Link>
        </div>

        <nav aria-label="Main" className="flex gap-1 px-3 pb-3 lg:flex-col">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <NavLink key={item.to} to={item.to} className={navLinkClass}>
                <Icon size={16} aria-hidden="true" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </aside>

      <main className="px-6 py-8 lg:px-10">
        <div key={location.pathname} className="motion-safe:animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default AppLayout