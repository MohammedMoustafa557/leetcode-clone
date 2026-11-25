import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Logo } from '../components/NavBar'

function AuthShell({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
          <span style={{ width: 44, height: 44, display: 'block' }}><Logo /></span>
        </div>
        <h1>{title}</h1>
        <p className="sub">{sub}</p>
        {children}
      </div>
    </div>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ login: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setError('')
    try { await login(form.login, form.password); navigate('/problems') }
    catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }

  return (
    <AuthShell title="Welcome back" sub="Sign in to track your progress">
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="login">Username or email</label>
          <input id="login" className="input" autoComplete="username" required value={form.login} onChange={(e) => setForm({ ...form, login: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" className="input" type="password" autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>{busy ? <span className="spinner" /> : 'Sign in'}</button>
      </form>
      <p className="switch">New here? <Link to="/register">Create an account</Link></p>
    </AuthShell>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setError('')
    try { await register(form.username, form.email, form.password); navigate('/problems') }
    catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }

  return (
    <AuthShell title="Create your account" sub="Practice 2,800+ interview problems">
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="username">Username</label>
          <input id="username" className="input" autoComplete="username" required minLength={3} maxLength={32} pattern="[A-Za-z0-9_.\-]+" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" className="input" type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="password">Password <span className="faint">(min 8 characters)</span></label>
          <input id="password" className="input" type="password" autoComplete="new-password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>{busy ? <span className="spinner" /> : 'Create account'}</button>
      </form>
      <p className="switch">Have an account? <Link to="/login">Sign in</Link></p>
    </AuthShell>
  )
}
