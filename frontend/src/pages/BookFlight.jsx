import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Alert from '../components/Alert'
import BookingView from '../components/BookingView'
import Spinner from '../components/Spinner'
import useAsync from '../hooks/useAsync'
import { useAuth } from '../hooks/useAuth'
import { bookingService, flightService, passengerService, paymentService } from '../services/api'
import { duration, localDateTime, money, titleCase } from '../utils/format'

const STEPS = ['Itinerary', 'Passengers', 'Review', 'Payment', 'Confirmation']
const emptyPassenger = (type = 'ADULT') => ({ first_name: '', last_name: '', date_of_birth: '', gender: 'M', passenger_type: type })
const ids = (value) => (value ? value.split(',').filter(Boolean) : [])
const TYPE_LABEL = { ADULT: 'Adult (12+)', CHILD: 'Child (2–11)', INFANT: 'Infant (under 2)' }

// One passenger row per adult, child and infant chosen in search.
const initialPassengers = (params) => {
  const count = (key, fallback) => Math.max(0, Number(params.get(key) ?? fallback) || 0)
  const rows = [
    ...Array(Math.max(1, count('a', 1))).fill('ADULT'),
    ...Array(count('c', 0)).fill('CHILD'),
    ...Array(count('i', 0)).fill('INFANT'),
  ]
  return rows.map(emptyPassenger)
}

