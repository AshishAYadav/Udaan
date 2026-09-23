import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import banner from '../banner.png'
import SearchForm, { toQuery } from '../components/SearchForm'
import { useAuth } from '../hooks/useAuth'
import { referenceService } from '../services/api'

const SERVICES = [
  { to: '/booking', icon: '🧾', title: 'Manage booking', text: 'View, change or cancel your trip with your PNR and last name.' },
  { to: '/checkin', icon: '🛫', title: 'Online check-in', text: 'Check in and print your boarding passes for every flight.' },
  { to: '/help/baggage', icon: '🧳', title: 'Baggage', text: 'Allowances by route, cabin and passenger type.' },
  { to: '/login', icon: '⭐', title: 'Udaan Club', text: 'Join for tier benefits: lounge access, extra baggage, special meals.' },
]

const DESTINATIONS = [
  { code: 'LHR', city: 'London', from: 'DEL', tag: 'via Dubai' },
  { code: 'DXB', city: 'Dubai', from: 'DEL', tag: 'Direct' },
  { code: 'SIN', city: 'Singapore', from: 'BOM', tag: 'Direct' },
  { code: 'JFK', city: 'New York', from: 'LHR', tag: 'Direct' },
]

export default function Home() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const search = (form) => navigate(`/search?${toQuery(form)}`)
  const [tiers, setTiers] = useState([])

  useEffect(() => {
    referenceService.tiers().then(setTiers).catch(() => setTiers([]))
  }, [])

  return (
    <div className="space-y-10">
      <section className="space-y-6">
        <Link to="/search" className="block overflow-hidden rounded-2xl shadow-sm ring-1 ring-slate-200">
          <img src={banner} alt="Udaan Airlines — Fly beyond your expectations. Book your flight."
            className="block aspect-[5/2] w-full object-cover object-left" />
        </Link>
        <div className="shadow-lg">
          <SearchForm onSubmit={search} />
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SERVICES.filter((s) => !(user && s.to === '/login')).map((s) => (
          <Link key={s.to} to={s.to} className="card flex gap-4 transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md">
            <span className="text-3xl">{s.icon}</span>
            <span>
              <span className="block font-semibold text-slate-900">{s.title}</span>
              <span className="text-sm text-slate-500">{s.text}</span>
            </span>
          </Link>
        ))}
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Popular destinations</h2>
        <div className="grid gap-4 sm:grid-cols-4">
          {DESTINATIONS.map((d) => (
            <Link key={d.code} to={`/search?${toQuery({ trip: 'ONE_WAY', origin: d.from, destination: d.code })}`}
              className="group overflow-hidden rounded-xl bg-gradient-to-br from-blue-800 to-sky-500 p-5 text-white shadow-sm transition hover:shadow-lg">
              <p className="text-xs uppercase tracking-widest text-blue-100">{d.from} → {d.code}</p>
              <p className="mt-6 text-2xl font-bold">{d.city}</p>
              <p className="text-sm text-blue-100">{d.tag} · <span className="underline-offset-2 group-hover:underline">Find flights</span></p>
            </Link>
          ))}
        </div>
      </section>

      {tiers.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-slate-900">Udaan Club tiers</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            {tiers.map((t) => (
              <div key={t.tier_id} className="card">
                <p className="text-lg font-bold">{t.name}</p>
                <ul className="mt-2 list-inside list-disc text-sm text-slate-600">
                  {t.benefits.map((b) => <li key={b}>{b}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
