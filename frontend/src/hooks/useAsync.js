import { useCallback, useState } from 'react'

// Tracks loading / error state for an async action.
export default function useAsync() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = useCallback(async (fn) => {
    setLoading(true)
    setError('')
    try {
      return await fn()
    } catch (err) {
      setError(err.message || 'Something went wrong.')
      return undefined
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, setError, run }
}
