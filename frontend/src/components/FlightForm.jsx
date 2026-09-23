import { useEffect, useState } from 'react'
import Alert from './Alert'
import useAsync from '../hooks/useAsync'
import { flightService, referenceService } from '../services/api'

const STATUSES = ['SCHEDULED', 'DELAYED', 'DEPARTED', 'CANCELLED']

// Local datetime-local value (YYYY-MM-DDTHH:mm) from an ISO string with offset.
const toInputValue = (iso) => (iso ? iso.slice(0, 16) : '')

// Create (flight = null) or edit a flight schedule. Departure is entered in origin local time.
export default function FlightForm({ flight, onSaved, onCancel }) {
  const editing = Boolean(flight)
  const [routes, setRoutes] = useState([])
  const [aircraft, setAircraft] = useState([])
  const [form, setForm] = useState({
    flight_number: flight?.flight_number || '',
    route_id: flight?.route_id || '',
    aircraft_id: flight?.aircraft_id || '',
    departure_time: toInputValue(flight?.departure_time),
    status: flight?.status || 'SCHEDULED',
  })
  const { loading, error, run } = useAsync()

  useEffect(() => {
    run(async () => {
      const [r, a] = await Promise.all([referenceService.validRoutes(), referenceService.aircraft()])
      setRoutes(r)
      setAircraft(a)
      if (!editing) setForm((f) => ({ ...f, route_id: r[0]?.route_id || '', aircraft_id: a[0]?.aircraft_id || '' }))
    })
  }, [editing, run])

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const submit = (event) => {
    event.preventDefault()
    run(async () => {
      const saved = editing
        ? await flightService.updateSchedule(flight.flight_id, changedFields(flight, form))
        : await flightService.createSchedule({
            flight_number: form.flight_number.toUpperCase(),
            route_id: form.route_id,
            aircraft_id: form.aircraft_id,
            departure_time: form.departure_time,
          })
      onSaved(saved)
    })
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label">Flight number</label>
          <input className="input uppercase" required pattern="[A-Za-z0-9]{2}[0-9]{1,4}" placeholder="UD901"
            value={form.flight_number} onChange={update('flight_number')} />
        </div>
        <div>
          <label className="label">Route</label>
          <select className="input" value={form.route_id} onChange={update('route_id')} disabled={editing} required>
            {routes.map((r) => (
              <option key={r.route_id} value={r.route_id}>{r.origin} → {r.destination} ({r.route_id})</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Aircraft</label>
          <select className="input" value={form.aircraft_id} onChange={update('aircraft_id')} required>
            {aircraft.map((a) => (
              <option key={a.aircraft_id} value={a.aircraft_id}>{a.registration} · {a.model} ({a.total_seats} seats)</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Departure (origin local time)</label>
          <input type="datetime-local" className="input" required value={form.departure_time} onChange={update('departure_time')} />
        </div>
        {editing && (
          <div>
            <label className="label">Status</label>
            <select className="input" value={form.status} onChange={update('status')}>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        )}
      </div>
      <p className="text-xs text-slate-500">An aircraft needs 4 h ground time after a domestic flight and 8 h after an international flight before its next departure.</p>
      <Alert>{error}</Alert>
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
        <button className="btn-primary" disabled={loading}>{loading ? 'Saving…' : editing ? 'Save changes' : 'Create flight'}</button>
      </div>
    </form>
  )
}

function changedFields(flight, form) {
  const changes = {}
  if (form.flight_number.toUpperCase() !== flight.flight_number) changes.flight_number = form.flight_number.toUpperCase()
  if (form.aircraft_id !== flight.aircraft_id) changes.aircraft_id = form.aircraft_id
  if (form.departure_time !== toInputValue(flight.departure_time)) changes.departure_time = form.departure_time
  if (form.status !== flight.status) changes.status = form.status
  return changes
}
