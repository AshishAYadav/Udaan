import { Navigate, useLocation } from 'react-router-dom'
import Alert from './Alert'
import { useAuth } from '../hooks/useAuth'

// Redirects to login when signed out; shows a message when the token lacks a scope.
export default function RequireAuth({ scope, children }) {
  const { user, hasScope } = useAuth()
  const location = useLocation()
  const loginPath = location.pathname.startsWith('/admin') ? '/admin/login' : '/login'
  if (!user) return <Navigate to={loginPath} replace state={{ from: location.pathname + location.search }} />
  if (scope && !hasScope(scope)) return <Alert>You do not have permission to view this page.</Alert>
  return children
}
