import { Link } from 'react-router-dom'
import { baggageText } from './Baggage'
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
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span>Booking <StatusBadge status={booking.status} /></span>
          {payment && <span>Payment <StatusBadge status={payment.status} /></span>}
          <span className="font-semibold">{money(booking.total_amount, booking.currency)}</span>
          {payment?.card && <span className="text-xs text-slate-500">{payment.card.brand} •••• {payment.card.last4}</span>}
        </div>
      </div>

      {booking.status === 'PENDING' && payment?.payment_url && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <span>Seats are held until <b>{localDateTime(booking.hold_expires_at)}</b> (UTC). Pay to confirm your booking.</span>
          <Link className="btn-primary py-1" to={`/pay/${payment.payment_url.split('/pay/')[1]}`}>Complete payment</Link>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>{onToggle && <th />}<th>Passenger</th><th>Type</th><th>Date of birth</th><th>Baggage</th></tr>
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
                <td>
                  {titleCase(p.passenger_type)}
                  {p.infant_on_lap_of && <div className="text-xs text-slate-500">on lap of {names[p.infant_on_lap_of]}</div>}
                </td>
                <td>{p.date_of_birth}</td>
                <td className="whitespace-normal text-xs text-slate-600">
                  {Object.entries(p.baggage).map(([direction, allowance]) => (
                    <div key={direction}>{Object.keys(p.baggage).length > 1 && <b>{titleCase(direction)}: </b>}{baggageText(allowance)}</div>
                  ))}
                </td>
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
                {localDateTime(f.departure)} → {localDateTime(f.arrival)} · {duration(f.duration_minutes)} · <StatusBadge status={f.phase} />
                {f.status === 'DELAYED' && <StatusBadge status="DELAYED" />}
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
