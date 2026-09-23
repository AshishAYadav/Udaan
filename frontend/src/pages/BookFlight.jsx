import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Alert from '../components/Alert'
import Spinner from '../components/Spinner'
import useAsync from '../hooks/useAsync'
import { useAuth } from '../hooks/useAuth'
import { useCurrency } from '../hooks/useCurrency'
import { bookingService, flightService, passengerService } from '../services/api'
import { duration, localDateTime, titleCase } from '../utils/format'

// The last step happens on the hosted payment page; it is shown here so the journey is clear.
const STEPS = ['Itinerary', 'Passengers', 'Review', 'Payment']
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
  const { currency, price } = useCurrency()
  const selection = useMemo(
    () => ({ outbound: ids(params.get('out')), return: ids(params.get('ret')), classId: params.get('class') || 'ECONOMY' }),
    [params],
  )
  const [step, setStep] = useState(0)
  const [flights, setFlights] = useState({})
  const [fares, setFares] = useState({})
  const [passengers, setPassengers] = useState(() => initialPassengers(params))
  const [contactEmail, setContactEmail] = useState('')
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

  // Review → hold the booking (PNR + seats) and continue on the hosted payment page.
  const proceedToPayment = () =>
    run(async () => {
      const created = []
      for (const p of passengers) created.push(await passengerService.create(p))
      const lastName = encodeURIComponent(passengers[0].last_name)
      const origin = window.location.origin
      const hold = await bookingService.create({
        outbound_flight_ids: selection.outbound,
        return_flight_ids: selection.return,
        class_id: selection.classId,
        passenger_ids: created.map((p) => p.passenger_id),
        contact_email: contactEmail || null,
        currency,
        success_url: `${origin}/booking?last_name=${lastName}&paid=1`,
        cancel_url: `${origin}/booking?last_name=${lastName}`,
      })
      window.location.assign(`/pay/${hold.payment.session_id}`)
    })

  if (!selection.outbound.length) return <Alert>No flights selected. <Link className="underline" to="/search">Search flights</Link></Alert>
  if (Object.keys(flights).length < allIds.length) return error ? <Alert>{error}</Alert> : <Spinner />

  const missingCabin = allIds.some((id) => !fares[id])
  const fareFor = (field) => allIds.reduce((sum, id) => sum + (fares[id]?.[field] || 0), 0)
  const typeFare = { ADULT: fareFor('base_price'), CHILD: fareFor('child_price'), INFANT: fareFor('infant_price') }
  const estimate = passengers.reduce((sum, p) => sum + typeFare[p.passenger_type], 0)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Book your trip</h1>
      <Stepper current={step} onSelect={goTo} />
      <Alert>{error}</Alert>

      {step === 0 && (
        <div className="card space-y-4">
          <Journey title="Outbound" ids={selection.outbound} flights={flights} />
          {selection.return.length > 0 && <Journey title="Return" ids={selection.return} flights={flights} />}
          <div className="flex items-center justify-between border-t border-slate-100 pt-4">
            <div className="text-sm">
              <p>{titleCase(selection.classId)} · {passengers.length} passenger(s) · total <span className="text-lg font-bold">{price(estimate)}</span></p>
              <p className="text-xs text-slate-500">
                Per passenger: Adult {price(typeFare.ADULT)} · Child {price(typeFare.CHILD)} · Infant (on lap) {price(typeFare.INFANT)}
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
                <p className="mt-1 text-xs text-slate-500">{price(typeFare[p.passenger_type])}</p>
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
                <span className="text-slate-500">{titleCase(p.passenger_type)} · {p.date_of_birth} · {price(typeFare[p.passenger_type])}</span>
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
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
            <p className="text-sm">Total <span className="text-xl font-bold">{price(estimate)}</span>
              <span className="ml-2 text-xs text-slate-500">Seats are held for 30 minutes while you pay.</span></p>
            <div className="flex gap-2">
              <button className="btn-secondary" onClick={() => goTo(1)}>Back</button>
              <button className="btn-primary" disabled={loading} onClick={proceedToPayment}>
                {loading ? 'Holding your seats…' : '🔒 Continue to secure payment'}
              </button>
            </div>
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

// Completed steps are clickable so the traveller can go back and edit.
function Stepper({ current, onSelect }) {
  return (
    <ol className="flex flex-wrap gap-2 text-sm">
      {STEPS.map((label, i) => {
        const done = i < current
        const style = i === current ? 'bg-blue-600 text-white' : done ? 'bg-blue-100 text-blue-800 hover:bg-blue-200' : 'bg-slate-100 text-slate-500'
        return (
          <li key={label}>
            <button type="button" disabled={!done} onClick={() => onSelect(i)}
              className={`rounded-full px-3 py-1 ${style} ${done ? 'cursor-pointer' : 'cursor-default'}`}>
              {done ? '✓' : i + 1}. {label}
            </button>
          </li>
        )
      })}
    </ol>
  )
}
