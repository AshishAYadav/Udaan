import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { policyService } from '../services/api'

const STORAGE_KEY = 'udaan.currency'
const REGION_CURRENCY = {
  US: 'USD', IN: 'INR', AE: 'AED', GB: 'GBP', FR: 'EUR', DE: 'EUR', IE: 'EUR', IT: 'EUR', ES: 'EUR', NL: 'EUR',
  SG: 'SGD', JP: 'JPY', AU: 'AUD', QA: 'QAR',
}
const TIMEZONE_CURRENCY = {
  'Asia/Kolkata': 'INR', 'Asia/Calcutta': 'INR', 'Asia/Dubai': 'AED', 'Europe/London': 'GBP', 'Asia/Singapore': 'SGD',
  'Asia/Tokyo': 'JPY', 'Australia/Sydney': 'AUD', 'Asia/Qatar': 'QAR',
}

// Best guess of the visitor's currency from the browser region, then the timezone.
function detectCurrency() {
  const region = (navigator.language || '').split('-')[1]?.toUpperCase()
  if (region && REGION_CURRENCY[region]) return REGION_CURRENCY[region]
  return TIMEZONE_CURRENCY[Intl.DateTimeFormat().resolvedOptions().timeZone] || 'USD'
}

function stored() {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

const CurrencyContext = createContext(null)

export function CurrencyProvider({ children }) {
  const [currency, setCurrencyState] = useState(() => stored() || detectCurrency())
  const [currencies, setCurrencies] = useState([{ code: 'USD', name: 'US Dollar', rate: 1, decimals: 2 }])

  useEffect(() => {
    policyService.currencies().then(setCurrencies).catch(() => {})
  }, [])

  const value = useMemo(() => {
    const rate = currencies.find((c) => c.code === currency)?.rate ?? 1
    const code = currencies.some((c) => c.code === currency) ? currency : 'USD'
    return {
      currency: code,
      currencies,
      setCurrency: (next) => {
        try { localStorage.setItem(STORAGE_KEY, next) } catch { /* private mode */ }
        setCurrencyState(next)
      },
      // Formats a base-currency (USD) amount in the visitor's currency.
      price: (usd) => new Intl.NumberFormat(undefined, { style: 'currency', currency: code }).format(usd * rate),
    }
  }, [currency, currencies])

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>
}

export const useCurrency = () => useContext(CurrencyContext)
