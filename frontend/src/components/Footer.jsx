import { Link } from 'react-router-dom'
import logo from '../logo.png'

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-slate-200 bg-white print:hidden">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 text-sm text-slate-600 sm:grid-cols-4">
        <div className="sm:col-span-2">
          <img src={logo} alt="Udaan Airlines" className="h-10 w-auto" />
          <p className="mt-2 max-w-sm text-xs">
            More destinations. A brighter tomorrow. This is a sandbox system: fares, payments and tickets are simulated.
          </p>
        </div>
        <div className="space-y-1">
          <p className="font-semibold text-slate-800">Travel</p>
          <Link className="block hover:text-blue-700" to="/search">Book a flight</Link>
          <Link className="block hover:text-blue-700" to="/booking">Manage booking</Link>
          <Link className="block hover:text-blue-700" to="/checkin">Online check-in</Link>
          <Link className="block hover:text-blue-700" to="/help/baggage">Baggage</Link>
          <Link className="block hover:text-blue-700" to="/help">Help & policies</Link>
        </div>
        <div className="space-y-1">
          <p className="font-semibold text-slate-800">Udaan Club</p>
          <Link className="block hover:text-blue-700" to="/login">Join or log in</Link>
          <Link className="block hover:text-blue-700" to="/admin/login">Staff sign in</Link>
        </div>
      </div>
      <p className="border-t border-slate-100 py-3 text-center text-xs text-slate-400">© {new Date().getFullYear()} Udaan Airlines (sandbox)</p>
    </footer>
  )
}
