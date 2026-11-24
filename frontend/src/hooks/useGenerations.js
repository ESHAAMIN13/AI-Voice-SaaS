import { useCallback, useEffect, useRef, useState } from 'react'
import { listGenerations } from '../services/generationService'
import { getErrorMessage } from '../utils/apiError'

const POLL_MS = 5000 // ST-2: one list call every 5 seconds
const ACTIVE = ['PENDING', 'PROCESSING']

export function useGenerations() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [connectionProblem, setConnectionProblem] = useState(false)
  const tickRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    let timer = null
    let inFlight = false
    let again = false
    let failures = 0
    let hasActive = false
    let loadedOnce = false

    function clearTimer() {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
    }

    // ST-1 and ST-3: only poll while a job is active and the tab is visible
    function schedule() {
      clearTimer()
      if (cancelled || !hasActive || document.hidden) return
      timer = setTimeout(tick, POLL_MS)
    }

    async function tick() {
      if (cancelled) return
      if (inFlight) {
        again = true // ST-2: never two calls at once; run once more afterwards
        return
      }
      inFlight = true
      try {
        const data = await listGenerations()
        if (!cancelled) {
          failures = 0
          loadedOnce = true
          hasActive = data.some((g) => ACTIVE.includes(g.status))
          setItems(data)
          setError('')
          setConnectionProblem(false)
        }
      } catch (err) {
        if (!cancelled) {
          failures += 1
          if (!loadedOnce) setError(getErrorMessage(err))
          else if (failures >= 3) setConnectionProblem(true) // ST-7
        }
      } finally {
        inFlight = false
        if (!cancelled) {
          setLoading(false)
          if (again) {
            again = false
            clearTimer()
            timer = setTimeout(tick, 0)
          } else {
            schedule()
          }
        }
      }
    }

    function onVisibility() {
      if (document.hidden) clearTimer()
      else tick() // ST-3: one call right away when the tab is back
    }

    document.addEventListener('visibilitychange', onVisibility)
    tickRef.current = tick
    timer = setTimeout(tick, 0) // first load

    return () => {
      cancelled = true
      clearTimer()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  const refresh = useCallback(() => {
    if (tickRef.current) tickRef.current()
  }, [])

  return { items, loading, error, connectionProblem, refresh }
}
