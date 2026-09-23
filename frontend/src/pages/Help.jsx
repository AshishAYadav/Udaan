import { marked } from 'marked'
import { useEffect, useState } from 'react'
import { NavLink, useNavigate, useParams } from 'react-router-dom'
import Alert from '../components/Alert'
import { baggageText } from '../components/Baggage'
import Spinner from '../components/Spinner'
import useAsync from '../hooks/useAsync'
import { policyService } from '../services/api'
import { titleCase } from '../utils/format'

// Policies are Markdown documents served by the API (docs/policies) — the same text an AI assistant retrieves.
export default function Help() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [policies, setPolicies] = useState([])
  const [doc, setDoc] = useState(null)
  const [baggage, setBaggage] = useState([])
  const { loading, error, run } = useAsync()

  useEffect(() => {
    run(async () => {
      const list = await policyService.list()
      setPolicies(list)
      if (!slug && list.length) navigate(`/help/${list[0].slug}`, { replace: true })
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!slug) return
    run(async () => {
      setDoc(await policyService.get(slug))
      if (slug === 'baggage') setBaggage(await policyService.baggage())
    })
  }, [slug, run])

  return (
    <div className="grid gap-6 md:grid-cols-[220px_1fr]">
      <aside className="space-y-1">
        <h1 className="mb-2 text-lg font-bold">Help & policies</h1>
        {policies.map((p) => (
          <NavLink key={p.slug} to={`/help/${p.slug}`}
            className={({ isActive }) => `block rounded-md px-3 py-2 text-sm ${isActive ? 'bg-blue-50 font-semibold text-blue-700' : 'text-slate-600 hover:bg-slate-100'}`}>
            {p.title}
          </NavLink>
        ))}
      </aside>
      <article className="card min-w-0">
        <Alert>{error}</Alert>
        {loading && !doc && <Spinner />}
        {doc && <div className="policy" dangerouslySetInnerHTML={{ __html: marked.parse(doc.content) }} />}
        {slug === 'baggage' && baggage.length > 0 && (
          <div className="mt-6 overflow-x-auto">
            <h2 className="mb-2 text-lg font-semibold">Allowance table (live)</h2>
            <table className="data-table">
              <thead><tr><th>Route</th><th>Cabin</th><th>Adult / Child</th><th>Infant</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {baggage.map((row) => (
                  <tr key={`${row.route_type}-${row.class_id}`}>
                    <td>{titleCase(row.route_type)}</td>
                    <td>{titleCase(row.class_id)}</td>
                    <td className="whitespace-normal">{baggageText(row.ADULT)}</td>
                    <td className="whitespace-normal">{baggageText(row.INFANT)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </div>
  )
}
