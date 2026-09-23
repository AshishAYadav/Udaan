// Thin HTTP client. All backend calls go through the service functions below.
const BASE_URL = import.meta.env.VITE_API_URL || ''
const TOKEN_KEY = 'udaan.token'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

// Called when the backend rejects the token, so the UI can return to the login page.
let onUnauthorized = () => {}
export const setUnauthorizedHandler = (handler) => { onUnauthorized = handler }

function describe(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(1).join('.')}: ${d.msg}`).join('; ')
  return 'Unexpected error'
}

async function request(method, path, body, { form = false, headers: extra = {} } = {}) {
  const headers = { ...extra }
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body) headers['Content-Type'] = form ? 'application/x-www-form-urlencoded' : 'application/json'

  let response
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      method,
      headers,
      body: body ? (form ? new URLSearchParams(body) : JSON.stringify(body)) : undefined,
    })
  } catch {
    throw new ApiError('Unable to reach the server. Please make sure the backend is running.', 0)
  }
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (response.status === 401 && token) onUnauthorized()
  if (!response.ok) throw new ApiError(describe(data?.detail), response.status)
  return data
}

const query = (params) => {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return entries.length ? `?${new URLSearchParams(entries)}` : ''
}

export const authService = {
  login: (username, password) => request('POST', '/auth/token', { username, password }, { form: true }),
  register: (payload) => request('POST', '/auth/register', payload),
  me: () => request('GET', '/auth/me'),
}

export const referenceService = {
  sources: () => request('GET', '/routes/sources'),
  destinations: (origin) => request('GET', `/routes/destinations${query({ origin })}`),
  validRoutes: () => request('GET', '/routes/valid'),
  tiers: () => request('GET', '/tiers'),
  aircraft: () => request('GET', '/aircrafts'),
  adminSummary: () => request('GET', '/admin/summary'),
}

export const flightService = {
  searchItineraries: (params) => request('GET', `/itineraries/search${query(params)}`),
  list: (params) => request('GET', `/flights${query(params)}`),
  get: (flightId) => request('GET', `/flights/${flightId}`),
  schedules: (params) => request('GET', `/flights/schedules${query(params)}`),
  createSchedule: (payload) => request('POST', '/flights/schedules', payload),
  updateSchedule: (flightId, payload) => request('PUT', `/flights/schedules/${flightId}`, payload),
  fares: (flightId) => request('GET', `/fares/flight/${flightId}`),
}

export const passengerService = {
  create: (payload) => request('POST', '/passengers', payload),
}

// Guests authorise follow-up payment calls with the payment's access_key.
const paymentKey = (key) => ({ headers: key ? { 'X-Payment-Key': key } : {} })

export const paymentService = {
  create: (payload) => request('POST', '/payments', payload),
  decide: (paymentId, action, key) => request('PUT', `/payments/${paymentId}`, { action }, paymentKey(key)),
  complete: (paymentId, key) => request('POST', `/payments/${paymentId}/complete`, undefined, paymentKey(key)),
}

export const bookingService = {
  create: (payload) => request('POST', '/bookings', payload),
  mine: () => request('GET', '/bookings'),
  byId: (bookingId) => request('GET', `/bookings/${bookingId}`),
  byPnr: (pnr, lastName) => request('GET', `/bookings/pnr/${encodeURIComponent(pnr)}${query({ last_name: lastName })}`),
  cancel: (bookingId, lastName, reason) =>
    request('POST', `/bookings/${bookingId}/cancel${query({ last_name: lastName })}`, { reason }),
  list: (params = {}) => request('GET', `/bookings${query(params)}`),
  remove: (bookingId) => request('DELETE', `/bookings/${bookingId}`),
}

export const checkinService = {
  validate: (pnr, lastName) => request('POST', '/checkins/validate', { pnr, last_name: lastName }),
  checkIn: (pnr, lastName, passengerIds) =>
    request('POST', '/checkins', { pnr, last_name: lastName, passenger_ids: passengerIds }),
}

export const ticketService = {
  get: (ticketId, lastName) => request('GET', `/tickets/${ticketId}${query({ last_name: lastName })}`),
}
