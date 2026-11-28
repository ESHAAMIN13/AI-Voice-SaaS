import { useCallback, useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { deleteGeneration, fetchHistory } from '../../services/generationService'
import { getErrorMessage } from '../../utils/apiError'

const STATUS = {
  PENDING: { label: 'Waiting', style: 'bg-slate-100 text-slate-700' },
  PROCESSING: { label: 'Creating', style: 'bg-blue-100 text-blue-700' },
  COMPLETED: { label: 'Ready', style: 'bg-green-100 text-green-700' },
  FAILED: { label: 'Failed', style: 'bg-red-100 text-red-700' },
}
const FILTERS = [
  { value: '', label: 'All' },
  { value: 'COMPLETED', label: 'Ready' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'PENDING', label: 'Waiting' },
  { value: 'PROCESSING', label: 'Creating' },
]

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

function formatDuration(seconds) {
  return seconds == null ? '' : ` - ${seconds.toFixed(1)} s`
}

export default function HistoryPage() {
  const [data, setData] = useState({ items: [], page: 1, pages: 1, count: 0 })
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetchHistory({ page, status: filter })
      .then((result) => {
        if (cancelled) return
        setData(result)
        setError('')
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, filter, reload])

  const changeFilter = useCallback((value) => {
    setLoading(true)
    setFilter(value)
    setPage(1)
  }, [])

  async function handleDelete(item) {
    if (!window.confirm('Delete this generation and its audio? This cannot be undone.')) return
    setDeletingId(item.id)
    try {
      await deleteGeneration(item.id)
      setError('')
      // Go back one page if the last item of the last page was deleted
      if (data.items.length === 1 && page > 1) setPage(page - 1)
      else setReload((n) => n + 1)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-900">History</h1>
        <select
          value={filter}
          onChange={(e) => changeFilter(e.target.value)}
          className="rounded-lg border border-slate-300 p-2 text-sm"
          aria-label="Filter by status"
        >
          {FILTERS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>

      <p className="text-sm text-slate-500">
        Play and download are coming in a later update. Your audio is already saved.
      </p>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : data.items.length === 0 ? (
        <p className="text-sm text-slate-500">
          {filter ? 'Nothing matches this filter.' : 'No generations yet.'}
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {data.items.map((g) => {
            const s = STATUS[g.status] || STATUS.PENDING
            return (
              <div key={g.id} className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow">
                <div className="min-w-0">
                  <p className="truncate text-sm text-slate-900">{g.text_preview}</p>
                  <p className="text-xs text-slate-500">
                    {g.voice_name} - {g.language} - {formatDate(g.created_at)}
                    {formatDuration(g.duration_sec)}
                  </p>
                  {g.status === 'FAILED' && g.error_message && (
                    <p className="text-xs text-red-600">{g.error_message}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${s.style}`}>
                    {s.label}
                  </span>
                  {(g.status === 'COMPLETED' || g.status === 'FAILED') && (
                    <button
                      onClick={() => handleDelete(g)}
                      disabled={deletingId === g.id}
                      aria-label="Delete generation"
                      className="text-slate-400 hover:text-red-600 disabled:opacity-50"
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <button
            onClick={() => {
              setLoading(true)
              setPage(page - 1)
            }}
            disabled={page <= 1}
            className="rounded-lg border border-slate-300 px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <span>Page {data.page} of {data.pages} ({data.count} total)</span>
          <button
            onClick={() => {
              setLoading(true)
              setPage(page + 1)
            }}
            disabled={page >= data.pages}
            className="rounded-lg border border-slate-300 px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
