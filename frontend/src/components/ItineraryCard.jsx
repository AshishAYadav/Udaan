import BaggageList from './Baggage'
import { useCurrency } from '../hooks/useCurrency'
import { duration, localDate, localTime } from '../utils/format'

// One itinerary (direct or connecting). Search is already filtered to a single cabin.
export default function ItineraryCard({ itinerary, party, selected, onSelect }) {
  const { price } = useCurrency()
  const cabin = itinerary.available_classes[0]
  const types = ['ADULT', ...(party?.children ? ['CHILD'] : []), ...(party?.infants ? ['INFANT'] : [])]
  return (
    <div className={`card space-y-3 ${selected ? 'border-blue-500 ring-2 ring-blue-100' : ''}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-5">
          <div>
            <p className="text-xl font-bold">{localTime(itinerary.departure)}</p>
            <p className="text-xs text-slate-500">{itinerary.origin.code} · {localDate(itinerary.departure)}</p>
          </div>
          <div className="text-center text-xs text-slate-500">
            <p>{duration(itinerary.total_duration_minutes)}</p>
            <p className="font-semibold text-slate-700">
              {itinerary.stops ? `1 stop · ${itinerary.layovers[0].airport.code}` : 'Direct'}
            </p>
          </div>
          <div>
            <p className="text-xl font-bold">{localTime(itinerary.arrival)}</p>
            <p className="text-xs text-slate-500">{itinerary.destination.code} · {localDate(itinerary.arrival)}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-lg font-bold">{price(cabin.party_total)}</p>
            <p className="text-xs text-slate-500">
              {cabin.name} · Adult {price(cabin.price)}
              {party?.children > 0 && ` · Child ${price(cabin.child_price)}`}
              {party?.infants > 0 && ` · Infant ${price(cabin.infant_price)}`}
            </p>
            <p className="text-xs text-slate-400">{cabin.available_seats} seats left</p>
          </div>
          <button className={selected ? 'btn-primary' : 'btn-secondary'} onClick={onSelect}>{selected ? 'Selected' : 'Select'}</button>
        </div>
      </div>
      <ol className="space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-600">
        {itinerary.segments.map((s, i) => (
          <li key={s.flight_id}>
            <span className="font-semibold">{s.flight_number}</span> {s.origin.code} {localTime(s.departure)} → {s.destination.code} {localTime(s.arrival)}
            <span className="text-slate-400"> · {s.aircraft_model}</span>
            {itinerary.layovers[i] && (
              <span className="ml-2 rounded bg-amber-50 px-1.5 text-amber-800">
                {duration(itinerary.layovers[i].minutes)} connection in {itinerary.layovers[i].airport.code}
              </span>
            )}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap items-start justify-between gap-2 border-t border-slate-100 pt-2">
        <BaggageList allowances={cabin.baggage} types={types} />
        <span className="text-xs text-slate-400">{itinerary.domestic ? 'Domestic' : 'International'} allowance</span>
      </div>
    </div>
  )
}
