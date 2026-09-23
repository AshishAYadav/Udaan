import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import logo from '../logo.png'
import { paymentService } from '../services/api'
import { money } from '../utils/format'

// Sandbox test cards accepted by the gateway (see docs/policies/payments.md).
const TEST_CARDS = [
  ['Visa', '4111 1111 1111 1111'], ['Visa', '4012 8888 8888 1881'], ['Visa', '4222 2222 22222'],
  ['MasterCard', '5555 5555 5555 4444'], ['MasterCard', '5105 1051 0510 5100'],
  ['American Express', '3782 822463 10005'], ['American Express', '3714 496353 98431'], ['Amex Corporate', '3787 344936 71000'],
  ['Discover', '6011 1111 1111 1117'], ['Discover', '6011 0009 9013 9424'],
  ['JCB', '3530 1113 3330 0000'], ['JCB', '3566 0020 2036 0505'],
  ['Diners Club', '3056 930902 5904'], ['Diners Club', '3852 000002 3237'],
  ['Australian BankCard', '5610 5910 8101 8250'], ['Dankort (PBS)', '7600 9244 561'], ['Dankort (PBS)', '5019 7170 1010 3742'],
  ['Switch/Solo', '6331 1019 9999 0016'],
]

function detectBrand(digits) {
  if (/^3[47]/.test(digits)) return 'American Express'
  if (/^4/.test(digits)) return 'Visa'
  if (/^(5[1-5]|2[2-7])/.test(digits)) return 'MasterCard'
  if (/^(6011|65)/.test(digits)) return 'Discover'
  if (/^35/.test(digits)) return 'JCB'
  if (/^3(0|6|8)/.test(digits)) return 'Diners Club'
  if (/^5610/.test(digits)) return 'Australian BankCard'
  if (/^(5019|76)/.test(digits)) return 'Dankort'
  if (/^6331/.test(digits)) return 'Switch/Solo'
  return ''
}

const groupDigits = (digits) => digits.replace(/(.{4})/g, '$1 ').trim()

function useCountdown(expiresAt) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const left = Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000))
  return { left, label: `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` }
}

