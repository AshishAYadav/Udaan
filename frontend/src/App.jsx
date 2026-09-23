import { Route, Routes } from 'react-router-dom'
import Footer from './components/Footer'
import Navbar from './components/Navbar'
import RequireAuth from './components/RequireAuth'
import Home from './pages/Home'
import Login from './pages/Login'
import SearchFlights from './pages/SearchFlights'
import BookFlight from './pages/BookFlight'
import MyBooking from './pages/MyBooking'
import CheckIn from './pages/CheckIn'
import AdminBookings from './pages/admin/AdminBookings'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminFlights from './pages/admin/AdminFlights'

const guard = (element, scope) => <RequireAuth scope={scope}>{element}</RequireAuth>

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/admin/login" element={<Login staff />} />
          <Route path="/search" element={<SearchFlights />} />
          <Route path="/book" element={<BookFlight />} />
          <Route path="/booking" element={<MyBooking />} />
          <Route path="/checkin" element={<CheckIn />} />
          <Route path="/admin" element={guard(<AdminDashboard />, 'admin')} />
          <Route path="/admin/flights" element={guard(<AdminFlights />, 'flights:write')} />
          <Route path="/admin/bookings" element={guard(<AdminBookings />, 'admin')} />
          <Route path="*" element={<p className="text-slate-500">Page not found.</p>} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
