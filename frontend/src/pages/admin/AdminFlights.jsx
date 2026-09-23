import { useCallback, useEffect, useState } from 'react'
import Alert from '../../components/Alert'
import FlightForm from '../../components/FlightForm'
import Modal from '../../components/Modal'
import Spinner from '../../components/Spinner'
import StatusBadge from '../../components/StatusBadge'
import useAsync from '../../hooks/useAsync'
import { flightService } from '../../services/api'
import { localDateTime } from '../../utils/format'

const PAGE_SIZE = 25

export default function AdminFlights() {
  const [filters, setFilters] = useState({ origin: '', destination: '', date_from: '', date_to: '', status: '' })
  const [page, setPage] = useState({ items: [], total: 0, offset: 0 })
  const [editing, setEditing] = useState(undefined) // undefined = closed, null = new flight
  const [notice, setNotice] = useState('')
  const { loading, error, run } = useAsync()

  const load = useCallback(
    (offset = 0) => run(async () => setPage(await flightService.schedules({ ...filters, limit: PAGE_SIZE, offset }))),
    [filters, run],
  )

  useEffect(() => { load(0) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const onSaved = (flight) => {
    setNotice(`Flight ${flight.flight_number} (${flight.flight_id}) saved.`)
    setEditing(undefined)
    load(page.offset)
  }

  // Fills gaps in the next 60 days: 3–4 validated flights per route per day (existing flights are kept).
  const generate = () => {
    const days = Number(window.prompt('Generate schedules for how many days from tomorrow? (1–120)', '60'))
    if (!days) return
    run(async () => {
      const result = await flightService.generateSchedules({ days })
      setNotice(`Created ${result.created} flights on ${result.routes} routes (${result.start_date} → ${result.end_date}); skipped ${result.skipped}.`)
      setPage(await flightService.schedules({ ...filters, limit: PAGE_SIZE, offset: 0 }))
    })
  }

  const update = (field) => (e) => setFilters({ ...filters, [field]: e.target.value.toUpperCase() })
  const lastItem = Math.min(page.offset + PAGE_SIZE, page.total)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Flights</h1>
        <div className="flex gap-2">
          <button className="btn-secondary" disabled={loading} onClick={generate}>⚙ Generate schedules</button>
          <button className="btn-primary" onClick={() => { setNotice(''); setEditing(null) }}>+ Add flight</button>
        </div>
      </div>

      <form className="card grid gap-3 sm:grid-cols-6 sm:items-end" onSubmit={(e) => { e.preventDefault(); load(0) }}>
        <div><label className="label">Origin</label><input className="input" maxLength={3} value={filters.origin} onChange={update('origin')} placeholder="DXB" /></div>
        <div><label className="label">Destination</label><input className="input" maxLength={3} value={filters.destination} onChange={update('destination')} placeholder="LHR" /></div>
        <div><label className="label">From</label><input type="date" className="input" value={filters.date_from} onChange={update('date_from')} /></div>
        <div><label className="label">To</label><input type="date" className="input" value={filters.date_to} onChange={update('date_to')} /></div>
        <div>
          <label className="label">Status</label>
          <select className="input" value={filters.status} onChange={update('status')}>
            <option value="">All</option>
            {['SCHEDULED', 'DELAYED', 'DEPARTED', 'CANCELLED'].map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <button className="btn-secondary">Filter</button>
      </form>

      <Alert type="success">{notice}</Alert>
      <Alert>{error}</Alert>

      <div className="card overflow-x-auto p-0">
        <table className="data-table">
          <thead>
            <tr><th>Flight</th><th>Origin</th><th>Destination</th><th>Departure</th><th>Arrival</th><th>Aircraft</th><th>Status</th><th>Phase</th><th>Seats</th><th /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {page.items.map((f) => (
              <tr key={f.flight_id}>
                <td className="font-semibold">{f.flight_number}<div className="text-xs font-normal text-slate-500">{f.flight_id}</div></td>
                <td>{f.departure_airport}</td>
                <td>{f.arrival_airport}</td>
                <td>{localDateTime(f.departure_time)}</td>
                <td>{localDateTime(f.arrival_time)}</td>
                <td>{f.aircraft_registration}<div className="text-xs text-slate-500">{f.aircraft_model}</div></td>
                <td><StatusBadge status={f.status} /></td>
                <td><StatusBadge status={f.phase} /></td>
                <td>{f.available_seats} / {f.capacity}</td>
                <td><button className="btn-secondary py-1" onClick={() => { setNotice(''); setEditing(f) }}>Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <div className="px-4"><Spinner /></div>}
        {!loading && page.items.length === 0 && <p className="p-4 text-sm text-slate-500">No flights match the filters.</p>}
      </div>

      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>{page.total ? `Showing ${page.offset + 1}–${lastItem} of ${page.total}` : ''}</span>
        <div className="flex gap-2">
          <button className="btn-secondary" disabled={page.offset === 0 || loading} onClick={() => load(page.offset - PAGE_SIZE)}>Previous</button>
          <button className="btn-secondary" disabled={lastItem >= page.total || loading} onClick={() => load(page.offset + PAGE_SIZE)}>Next</button>
        </div>
      </div>

      {editing !== undefined && (
        <Modal title={editing ? `Edit flight ${editing.flight_number}` : 'Add flight'} onClose={() => setEditing(undefined)}>
          <FlightForm flight={editing} onSaved={onSaved} onCancel={() => setEditing(undefined)} />
        </Modal>
      )}
    </div>
  )
}
