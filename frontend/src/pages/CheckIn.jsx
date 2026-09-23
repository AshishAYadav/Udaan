import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Alert from '../components/Alert'
import BoardingPass from '../components/BoardingPass'
import LookupForm from '../components/LookupForm'
import StatusBadge from '../components/StatusBadge'
import useAsync from '../hooks/useAsync'
import { checkinService, ticketService } from '../services/api'
import { localDateTime, titleCase } from '../utils/format'

export default function CheckIn() {
  const [params] = useSearchParams()
  const [lookup, setLookup] = useState({ pnr: params.get('pnr') || '', lastName: params.get('last_name') || '' })
  const [validation, setValidation] = useState(null)
  const [selected, setSelected] = useState({}) // flight_id -> passenger ids
  const [passes, setPasses] = useState([])
  const [notice, setNotice] = useState('')
  const { loading, error, run } = useAsync()

  const load = async (pnr, lastName) => {
    const result = await checkinService.validate(pnr, lastName)
    setValidation(result)
    setSelected(Object.fromEntries(result.segments.map((s) => [s.flight_id, s.passengers.filter((p) => p.eligible).map((p) => p.passenger_id)])))
    const ticketIds = result.booking.segments.flatMap((s) => s.passengers.map((p) => p.ticket_id)).filter(Boolean)
    setPasses(await Promise.all(ticketIds.map((id) => ticketService.get(id, lastName))))
  }

  const validate = (pnr, lastName) =>
    run(async () => {
      setNotice('')
      setLookup({ pnr, lastName })
      await load(pnr, lastName)
    })

  useEffect(() => {
    if (lookup.pnr && lookup.lastName) validate(lookup.pnr, lookup.lastName)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // An adult and the infant on their lap are always selected together.
  const toggle = (segment, passenger) => {
    const current = new Set(selected[segment.flight_id] || [])
    const partner = segment.passengers.find((p) => p.passenger_id === passenger.travels_with && p.eligible)
    const on = !current.has(passenger.passenger_id)
    for (const id of [passenger.passenger_id, partner?.passenger_id].filter(Boolean)) on ? current.add(id) : current.delete(id)
    setSelected({ ...selected, [segment.flight_id]: [...current] })
  }

  const checkIn = (segment) =>
    run(async () => {
      const result = await checkinService.checkIn(lookup.pnr, lookup.lastName, [segment.flight_id], selected[segment.flight_id])
      setNotice(`${result.checkins.length} boarding pass(es) issued for ${segment.flight_number}.`)
      await load(lookup.pnr, lookup.lastName)
    })

  const names = Object.fromEntries((validation?.booking.passengers || []).map((p) => [p.passenger_id, `${p.first_name} ${p.last_name}`]))
  const types = Object.fromEntries((validation?.booking.passengers || []).map((p) => [p.passenger_id, p.passenger_type]))

  return (
    <div className="space-y-6">
      <div className="space-y-6 print:hidden">
        <div>
          <h1 className="text-2xl font-bold">Online check-in</h1>
          <p className="text-sm text-slate-500">Check-in opens 48 hours and closes 4 hours before each flight. Check in each flight separately, one passenger at a time or all together.</p>
        </div>
        <LookupForm initialPnr={lookup.pnr} initialLastName={lookup.lastName} submitLabel="Find booking" loading={loading} onSubmit={validate} />
        <Alert type="success">{notice}</Alert>
        <Alert>{error}</Alert>

        {validation && (
          <div className="space-y-4">
            <p className="text-sm">Booking <span className="font-mono font-bold">{validation.booking.pnr}</span> · <StatusBadge status={validation.booking.status} /></p>
            {validation.segments.map((segment) => {
              const flight = validation.booking.segments.find((s) => s.flight_id === segment.flight_id).flight
              const chosen = selected[segment.flight_id] || []
              return (
                <div key={segment.flight_id} className={`card space-y-3 ${segment.open ? 'border-blue-200' : ''}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">
                      <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{titleCase(segment.direction)}</span>
                      {segment.flight_number} · {flight.origin.code} → {flight.destination.code} · {localDateTime(flight.departure)}
                    </p>
                    <StatusBadge status={segment.phase} />
                  </div>
                  <p className="text-xs text-slate-500">
                    Check-in window: {localDateTime(segment.checkin_opens_at)} – {localDateTime(segment.checkin_closes_at)} (UTC)
                    {segment.reason && <span className="ml-2 text-amber-700">· {segment.reason}</span>}
                  </p>
                  <ul className="divide-y divide-slate-100 text-sm">
                    {segment.passengers.map((p) => (
                      <li key={p.passenger_id} className="flex items-center justify-between gap-3 py-1.5">
                        <label className="flex items-center gap-2">
                          <input type="checkbox" className="h-4 w-4" disabled={!p.eligible || loading}
                            checked={chosen.includes(p.passenger_id)} onChange={() => toggle(segment, p)} />
                          <span className="font-medium">{names[p.passenger_id]}</span>
                          <span className="text-xs text-slate-500">{titleCase(types[p.passenger_id])}</span>
                          {p.travels_with && <span className="text-xs text-slate-400">with {names[p.travels_with]}</span>}
                        </label>
                        {p.checked_in ? <StatusBadge status="CHECKED_IN" /> : !p.eligible && <span className="text-xs text-slate-400">Not available</span>}
                      </li>
                    ))}
                  </ul>
                  {segment.open && segment.passengers.some((p) => p.eligible) && (
                    <div className="flex justify-end">
                      <button className="btn-primary" disabled={loading || !chosen.length} onClick={() => checkIn(segment)}>
                        {loading ? 'Checking in…' : `Check in ${chosen.length} passenger(s) on ${segment.flight_number}`}
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
            <p className="text-xs text-slate-500">By checking in you confirm each passenger is fit to travel and carries no prohibited items.</p>
          </div>
        )}
      </div>

      {passes.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between print:hidden">
            <h2 className="text-xl font-bold">Boarding passes</h2>
            <button className="btn-primary" onClick={() => window.print()}>Print</button>
          </div>
          {passes.map((pass) => <BoardingPass key={pass.ticket_id} pass={pass} />)}
        </section>
      )}
    </div>
  )
}
