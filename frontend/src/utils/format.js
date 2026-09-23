// Times are displayed in the airport's local time, taken directly from the ISO string.
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export const localDate = (iso) => {
  if (!iso) return ''
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d} ${MONTHS[Number(m) - 1]} ${y}`
}

export const localTime = (iso) => (iso ? iso.slice(11, 16) : '')

export const localDateTime = (iso) => `${localDate(iso)} ${localTime(iso)}`

export const duration = (minutes) => `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`

export const money = (amount, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount)

export const titleCase = (value = '') => value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
