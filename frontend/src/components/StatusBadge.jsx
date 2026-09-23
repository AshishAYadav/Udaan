const COLORS = {
  CONFIRMED: 'bg-green-100 text-green-800',
  CHANGED: 'bg-green-100 text-green-800',
  COMPLETED: 'bg-green-100 text-green-800',
  CHECKED_IN: 'bg-green-100 text-green-800',
  ISSUED: 'bg-green-100 text-green-800',
  SCHEDULED: 'bg-blue-100 text-blue-800',
  PENDING: 'bg-amber-100 text-amber-800',
  DELAYED: 'bg-amber-100 text-amber-800',
  APPROVED: 'bg-amber-100 text-amber-800',
  CANCELLED: 'bg-red-100 text-red-800',
  REJECTED: 'bg-red-100 text-red-800',
  FAILED: 'bg-red-100 text-red-800',
  REFUNDED: 'bg-slate-200 text-slate-700',
  DEPARTED: 'bg-slate-200 text-slate-700',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${COLORS[status] || 'bg-slate-100 text-slate-700'}`}>
      {status?.replaceAll('_', ' ')}
    </span>
  )
}
