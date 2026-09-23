import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import banner from '../banner.png'
import SearchForm, { toQuery } from '../components/SearchForm'
import { useAuth } from '../hooks/useAuth'
import { referenceService } from '../services/api'

const SERVICES = [
  { to: '/booking', icon: '🧾', title: 'Manage booking', text: 'View, change or cancel your trip with your PNR and last name.' },
  { to: '/checkin', icon: '🛫', title: 'Online check-in', text: 'Check in and print your boarding passes for every flight.' },
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
    <div className="-mt-8 space-y-10">
      <Link to="/search" className="-mx-4 block overflow-hidden sm:mx-0 sm:rounded-b-2xl">
        <img src={banner} alt="Udaan Airlines — Fly beyond your expectations. Book your flight." className="w-full object-cover" />
      </Link>

      <section className="relative -mt-16 px-2 sm:-mt-24 sm:px-6">
        <div className="shadow-xl">
          <SearchForm onSubmit={search} />
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
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