export default function PaymentPage() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [result, setResult] = useState(null)
  const [card, setCard] = useState({ number: '', expiry: '', cvv: '', name: '' })
  const [error, setError] = useState('')
  const [processing, setProcessing] = useState(false)
  const [showCards, setShowCards] = useState(false)

  useEffect(() => {
    paymentService.session(sessionId).then(setSession).catch((e) => setError(e.message))
  }, [sessionId])

  const digits = card.number.replace(/\D/g, '')
  const brand = detectBrand(digits)
  const cvvLength = brand === 'American Express' ? 4 : 3

  const submit = async (event) => {
    event.preventDefault()
    setProcessing(true)
    setError('')
    try {
      const paid = await paymentService.pay(sessionId, {
        card_number: digits, expiry: card.expiry.replace('/', ''), cvv: card.cvv, holder_name: card.name,
      })
      setResult(paid)
      if (paid.redirect_url) setTimeout(() => window.location.assign(paid.redirect_url), 4000)
    } catch (e) {
      setError(e.message)
    } finally {
      setProcessing(false)
    }
  }

  const setExpiry = (value) => {
    const d = value.replace(/\D/g, '').slice(0, 4)
    setCard({ ...card, expiry: d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d })
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <span className="text-lg font-extrabold tracking-tight text-slate-800">Udaan<span className="text-blue-600">Pay</span></span>
          <span className="flex items-center gap-1 text-xs font-semibold text-green-700">🔒 Secure checkout · Sandbox</span>
        </div>
      </header>

      <main className="mx-auto grid max-w-4xl gap-6 px-4 py-8 md:grid-cols-[1fr_1.2fr]">
        {!session && !error && <p className="text-slate-500">Loading payment…</p>}
        {!session && error && <Notice tone="red" title="Payment link not valid">{error}</Notice>}

        {session && (
          <>
            <aside className="space-y-4 rounded-xl bg-white p-6 shadow-sm">
              <img src={logo} alt={session.merchant} className="h-10 w-auto" />
              <div>
                <p className="text-sm text-slate-500">Pay {session.merchant}</p>
                <p className="text-3xl font-bold text-slate-900">{money(session.amount, session.currency)}</p>
                {session.currency !== session.base_currency && (
                  <p className="text-xs text-slate-500">≈ {money(session.base_amount, session.base_currency)}</p>
                )}
              </div>
              <div className="rounded-lg bg-slate-50 p-3 text-sm">
                <p className="font-semibold">{session.description}</p>
                <p className="text-xs text-slate-500">{session.passengers} passenger(s)</p>
                <ul className="mt-2 space-y-0.5 text-xs text-slate-600">
                  {session.itinerary.map((line) => <li key={line}>✈ {line}</li>)}
                </ul>
              </div>
              {session.status === 'PENDING' && !result && <Countdown expiresAt={session.expires_at} />}
            </aside>

            <section className="rounded-xl bg-white p-6 shadow-sm">
              {result ? (
                <Notice tone="green" title="Payment successful">
                  <p>{money(result.amount, result.currency)} paid with {result.card.brand} •••• {result.card.last4}.</p>
                  <p className="mt-1">Booking <b>{result.pnr}</b> is confirmed. A receipt has been sent to the merchant.</p>
                  {result.redirect_url && (
                    <a className="btn-primary mt-4" href={result.redirect_url}>Return to Udaan Airlines</a>
                  )}
                </Notice>
              ) : session.status !== 'PENDING' ? (
                <Notice tone={session.status === 'COMPLETED' ? 'green' : 'red'} title={`This payment is ${session.status.toLowerCase()}`}>
                  {session.status === 'COMPLETED'
                    ? `Paid with ${session.card?.brand} •••• ${session.card?.last4}.`
                    : 'The payment window has closed. Return to the airline to get a new payment link.'}
                  {session.cancel_url && <a className="btn-secondary mt-4" href={session.cancel_url}>Back to Udaan Airlines</a>}
                </Notice>
              ) : (
                <form onSubmit={submit} className="space-y-4">
                  <h1 className="text-lg font-semibold">Pay with card</h1>
                  <div>
                    <label className="label" htmlFor="cc-number">Card number</label>
                    <div className="relative">
                      <input id="cc-number" className="input pr-28 font-mono tracking-wider" inputMode="numeric" autoComplete="cc-number"
                        placeholder="1234 1234 1234 1234" required value={groupDigits(digits)}
                        onChange={(e) => setCard({ ...card, number: e.target.value.replace(/\D/g, '').slice(0, 19) })} />
                      {brand && <span className="absolute right-3 top-2 text-xs font-semibold text-blue-700">{brand}</span>}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="label" htmlFor="cc-exp">Expiry (MM/YY)</label>
                      <input id="cc-exp" className="input font-mono" inputMode="numeric" autoComplete="cc-exp" placeholder="MM/YY"
                        required value={card.expiry} onChange={(e) => setExpiry(e.target.value)} />
                    </div>
                    <div>
                      <label className="label" htmlFor="cc-cvv">Security code</label>
                      <input id="cc-cvv" className="input font-mono" inputMode="numeric" autoComplete="cc-csc" placeholder={'•'.repeat(cvvLength)}
                        required maxLength={cvvLength} value={card.cvv}
                        onChange={(e) => setCard({ ...card, cvv: e.target.value.replace(/\D/g, '').slice(0, cvvLength) })} />
                    </div>
                  </div>
                  <div>
                    <label className="label" htmlFor="cc-name">Name on card</label>
                    <input id="cc-name" className="input uppercase" autoComplete="cc-name" required value={card.name}
                      onChange={(e) => setCard({ ...card, name: e.target.value })} />
                  </div>
                  {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
                  <button className="btn-primary w-full py-3 text-base" disabled={processing}>
                    {processing ? 'Processing…' : `Pay ${money(session.amount, session.currency)}`}
                  </button>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>Card details are not stored — only the brand and last 4 digits.</span>
                    {session.cancel_url && <a className="underline" href={session.cancel_url}>Cancel</a>}
                  </div>

                  <div className="rounded-md border border-dashed border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
                    <button type="button" className="font-semibold underline" onClick={() => setShowCards(!showCards)}>
                      Sandbox: {showCards ? 'hide' : 'show'} test cards
                    </button>
                    {showCards && (
                      <ul className="mt-2 grid gap-1 sm:grid-cols-2">
                        {TEST_CARDS.map(([name, number]) => (
                          <li key={number}>
                            <button type="button" className="text-left hover:underline"
                              onClick={() => setCard({ ...card, number: number.replace(/\s/g, '') })}>
                              {name}: <span className="font-mono">{number}</span>
                            </button>
                          </li>
                        ))}
                        <li className="sm:col-span-2">Use any future expiry, and a CVV of 4 digits for Amex or 3 for other cards. Any other number is declined.</li>
                      </ul>
                    )}
                  </div>
                </form>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function Countdown({ expiresAt }) {
  const { left, label } = useCountdown(expiresAt)
  return (
    <p className={`rounded-md px-3 py-2 text-sm ${left < 300 ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-800'}`}>
      {left ? <>Seats held for <b className="font-mono">{label}</b></> : 'This payment window has expired.'}
    </p>
  )
}

function Notice({ tone, title, children }) {
  const style = tone === 'green' ? 'border-green-200 bg-green-50 text-green-900' : 'border-red-200 bg-red-50 text-red-900'
  return (
    <div className={`rounded-lg border p-5 ${style}`}>
      <p className="text-lg font-semibold">{tone === 'green' ? '✅ ' : '⚠️ '}{title}</p>
      <div className="mt-2 text-sm">{children}</div>
    </div>
  )
}
