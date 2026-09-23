import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '../../components/Alert'
import Spinner from '../../components/Spinner'
import useAsync from '../../hooks/useAsync'
import { referenceService } from '../../services/api'

const STATS = [
  ['flights_upcoming', 'Upcoming flights'],
  ['flights_total', 'Total flights'],
  ['bookings_active', 'Active bookings'],
  ['bookings_total', 'Total bookings'],
  ['passengers', 'Passengers'],
  ['checkins', 'Check-ins'],
  ['tickets_issued', 'Tickets issued'],
  ['aircraft', 'Aircraft'],
  ['routes', 'Routes'],
  ['airports', 'Airports'],
  ['users', 'Users'],
]

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null)
  const { error, run } = useAsync()

  useEffect(() => {
    run(async () => setSummary(await referenceService.adminSummary()))
  }, [run])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Admin dashboard</h1>
        <div className="flex gap-2">
          <Link className="btn-primary" to="/admin/flights">Manage flights</Link>
          <Link className="btn-primary" to="/admin/bookings">Manage bookings</Link>
          <a className="btn-secondary" href="/docs" target="_blank" rel="noreferrer">API docs</a>
        </div>
      </div>
      <Alert>{error}</Alert>
      {!summary && !error && <Spinner />}
      {summary && (
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {STATS.map(([key, label]) => (
            <div key={key} className="card">
              <p className="label">{label}</p>
              <p className="text-3xl font-bold text-slate-900">{summary[key]}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
