import { useEffect, useState } from 'react'
import { Mic } from 'lucide-react'
import { getHealth } from './services/healthService'

const STATUS_STYLES = {
  checking: { dot: 'bg-slate-400', text: 'Checking backend...' },
  online: { dot: 'bg-green-500', text: 'Backend: Online' },
  offline: { dot: 'bg-red-500', text: 'Backend: Offline' },
}

export default function App() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((result) => {
        if (!cancelled) setStatus(result.success ? 'online' : 'offline')
      })
      .catch(() => {
        if (!cancelled) setStatus('offline')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const { dot, text } = STATUS_STYLES[status]

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="flex w-full max-w-md flex-col items-center gap-4 rounded-2xl bg-white p-8 shadow-lg">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
          <Mic size={28} />
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">AI Voice Studio</h1>
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
          <span>{text}</span>
        </div>
      </div>
    </div>
  )
}