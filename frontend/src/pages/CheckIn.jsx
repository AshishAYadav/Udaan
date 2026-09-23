import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Alert from '../components/Alert'
import BoardingPass from '../components/BoardingPass'
import BookingView from '../components/BookingView'
import LookupForm from '../components/LookupForm'
import useAsync from '../hooks/useAsync'
import { checkinService, ticketService } from '../services/api'
import { titleCase } from '../utils/format'

export default function CheckIn() {
  const [params] = useSearchParams()
  const [lookup, setLookup] = useState({ pnr: params.get('pnr') || '', lastName: params.get('last_name') || '' })
  const [validation, setValidation] = useState(null)
  const [selected, setSelected] = useState([])
  const [passes, setPasses] = useState([])
  const { loading, error, run } = useAsync()

  const issuedPasses = (booking, lastName) => {
    const ticketIds = booking.segments.flatMap((s) => s.passengers.map((p) => p.ticket_id)).filter(Boolean)
    return Promise.all(ticketIds.map((id) => ticketService.get(id, lastName)))
  }

  const validate = (pnr, lastName) =>
    run(async () => {
      setLookup({ pnr, lastName })
      const result = await checkinService.validate(pnr, lastName)
      setValidation(result)
      setSelected(result.eligible_passenger_ids)
      setPasses(await issuedPasses(result.booking, lastName))
    })

  useEffect(() => {
    if (lookup.pnr && lookup.lastName) validate(lookup.pnr, lookup.lastName)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (id) => setSelected(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id])

  const confirm = () =>
    run(async () => {
      await checkinService.checkIn(lookup.pnr, lookup.lastName, selected)
      const result = await checkinService.validate(lookup.pnr, lookup.lastName)
      setValidation(result)
      setSelected(result.eligible_passenger_ids)
      setPasses(await issuedPasses(result.booking, lookup.lastName))
    })

  return (
    <div className="space-y-6">
      <div className="space-y-6 print:hidden">
        <h1 className="text-2xl font-bold">Online check-in</h1>
        <LookupForm initialPnr={lookup.pnr} initialLastName={lookup.lastName} submitLabel="Find booking" loading={loading} onSubmit={validate} />
        <Alert>{error}</Alert>

        {validation && (
          <>
            {validation.reasons.map((r) => <Alert key={r} type="info">{r}</Alert>)}
            <BookingView booking={validation.booking} selectable={validation.eligible_passenger_ids} selected={selected}
              onToggle={validation.can_check_in ? toggle : undefined} activeFlightIds={validation.flight_ids} />
            {validation.can_check_in && (
              <div className="flex flex-wrap items-center justify-between gap-4">
                <p className="text-sm text-slate-500">
                  Checking in for the <b>{titleCase(validation.direction)}</b> journey ({validation.flight_ids.length} flight(s), highlighted).
                  I confirm the selected passengers are fit to travel and carry no prohibited items.
                </p>
                <button className="btn-primary" disabled={loading || !selected.length} onClick={confirm}>
                  {loading ? 'Checking in…' : `Confirm check-in (${selected.length})`}
                </button>
              </div>
            )}
          </>
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
