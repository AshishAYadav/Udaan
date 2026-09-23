import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Alert from '../components/Alert'
import useAsync from '../hooks/useAsync'
import { useAuth } from '../hooks/useAuth'
import { authService } from '../services/api'

const EMPTY_REGISTRATION = { username: '', password: '', first_name: '', last_name: '', email: '', phone: '' }

// `staff` renders the admin sign-in at /admin/login, the only place sandbox accounts are listed.
export default function Login({ staff = false }) {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('login')
  const [credentials, setCredentials] = useState({ username: '', password: '' })
  const [registration, setRegistration] = useState(EMPTY_REGISTRATION)
  const [notice, setNotice] = useState('')
  const { loading, error, run } = useAsync()

  const submitLogin = (event) => {
    event.preventDefault()
    run(async () => {
      await login(credentials.username, credentials.password)
      navigate(location.state?.from || (staff ? '/admin' : '/'), { replace: true })
    })
  }

  const submitRegistration = (event) => {
    event.preventDefault()
    run(async () => {
      await authService.register(registration)
      setCredentials({ username: registration.username, password: '' })
      setRegistration(EMPTY_REGISTRATION)
      setNotice('Account created. Please log in.')
      setMode('login')
    })
  }

  const field = (state, setState, name, label, type = 'text') => (
    <div>
      <label className="label" htmlFor={name}>{label}</label>
      <input id={name} type={type} className="input" required={name !== 'phone'} value={state[name]}
        onChange={(e) => setState({ ...state, [name]: e.target.value })} />
    </div>
  )

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-bold">{staff ? 'Staff sign in' : 'Sign in to Udaan'}</h1>
      {!staff && (
        <p className="text-sm text-slate-500">
          Members earn tier benefits such as lounge access and extra baggage. You can also book and check in as a guest without an account.
        </p>
      )}
      <div className={`flex gap-2 ${staff ? 'hidden' : ''}`}>
        {['login', 'register'].map((m) => (
          <button key={m} className={m === mode ? 'btn-primary' : 'btn-secondary'} onClick={() => setMode(m)}>
            {m === 'login' ? 'Log in' : 'Create account'}
          </button>
        ))}
      </div>
      <Alert type="success">{notice}</Alert>
      <Alert>{error}</Alert>

      {mode === 'login' ? (
        <form onSubmit={submitLogin} className="card space-y-4">
          {field(credentials, setCredentials, 'username', 'Username')}
          {field(credentials, setCredentials, 'password', 'Password', 'password')}
          <button className="btn-primary w-full" disabled={loading}>{loading ? 'Signing in…' : 'Log in'}</button>
          {staff && (
            <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-900">
              <p className="font-semibold">Sandbox accounts</p>
              <p>Admin: <b>admin / admin</b></p>
              <p>Demo members (password <b>password123</b>): john, emma (Gold) · priya, sofia (Silver) · ahmed, rahul (Bronze)</p>
            </div>
          )}
        </form>
      ) : (
        <form onSubmit={submitRegistration} className="card grid gap-4 sm:grid-cols-2">
          {field(registration, setRegistration, 'username', 'Username')}
          {field(registration, setRegistration, 'password', 'Password (8+ chars)', 'password')}
          {field(registration, setRegistration, 'first_name', 'First name')}
          {field(registration, setRegistration, 'last_name', 'Last name')}
          {field(registration, setRegistration, 'email', 'Email', 'email')}
          {field(registration, setRegistration, 'phone', 'Phone')}
          <button className="btn-primary sm:col-span-2" disabled={loading}>{loading ? 'Creating…' : 'Create account'}</button>
        </form>
      )}
    </div>
  )
}
