// Compact baggage allowance text, e.g. "1 × 15 kg checked · 7 kg cabin + personal item".
export function baggageText(a) {
  const checked = a.checked_pieces ? `${a.checked_pieces} pc · ${a.checked_kg} kg checked` : 'No checked bag'
  const cabin = `${a.cabin_pieces > 1 ? `${a.cabin_pieces} × ` : ''}${a.cabin_kg} kg cabin${a.personal_item ? ' + personal item' : ''}`
  return `${checked} · ${cabin}`
}

const LABEL = { ADULT: 'Adult', CHILD: 'Child', INFANT: 'Infant' }

export default function BaggageList({ allowances, types = ['ADULT', 'CHILD', 'INFANT'] }) {
  return (
    <ul className="space-y-0.5 text-xs text-slate-600">
      {types.map((t) => allowances[t] && (
        <li key={t}><span className="font-semibold">🧳 {LABEL[t]}:</span> {baggageText(allowances[t])}</li>
      ))}
    </ul>
  )
}
