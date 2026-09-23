export default function BoardingPass({ pass }) {
  return (
    <div className="break-inside-avoid overflow-hidden rounded-xl border-2 border-dashed border-slate-400 bg-white">
      <div className="flex items-center justify-between bg-blue-700 px-5 py-3 text-white print:bg-white print:text-black">
        <span className="font-bold">✈ {pass.airline}</span>
        <span className="text-sm uppercase tracking-wide">Boarding Pass</span>
      </div>
      <div className="grid gap-4 p-5 sm:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          <div>
            <p className="label">Passenger</p>
            <p className="text-lg font-bold">{pass.passenger_name}</p>
          </div>
          <div className="flex items-center gap-6">
            <Airport code={pass.origin.code} city={pass.origin.city} />
            <span className="text-2xl text-slate-400">→</span>
            <Airport code={pass.destination.code} city={pass.destination.city} />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Flight" value={pass.flight_number} />
            <Field label="Date" value={pass.departure_date} />
            <Field label="Departure" value={pass.departure_local_time} />
            <Field label="Boarding" value={pass.boarding_time} />
            <Field label="Gate" value={pass.gate} />
            <Field label="Cabin" value={pass.cabin_name} />
          </div>
        </div>
        <div className="space-y-4 border-t border-dashed border-slate-300 pt-4 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0">
          <Field label="Seat" value={<span className="text-3xl">{pass.seat}</span>} />
          <Field label="PNR" value={<span className="font-mono">{pass.pnr}</span>} />
          <Field label="Ticket number" value={<span className="font-mono">{pass.ticket_number}</span>} />
          <Field label="Sequence" value={String(pass.sequence_number).padStart(3, '0')} />
        </div>
      </div>
    </div>
  )
}

function Airport({ code, city }) {
  return (
    <div>
      <p className="text-3xl font-bold">{code}</p>
      <p className="text-xs text-slate-500">{city}</p>
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  )
}