export default function BookFlight() {
  const [params] = useSearchParams()
  const { user } = useAuth()
  const selection = useMemo(
    () => ({ outbound: ids(params.get('out')), return: ids(params.get('ret')), classId: params.get('class') || 'ECONOMY' }),
    [params],
  )
  const [step, setStep] = useState(0)
  const [flights, setFlights] = useState({})
  const [fares, setFares] = useState({})
  const [passengers, setPassengers] = useState(() => initialPassengers(params))
  const [contactEmail, setContactEmail] = useState('')
  const [passengerIds, setPassengerIds] = useState([])
  const [payment, setPayment] = useState(null)
  const [decision, setDecision] = useState('APPROVE')
  const [booking, setBooking] = useState(null)
  const { loading, error, setError, run } = useAsync()

  const allIds = [...selection.outbound, ...selection.return]

  useEffect(() => {
    run(async () => {
      const loaded = await Promise.all(allIds.map((id) => Promise.all([flightService.get(id), flightService.fares(id)])))
      setFlights(Object.fromEntries(loaded.map(([f]) => [f.flight_id, f])))
      setFares(Object.fromEntries(loaded.map(([f, fr]) => [f.flight_id, fr.find((x) => x.class_id === selection.classId)])))
    })
  }, [params]) // eslint-disable-line react-hooks/exhaustive-deps

  const goTo = (next) => { setError(''); setStep(next) }
  const updatePassenger = (index, field, value) =>
    setPassengers(passengers.map((p, i) => (i === index ? { ...p, [field]: value } : p)))
  const tripPayload = (extra) => ({
    outbound_flight_ids: selection.outbound, return_flight_ids: selection.return, class_id: selection.classId, ...extra,
  })

  // Review → Payment: persist passengers, then open a PENDING payment priced by the server.
  const proceedToPayment = () =>
    run(async () => {
      const created = []
      for (const p of passengers) created.push(await passengerService.create(p))
      const newIds = created.map((p) => p.passenger_id)
      setPassengerIds(newIds)
      setPayment(await paymentService.create(tripPayload({ passenger_ids: newIds })))
      goTo(3)
    })

  const retryPayment = () => run(async () => setPayment(await paymentService.create(tripPayload({ passenger_ids: passengerIds }))))

  const completePayment = () =>
    run(async () => {
      await paymentService.decide(payment.payment_id, decision, payment.access_key)
      const completed = await paymentService.complete(payment.payment_id, payment.access_key)
      setPayment(completed)
      if (completed.status !== 'COMPLETED') {
        throw new Error('Unable to complete booking. Payment was rejected. Your seats have not been reserved.')
      }
      setBooking(await bookingService.create(tripPayload({
        passenger_ids: passengerIds, payment_id: completed.payment_id, payment_key: payment.access_key,
        contact_email: contactEmail || null,
      })))
      goTo(4)
    })

  if (!selection.outbound.length) return <Alert>No flights selected. <Link className="underline" to="/search">Search flights</Link></Alert>
  if (Object.keys(flights).length < allIds.length) return error ? <Alert>{error}</Alert> : <Spinner />

  const missingCabin = allIds.some((id) => !fares[id])
  const fareFor = (field) => allIds.reduce((sum, id) => sum + (fares[id]?.[field] || 0), 0)
  const typeFare = { ADULT: fareFor('base_price'), CHILD: fareFor('child_price'), INFANT: fareFor('infant_price') }
  const estimate = passengers.reduce((sum, p) => sum + typeFare[p.passenger_type], 0)
  const lastName = booking?.passengers[0]?.last_name || ''
  const pnrQuery = booking ? `?pnr=${booking.pnr}&last_name=${encodeURIComponent(lastName)}` : ''

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Book your trip</h1>
      <Stepper current={step} />
      <Alert>{error}</Alert>

      {step === 0 && (
        <div className="card space-y-4">
          <Journey title="Outbound" ids={selection.outbound} flights={flights} />
          {selection.return.length > 0 && <Journey title="Return" ids={selection.return} flights={flights} />}
          <div className="flex items-center justify-between border-t border-slate-100 pt-4">
            <div className="text-sm">
              <p>{titleCase(selection.classId)} · {passengers.length} passenger(s) · total <span className="text-lg font-bold">{money(estimate)}</span></p>
              <p className="text-xs text-slate-500">
                Per passenger: Adult {money(typeFare.ADULT)} · Child {money(typeFare.CHILD)} · Infant (on lap) {money(typeFare.INFANT)}
              </p>
            </div>
            <button className="btn-primary" disabled={missingCabin} onClick={() => goTo(1)}>Continue</button>
          </div>
          {missingCabin && <Alert>{titleCase(selection.classId)} is not offered on every flight. Please search again.</Alert>}
        </div>
      )}

      {step === 1 && (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); goTo(2) }}>
          {passengers.map((p, i) => (
            <div key={i} className="card grid gap-3 sm:grid-cols-6 sm:items-end">
              <div>
                <label className="label">Type</label>
                <select className="input" value={p.passenger_type} onChange={(e) => updatePassenger(i, 'passenger_type', e.target.value)}>
                  {Object.entries(TYPE_LABEL).map(([type, label]) => <option key={type} value={type}>{label}</option>)}
                </select>
                <p className="mt-1 text-xs text-slate-500">{money(typeFare[p.passenger_type])}</p>
              </div>
              <div>
                <label className="label">First name</label>
                <input className="input" required value={p.first_name} onChange={(e) => updatePassenger(i, 'first_name', e.target.value)} />
              </div>
              <div>
                <label className="label">Last name</label>
                <input className="input" required value={p.last_name} onChange={(e) => updatePassenger(i, 'last_name', e.target.value)} />
              </div>
              <div>
                <label className="label">Date of birth</label>
                <input type="date" className="input" required value={p.date_of_birth} onChange={(e) => updatePassenger(i, 'date_of_birth', e.target.value)} />
              </div>
              <div>
                <label className="label">Gender</label>
                <select className="input" value={p.gender} onChange={(e) => updatePassenger(i, 'gender', e.target.value)}>
                  <option value="M">Male</option><option value="F">Female</option><option value="X">Unspecified</option>
                </select>
              </div>
              <button type="button" className="btn-secondary" disabled={passengers.length === 1}
                onClick={() => setPassengers(passengers.filter((_, j) => j !== i))}>Remove</button>
            </div>
          ))}
          <div className="flex flex-wrap justify-between gap-2">
            <div className="flex gap-2">
              {['ADULT', 'CHILD', 'INFANT'].map((type) => (
                <button key={type} type="button" className="btn-secondary" disabled={passengers.length >= 9}
                  onClick={() => setPassengers([...passengers, emptyPassenger(type)])}>+ {titleCase(type)}</button>
              ))}
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => goTo(0)}>Back</button>
              <button className="btn-primary">Review</button>
            </div>
          </div>
        </form>
      )}

      {step === 2 && (
        <div className="card space-y-4">
          <Journey title="Outbound" ids={selection.outbound} flights={flights} />
          {selection.return.length > 0 && <Journey title="Return" ids={selection.return} flights={flights} />}
          <ul className="divide-y divide-slate-100 rounded-md border border-slate-200">
            {passengers.map((p, i) => (
              <li key={i} className="flex justify-between px-4 py-2 text-sm">
                <span className="font-medium">{p.first_name} {p.last_name}</span>
                <span className="text-slate-500">{titleCase(p.passenger_type)} · {p.date_of_birth} · {money(typeFare[p.passenger_type])}</span>
              </li>
            ))}
          </ul>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="label">Booking as</p>
              {user ? (
                <p className="font-semibold">{user.name} <span className="text-xs text-slate-500">({user.tier || user.role})</span></p>
              ) : (
                <p className="text-sm">
                  <span className="font-semibold">Guest</span> — <Link className="text-blue-700 underline" to="/login" state={{ from: `/book?${params}` }}>log in</Link> to earn tier benefits and add special services.
                </p>
              )}
            </div>
            <div>
              <label className="label">Contact email</label>
              <input type="email" className="input" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => goTo(1)}>Back</button>
            <button className="btn-primary" disabled={loading} onClick={proceedToPayment}>
              {loading ? 'Preparing…' : 'Continue to payment'}
            </button>
          </div>
        </div>
      )}

      {step === 3 && payment && (
        <div className="card max-w-lg space-y-4">
          <div>
            <p className="label">Payment amount</p>
            <p className="text-3xl font-bold">{money(payment.amount, payment.currency)}</p>
            <ul className="mt-1 text-sm text-slate-500">
              {Object.entries(payment.breakdown.reduce((acc, line) => ({ ...acc, [line.passenger_type]: (acc[line.passenger_type] || 0) + line.amount }), {}))
                .map(([type, amount]) => <li key={type}>{titleCase(type)} fares: {money(amount, payment.currency)}</li>)}
            </ul>
            <p className="text-xs text-slate-400">{passengerIds.length} passenger(s) × {allIds.length} flight(s)</p>
          </div>
          <Alert type="info">Mock payment gateway — no card details are needed.</Alert>
          {payment.status === 'PENDING' ? (
            <>
              <fieldset className="space-y-2">
                <legend className="label">Payment result</legend>
                {['APPROVE', 'REJECT'].map((option) => (
                  <label key={option} className="flex items-center gap-2 text-sm">
                    <input type="radio" name="decision" checked={decision === option} onChange={() => setDecision(option)} />
                    {titleCase(option)}
                  </label>
                ))}
              </fieldset>
              <button className="btn-primary w-full" disabled={loading} onClick={completePayment}>
                {loading ? 'Processing…' : 'Complete payment'}
              </button>
            </>
          ) : (
            <button className="btn-secondary w-full" disabled={loading} onClick={retryPayment}>Try payment again</button>
          )}
        </div>
      )}

      {step === 4 && booking && (
        <div className="space-y-4">
          <Alert type="success">Payment approved — your booking is confirmed.</Alert>
          <BookingView booking={booking} />
          <div className="flex gap-2">
            <Link className="btn-secondary" to={`/booking${pnrQuery}`}>View booking</Link>
            <Link className="btn-primary" to={`/checkin${pnrQuery}`}>Check in</Link>
          </div>
        </div>
      )}
    </div>
  )
}

function Journey({ title, ids: flightIds, flights }) {
  return (
    <div>
      <p className="label">{title}</p>
      <ul className="space-y-1 text-sm">
        {flightIds.map((id) => {
          const f = flights[id]
          return (
            <li key={id} className="flex flex-wrap gap-x-4">
              <span className="font-semibold">{f.flight_number}</span>
              <span>{f.departure_airport} → {f.arrival_airport}</span>
              <span>{localDateTime(f.departure_time)} → {localDateTime(f.arrival_time)}</span>
              <span className="text-slate-500">{duration(f.duration_minutes)} · {f.aircraft_model}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Stepper({ current }) {
  return (
    <ol className="flex flex-wrap gap-2 text-sm">
      {STEPS.map((label, i) => (
        <li key={label} className={`rounded-full px-3 py-1 ${i === current ? 'bg-blue-600 text-white' : i < current ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-500'}`}>
          {i + 1}. {label}
        </li>
      ))}
    </ol>
  )
}
