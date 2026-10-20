import { Activity, BookOpen, Gauge, LogOut, Upload, Users } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const NAV_ITEMS = [
  { to: '/app/customers', label: 'Customers', icon: Users },
  { to: '/app/import', label: 'Import customers', icon: Upload },
  { to: '/app/model', label: 'Model', icon: Gauge },
  { to: '/app/playbook', label: 'Retention playbook', icon: BookOpen },
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
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="flex flex-col justify-between border-b border-line bg-surface lg:sticky lg:top-0 lg:h-screen lg:self-start lg:border-b-0 lg:border-r">
        <div>
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
        </div>

        {/* User Session Pill & Logout */}
        {user && (
          <div className="border-t border-line p-3">
            <div className="flex items-center justify-between rounded-lg bg-paper p-2.5 text-xs">
              <div className="truncate pr-2">
                <p className="truncate font-medium text-ink">{user.full_name}</p>
                <div className="flex items-center gap-1.5 text-[11px] text-muted">
                  <span className="capitalize">{user.role}</span>
                  <span>·</span>
                  <span className="truncate">{user.email}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={logout}
                title="Log out"
                className="rounded p-1 text-muted hover:bg-surface hover:text-ink"
              >
                <LogOut size={15} />
              </button>
            </div>
          </div>
        )}
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