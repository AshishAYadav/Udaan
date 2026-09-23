import StatusBadge from './StatusBadge'
import { duration, localDateTime, money, titleCase } from '../utils/format'

// Reusable itinerary view: booking confirmation, My Booking and Check-in.
// Pass `selectable` + `selected` + `onToggle` to render check-in checkboxes, and
// `activeFlightIds` to highlight the segments a check-in covers.
export default function BookingView({ booking, selectable = [], selected = [], onToggle, activeFlightIds = [] }) {
  const { payment, passengers, segments } = booking
  const names = Object.fromEntries(passengers.map((p) => [p.passenger_id, `${p.first_name} ${p.last_name}`]))

  return (
    <div className="card space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="label">Booking reference (PNR)</p>
          <p className="font-mono text-3xl font-bold tracking-widest text-blue-700">{booking.pnr}</p>
          <p className="text-xs text-slate-500">{titleCase(booking.trip_type)} · {booking.cabin_name} · booking {booking.booking_id}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <span>Booking <StatusBadge status={booking.status} /></span>
          <span>Payment <StatusBadge status={payment.status} /></span>
          <span className="font-semibold">{money(payment.amount, payment.currency)}</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>{onToggle && <th />}<th>Passenger</th><th>Type</th><th>Date of birth</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {passengers.map((p) => (
              <tr key={p.passenger_id}>
                {onToggle && (
                  <td>
                    <input type="checkbox" className="h-4 w-4" disabled={!selectable.includes(p.passenger_id)}
                      checked={selected.includes(p.passenger_id)} onChange={() => onToggle(p.passenger_id)} />
                  </td>
                )}
                <td className="font-medium">{p.first_name} {p.last_name}</td>
                <td>{titleCase(p.passenger_type)}</td>
                <td>{p.date_of_birth}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {segments.map((segment) => {
        const f = segment.flight
        const active = activeFlightIds.includes(segment.flight_id)
        return (
          <div key={segment.segment_no} className={`rounded-md border p-4 ${active ? 'border-blue-300 bg-blue-50/40' : 'border-slate-200'}`}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold">
                <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{titleCase(segment.direction)} · {segment.segment_no}</span>
                {f.flight_number} · {f.origin.code} → {f.destination.code}
              </p>
              <p className="text-sm text-slate-600">
                {localDateTime(f.departure)} → {localDateTime(f.arrival)} · {duration(f.duration_minutes)} · <StatusBadge status={f.status} />
              </p>
            </div>
            <table className="data-table">
              <thead><tr><th>Passenger</th><th>Check-in</th><th>Seat</th><th>Ticket</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {segment.passengers.map((sp) => (
                  <tr key={sp.passenger_id}>
                    <td>{names[sp.passenger_id]}</td>
                    <td><StatusBadge status={sp.checkin_status} /></td>
                    <td>{sp.seat || '—'}</td>
                    <td>{sp.ticket_number || <StatusBadge status={sp.ticket_status} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })}
    </div>
  )
}
