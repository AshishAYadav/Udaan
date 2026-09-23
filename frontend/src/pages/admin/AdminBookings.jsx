import { useCallback, useEffect, useState } from 'react'
import Alert from '../../components/Alert'
import BookingView from '../../components/BookingView'
import Modal from '../../components/Modal'
import Spinner from '../../components/Spinner'
import StatusBadge from '../../components/StatusBadge'
import useAsync from '../../hooks/useAsync'
import { bookingService } from '../../services/api'
import { localDateTime, money, titleCase } from '../../utils/format'

const STATUSES = ['CONFIRMED', 'CHANGED', 'CANCELLED']

export default function AdminBookings() {
  const [filters, setFilters] = useState({ pnr: '', status: '', user_id: '' })
  const [bookings, setBookings] = useState([])
  const [viewing, setViewing] = useState(null)
  const [notice, setNotice] = useState('')
  const { loading, error, run } = useAsync()

  const load = useCallback(() => run(async () => setBookings(await bookingService.list(filters))), [filters, run])
  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const open = (booking) => run(async () => setViewing(await bookingService.byId(booking.booking_id)))

  const cancel = (booking) => {
    if (!window.confirm(`Cancel booking ${booking.pnr}? Seats are released and the payment refunded.`)) return
    run(async () => {
      await bookingService.cancel(booking.booking_id, undefined, 'Cancelled by admin')
      setNotice(`Booking ${booking.pnr} cancelled.`)
      setBookings(await bookingService.list(filters))
    })
  }

  const remove = (booking) => {
    if (!window.confirm(`Permanently delete booking ${booking.pnr}? This also removes its check-ins, tickets and SSRs.`)) return
    run(async () => {
      await bookingService.remove(booking.booking_id)
      setNotice(`Booking ${booking.pnr} deleted.`)
      setBookings(await bookingService.list(filters))
    })
  }

  const update = (field) => (e) => setFilters({ ...filters, [field]: e.target.value.toUpperCase() })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bookings</h1>
      <form className="card grid gap-3 sm:grid-cols-4 sm:items-end" onSubmit={(e) => { e.preventDefault(); load() }}>
        <div><label className="label">PNR</label><input className="input uppercase" maxLength={6} value={filters.pnr} onChange={update('pnr')} /></div>
        <div><label className="label">User ID</label><input className="input uppercase" value={filters.user_id} onChange={update('user_id')} placeholder="USR002" /></div>
        <div>
          <label className="label">Status</label>
          <select className="input" value={filters.status} onChange={update('status')}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <button className="btn-secondary">Filter</button>
      </form>

      <Alert type="success">{notice}</Alert>
      <Alert>{error}</Alert>

      <div className="card overflow-x-auto p-0">
        <table className="data-table">
          <thead>
            <tr><th>PNR</th><th>Booked by</th><th>Trip</th><th>Flights</th><th>Cabin</th><th>Pax</th><th>Amount</th><th>Status</th><th>Created</th><th /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {bookings.map((b) => (
              <tr key={b.booking_id}>
                <td className="font-mono font-semibold">{b.pnr}<div className="text-xs font-normal text-slate-500">{b.booking_id}</div></td>
                <td>{b.user_id || <span className="text-slate-500">Guest</span>}</td>
                <td>{titleCase(b.trip_type)}</td>
                <td className="text-xs">{b.segments.map((s) => s.flight_id).join(' · ')}</td>
                <td>{titleCase(b.class_id)}</td>
                <td>{b.passenger_ids.length}</td>
                <td>{money(b.total_amount, b.currency)}</td>
                <td><StatusBadge status={b.status} /></td>
                <td className="text-xs">{localDateTime(b.created_at)}</td>
                <td className="space-x-1">
                  <button className="btn-secondary py-1" onClick={() => open(b)}>View</button>
                  {['CONFIRMED', 'CHANGED'].includes(b.status) && <button className="btn-secondary py-1" onClick={() => cancel(b)}>Cancel</button>}
                  <button className="btn-danger py-1" onClick={() => remove(b)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <div className="px-4"><Spinner /></div>}
        {!loading && bookings.length === 0 && <p className="p-4 text-sm text-slate-500">No bookings match the filters.</p>}
      </div>

      {viewing && (
        <Modal title={`Booking ${viewing.pnr}`} onClose={() => setViewing(null)}>
          <BookingView booking={viewing} />
        </Modal>
      )}
    </div>
  )
}
