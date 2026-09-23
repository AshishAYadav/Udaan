import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Alert from '../components/Alert'
import BookingView from '../components/BookingView'
import LookupForm from '../components/LookupForm'
import StatusBadge from '../components/StatusBadge'
import useAsync from '../hooks/useAsync'
import { useAuth } from '../hooks/useAuth'
import { bookingService } from '../services/api'
import { titleCase } from '../utils/format'

const ACTIVE = ['CONFIRMED', 'CHANGED']

export default function MyBooking() {
  const [params, setParams] = useSearchParams()
  const { user, scopes } = useAuth()
  const [booking, setBooking] = useState(null)
  const [mine, setMine] = useState([])
  const [notice, setNotice] = useState('')
  const { loading, error, run } = useAsync()
  const pnr = params.get('pnr') || ''
  const lastName = params.get('last_name') || ''
  const services = scopes.filter((s) => s.startsWith('ssr:') && !['ssr:read', 'ssr:write'].includes(s)).map((s) => titleCase(s.slice(4)))
  const passengerLastName = lastName || booking?.passengers[0]?.last_name || ''

  useEffect(() => {
    if (user) bookingService.mine().then(setMine).catch(() => setMine([]))
  }, [user])

  useEffect(() => {
    if (!pnr || !lastName) return
    run(async () => {
      const found = await bookingService.byPnr(pnr, lastName)
      setBooking(found)
      // Returning from the hosted payment page (success_url carries paid=1).
      if (params.get('paid') && found.status === 'CONFIRMED') setNotice(`Payment received — booking ${found.pnr} is confirmed. Have a great trip!`)
    })
  }, [pnr, lastName, run]) // eslint-disable-line react-hooks/exhaustive-deps

  const search = (newPnr, newLastName) => {
    setBooking(null)
    setNotice('')
    setParams({ pnr: newPnr, last_name: newLastName })
  }

  const cancel = () => {
    if (!window.confirm(`Cancel booking ${booking.pnr}? Seats are released and any payment is refunded.`)) return
    const wasPaid = booking.status !== 'PENDING'
    run(async () => {
      setBooking(await bookingService.cancel(booking.booking_id, passengerLastName, 'Cancelled online'))
      setNotice(wasPaid ? 'Your booking has been cancelled and a refund has been issued.' : 'Your seat hold has been released.')
      if (user) setMine(await bookingService.mine())
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Manage booking</h1>
        <p className="text-sm text-slate-500">Enter your booking reference (PNR) and the last name of any passenger on the booking.</p>
      </div>
      <LookupForm key={`${pnr}-${lastName}`} initialPnr={pnr} initialLastName={lastName} submitLabel="Find booking" loading={loading} onSubmit={search} />
      <Alert type="success">{notice}</Alert>
      <Alert>{error}</Alert>
      {booking && (
        <>
          <BookingView booking={booking} />
          {[...ACTIVE, 'PENDING'].includes(booking.status) && (
            <div className="flex flex-wrap gap-2">
              {ACTIVE.includes(booking.status) && (
                <Link className="btn-primary" to={`/checkin?pnr=${booking.pnr}&last_name=${encodeURIComponent(passengerLastName)}`}>Check in</Link>
              )}
              <button className="btn-danger" disabled={loading} onClick={cancel}>
                {booking.status === 'PENDING' ? 'Cancel hold' : 'Cancel booking'}
              </button>
            </div>
          )}
        </>
      )}

      {user && mine.length > 0 && (
        <section className="card space-y-3">
          <h2 className="font-semibold">Your trips</h2>
          <ul className="divide-y divide-slate-100 text-sm">
            {mine.map((b) => (
              <li key={b.booking_id} className="flex items-center justify-between gap-2 py-2">
                <span className="font-mono font-semibold">{b.pnr}</span>
                <span>{titleCase(b.trip_type)} · {b.segments.length} flight(s)</span>
                <StatusBadge status={b.status} />
                <button className="btn-secondary py-1" onClick={() => run(async () => { setNotice(''); setBooking(await bookingService.byId(b.booking_id)) })}>Open</button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {user ? (
        <p className="text-xs text-slate-500">
          Special services your membership allows: {services.length ? services.join(', ') : 'none'}. They can be requested through the API.
        </p>
      ) : (
        <p className="text-xs text-slate-500">
          <Link className="text-blue-700 underline" to="/login">Log in</Link> to see all your trips and use membership benefits.
        </p>
      )}
    </div>
  )
}
