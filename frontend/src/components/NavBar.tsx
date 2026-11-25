import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { local } from '../lib/storage'

export function Logo() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#262626" />
      <path d="M12 9l-6 7 6 7M20 9l6 7-6 7" stroke="#ffa116" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [theme, setTheme] = useState(document.documentElement.dataset.theme ?? 'dark')

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    local.set('codearena.theme', next)
    setTheme(next)
  }

  return (
    <header className="navbar">
      <Link to="/problems" className="brand"><Logo /> CodeArena</Link>
      <nav className="nav-links">
        <NavLink to="/problems">Problems</NavLink>
        <NavLink to="/plans">Study Plan</NavLink>
        <NavLink to="/learn">Learn</NavLink>
        <NavLink to="/contest">Contest</NavLink>
        <NavLink to="/leaderboard">Leaderboard</NavLink>
        {user && <NavLink to="/interview">Interview</NavLink>}
        {user && <NavLink to="/profile">Progress</NavLink>}
      </nav>
      <div className="nav-right">
        <button className="btn btn-ghost" onClick={toggleTheme} title="Toggle theme">
          {theme === 'dark' ? 'Light' : 'Dark'}
        </button>
        {user ? (
          <>
            <Link to={`/u/${user.username}`} className="avatar" title={user.username}>{user.username[0]}</Link>
            <button className="btn btn-ghost" onClick={() => { logout(); navigate('/problems') }}>Sign out</button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn btn-ghost">Sign in</Link>
            <Link to="/register" className="btn btn-primary">Register</Link>
          </>
        )}
      </div>
    </header>
  )
}
