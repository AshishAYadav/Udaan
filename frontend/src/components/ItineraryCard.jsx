import { duration, localDate, localTime, money } from '../utils/format'

// One itinerary (direct or connecting). Search is already filtered to a single cabin.
export default function ItineraryCard({ itinerary, party, selected, onSelect }) {
  const cabin = itinerary.available_classes[0]
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
            <p className="text-lg font-bold">{money(cabin.party_total, cabin.currency)}</p>
            <p className="text-xs text-slate-500">
              {cabin.name} · Adult {money(cabin.price, cabin.currency)}
              {party?.children > 0 && ` · Child ${money(cabin.child_price, cabin.currency)}`}
              {party?.infants > 0 && ` · Infant ${money(cabin.infant_price, cabin.currency)}`}
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
    </div>
  )
}
