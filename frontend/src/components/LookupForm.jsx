import { useState } from 'react'

// PNR + last name form shared by My Booking and Check-in.
export default function LookupForm({ initialPnr = '', initialLastName = '', submitLabel, loading, onSubmit }) {
  const [pnr, setPnr] = useState(initialPnr)
  const [lastName, setLastName] = useState(initialLastName)

  const submit = (event) => {
    event.preventDefault()
    onSubmit(pnr.trim().toUpperCase(), lastName.trim())
  }

  return (
    <form onSubmit={submit} className="card grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
      <div>
        <label className="label" htmlFor="pnr">PNR</label>
        <input id="pnr" className="input uppercase" maxLength={6} minLength={6} required value={pnr}
          onChange={(e) => setPnr(e.target.value)} placeholder="AB12CD" />
      </div>
      <div>
        <label className="label" htmlFor="lastName">Last name</label>
        <input id="lastName" className="input" required value={lastName}
          onChange={(e) => setLastName(e.target.value)} placeholder="Smith" />
      </div>
      <button className="btn-primary" disabled={loading}>{loading ? 'Searching…' : submitLabel}</button>
    </form>
  )
}
