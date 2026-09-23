import { useEffect, useState } from 'react'
import { referenceService } from '../services/api'

export const isoDate = (offsetDays) => new Date(Date.now() + offsetDays * 86400000).toISOString().slice(0, 10)
const CABINS = [['ECONOMY', 'Economy'], ['PREMIUM_ECONOMY', 'Premium Economy'], ['BUSINESS', 'Business'], ['FIRST', 'First']]

export const DEFAULT_SEARCH = {
  trip: 'ONE_WAY', origin: 'DEL', destination: 'LHR', date: isoDate(1), returnDate: '',
  cabin: 'ECONOMY', adults: 1, children: 0, infants: 0,
}

// Search criteria <-> URL query string, so results can be shared and the home page can hand off.
export const toQuery = (f) => new URLSearchParams(Object.entries(f).filter(([, v]) => v !== '' && v !== null))
export const fromQuery = (params) => {
  const f = { ...DEFAULT_SEARCH }
  for (const key of Object.keys(f)) if (params.get(key) !== null) f[key] = params.get(key)
  for (const key of ['adults', 'children', 'infants']) f[key] = Number(f[key])
  return f
}

export default function SearchForm({ initial = DEFAULT_SEARCH, onSubmit, loading }) {
  const [form, setForm] = useState(initial)
  const [sources, setSources] = useState([])
  const [destinations, setDestinations] = useState([])
  const roundTrip = form.trip === 'ROUND_TRIP'

  useEffect(() => { setForm(initial) }, [initial])
  useEffect(() => { referenceService.sources().then(setSources).catch(() => setSources([])) }, [])
  useEffect(() => {
    if (!form.origin) return
    referenceService.destinations(form.origin).then((list) => {
      setDestinations(list)
      if (!list.some((a) => a.iata_code === form.destination)) setForm((f) => ({ ...f, destination: list[0]?.iata_code || '' }))
    }).catch(() => setDestinations([]))
  }, [form.origin]) // eslint-disable-line react-hooks/exhaustive-deps

  const update = (field, numeric = false) => (e) => setForm({ ...form, [field]: numeric ? Number(e.target.value) : e.target.value })

  // One-way keeps the return date empty; switching to round trip proposes one three days later.
  const setTrip = (trip) => setForm((f) => ({
    ...f,
    trip,
    returnDate: trip === 'ROUND_TRIP' ? f.returnDate || addDays(f.date, 3) : '',
  }))

  const counts = [
    ['adults', 'Adults', '12+ yrs', 1, 9],
    ['children', 'Children', '2–11 yrs', 0, 8],
    ['infants', 'Infants', 'under 2, on lap', 0, form.adults],
  ]

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(form) }} className="card space-y-4">
      <div className="flex gap-2">
        {[['ONE_WAY', 'One way'], ['ROUND_TRIP', 'Round trip']].map(([value, label]) => (
          <button key={value} type="button" onClick={() => setTrip(value)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold ${form.trip === value ? 'bg-blue-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            {label}
          </button>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-5">
        <Field label="From">
          <select className="input" value={form.origin} onChange={update('origin')} required>
            {sources.map((a) => <option key={a.iata_code} value={a.iata_code}>{a.city} ({a.iata_code})</option>)}
          </select>
        </Field>
        <Field label="To">
          <select className="input" value={form.destination} onChange={update('destination')} required>
            {destinations.map((a) => <option key={a.iata_code} value={a.iata_code}>{a.city} ({a.iata_code})</option>)}
          </select>
        </Field>
        <Field label="Depart">
          <input type="date" className="input" min={isoDate(0)} value={form.date} required
            onChange={(e) => setForm({ ...form, date: e.target.value, returnDate: form.returnDate && form.returnDate < e.target.value ? e.target.value : form.returnDate })} />
        </Field>
        <Field label="Return">
          <input type="date" className="input disabled:bg-slate-100" min={form.date} value={form.returnDate}
            onChange={update('returnDate')} disabled={!roundTrip} required={roundTrip} placeholder="One way" />
        </Field>
        <Field label="Cabin">
          <select className="input" value={form.cabin} onChange={update('cabin')}>
            {CABINS.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-4 sm:items-end">
        {counts.map(([key, label, hint, min, max]) => (
          <Field key={key} label={`${label} · ${hint}`}>
            <input type="number" className="input" min={min} max={max} value={form[key]} onChange={update(key, true)} />
          </Field>
        ))}
        <button className="btn-primary h-10" disabled={loading}>{loading ? 'Searching…' : 'Search flights'}</button>
      </div>
    </form>
  )
}

function addDays(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

function Field({ label, children }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  )
}
