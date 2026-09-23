import { NavLink, useNavigate } from 'react-router-dom'
import logo from '../logo.png'
import { useAuth } from '../hooks/useAuth'

// Links are shown only when the token carries the scope the page needs.
const LINKS = [
  { to: '/search', label: 'Book' },
  { to: '/booking', label: 'Manage booking' },
  { to: '/checkin', label: 'Check-in' },
  { to: '/admin', label: 'Admin', scope: 'admin' },
]

export default function Navbar() {
  const { user, hasScope, logout } = useAuth()
  const navigate = useNavigate()
  const visible = LINKS.filter((link) => !link.scope || (user && hasScope(link.scope)))

  const signOut = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur print:hidden">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-2">
        <NavLink to="/" aria-label="Udaan Airlines home">
          <img src={logo} alt="Udaan Airlines" className="h-12 w-auto" />
        </NavLink>
        <div className="flex flex-wrap items-center gap-1">
          {visible.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-semibold ${isActive ? 'text-blue-700' : 'text-slate-700 hover:text-blue-700'}`
              }
            >
              {label}
            </NavLink>
          ))}
          {user ? (
            <div className="ml-2 flex items-center gap-2 border-l border-slate-200 pl-3 text-sm">
              <span className="text-slate-700">{user.name}</span>
              {user.tier && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">{user.tier}</span>}
              <button className="btn-secondary py-1" onClick={signOut}>Log out</button>
            </div>
          ) : (
            <NavLink to="/login" className="btn-primary ml-2 py-1">Log in / Join</NavLink>
          )}
        </div>
      </nav>
    </header>
  )
}
