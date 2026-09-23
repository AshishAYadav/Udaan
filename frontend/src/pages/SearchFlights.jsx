import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Alert from '../components/Alert'
import ItineraryCard from '../components/ItineraryCard'
import SearchForm, { fromQuery, toQuery } from '../components/SearchForm'
import Spinner from '../components/Spinner'
import useAsync from '../hooks/useAsync'
import { flightService } from '../services/api'
import { useCurrency } from '../hooks/useCurrency'
import { localDate } from '../utils/format'

export default function SearchFlights() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const criteria = useMemo(() => fromQuery(params), [params])
  const [results, setResults] = useState(null)
  const [selection, setSelection] = useState({ outbound: null, return: null })
  const { loading, error, run } = useAsync()
  const { price } = useCurrency()
  const roundTrip = criteria.trip === 'ROUND_TRIP'

  // The URL is the source of truth: submitting updates it, and a URL with a date runs the search.
  useEffect(() => {
    if (!params.get('date')) return
    run(async () => {
      setSelection({ outbound: null, return: null })
      setResults(await flightService.searchItineraries({
        origin: criteria.origin, destination: criteria.destination, date: criteria.date,
        return_date: roundTrip ? criteria.returnDate : undefined, cabin_class: criteria.cabin,
        adults: criteria.adults, children: criteria.children, infants: criteria.infants,
      }))
    })
  }, [params]) // eslint-disable-line react-hooks/exhaustive-deps

  const ready = selection.outbound && (!roundTrip || selection.return)
  const total = [selection.outbound, selection.return].filter(Boolean).reduce((sum, it) => sum + it.available_classes[0].party_total, 0)

  const proceed = () => {
    const next = new URLSearchParams({
      out: selection.outbound.flight_ids.join(','), class: criteria.cabin,
      a: criteria.adults, c: criteria.children, i: criteria.infants,
    })
    if (roundTrip) next.set('ret', selection.return.flight_ids.join(','))
    navigate(`/book?${next}`)
  }

  const journey = (key, title, list) => (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      {list.length === 0 && <Alert type="info">No flights with enough seats on this date. Try another date or cabin.</Alert>}
      {list.map((it) => (
        <ItineraryCard key={it.itinerary_id} itinerary={it} party={results.party}
          selected={selection[key]?.itinerary_id === it.itinerary_id}
          onSelect={() => setSelection({ ...selection, [key]: it })} />
      ))}
    </section>
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Book a flight</h1>
      <SearchForm initial={criteria} loading={loading} onSubmit={(form) => setParams(toQuery(form))} />
      <p className="text-xs text-slate-500">
        Direct flights and one-stop connections are shown, with 3–4 departures a day on every route (morning, afternoon and night). Book up to 2 months ahead.
      </p>

      <Alert>{error}</Alert>
      {loading && <Spinner label="Searching flights…" />}

      {results && !loading && (
        <div className="space-y-8 pb-24">
          {journey('outbound', `Outbound · ${criteria.origin} → ${criteria.destination} · ${localDate(criteria.date)}`, results.outbound)}
          {roundTrip && journey('return', `Return · ${criteria.destination} → ${criteria.origin} · ${localDate(criteria.returnDate)}`, results.return)}
        </div>
      )}

      {ready && (
        <div className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-200 bg-white/95 py-3 shadow-lg">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4">
            <p className="text-sm">
              Trip total for {criteria.adults + criteria.children + criteria.infants} passenger(s):{' '}
              <span className="text-lg font-bold">{price(total)}</span>
            </p>
            <button className="btn-primary" onClick={proceed}>Continue</button>
          </div>
        </div>
      )}
    </div>
  )
}
