import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { createGeneration } from '../../services/generationService'
import { listVoices } from '../../services/voiceService'
import { useGenerations } from '../../hooks/useGenerations'
import { getErrorMessage } from '../../utils/apiError'

const MAX_CHARS = 200 // same as the server (TTS_MAX_TEXT_CHARS)
const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
]

// ST-4 and ST-5: honest labels
const STATUS = {
  PENDING: { badge: 'Waiting', style: 'bg-slate-100 text-slate-700', note: 'Waiting in queue.' },
  PROCESSING: {
    badge: 'Creating',
    style: 'bg-blue-100 text-blue-700',
    note: 'Creating audio. This can take a few minutes.',
  },
  COMPLETED: {
    badge: 'Ready',
    style: 'bg-green-100 text-green-700',
    note: 'Audio is ready. Listening and download come in a later update.',
  },
  FAILED: { badge: 'Failed', style: 'bg-red-100 text-red-700', note: '' },
}

export default function GeneratePage() {
  const { items, loading, error: listError, connectionProblem, refresh } = useGenerations()
  const [voices, setVoices] = useState([])
  const [voicesLoading, setVoicesLoading] = useState(true)
  const [voiceId, setVoiceId] = useState('')
  const [language, setLanguage] = useState('en')
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    listVoices()
      .then((v) => {
        if (!cancelled) setVoices(v.filter((x) => x.status === 'APPROVED'))
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setVoicesLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setMessage('')
    setError('')
    setSubmitting(true)
    try {
      await createGeneration({ voiceProfile: voiceId, language, text })
      setMessage('Request received. Waiting in queue.') // ST-6
      setText('')
      refresh() // starts polling, because the new job is PENDING
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-slate-900">Generate</h1>

      <form onSubmit={handleSubmit} className="flex max-w-lg flex-col gap-3 rounded-2xl bg-white p-4 shadow">
        {message && <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>
        )}

        <select
          required
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          className="rounded-lg border border-slate-300 p-2 text-sm"
        >
          <option value="">{voicesLoading ? 'Loading...' : 'Choose a voice'}</option>
          {voices.map((v) => (
            <option key={v.id} value={v.id}>{v.name}</option>
          ))}
        </select>
        {!voicesLoading && voices.length === 0 && (
          <p className="text-sm text-slate-500">
            You need an approved voice profile. Create one on the Voices page and upload a sample.
          </p>
        )}

        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded-lg border border-slate-300 p-2 text-sm"
        >
          {LANGUAGES.map((l) => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
          <option value="ur" disabled>Urdu (not supported yet)</option>
        </select>

        <textarea
          required
          rows={4}
          maxLength={MAX_CHARS}
          placeholder="Type the text to speak"
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-500"
        />
        <p className="text-right text-xs text-slate-500">{text.length} / {MAX_CHARS}</p>

        <button
          type="submit"
          disabled={submitting || !voiceId || !text.trim()}
          className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 p-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          <Sparkles size={16} />
          {submitting ? 'Sending...' : 'Generate'}
        </button>
      </form>

      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-slate-900">Your requests</h2>
        {connectionProblem && (
          <p className="text-sm text-amber-700">Connection problem, retrying...</p>
        )}
        {listError && (
          <p role="alert" className="text-sm text-red-700">
            {listError}{' '}
            <button type="button" onClick={refresh} className="underline">Try again</button>
          </p>
        )}
        {loading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing yet.</p>
        ) : (
          items.map((g) => {
            const s = STATUS[g.status] || STATUS.PENDING
            const note = g.status === 'FAILED' ? g.error_message : s.note
            return (
              <div key={g.id} className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow">
                <div className="min-w-0">
                  <p className="truncate text-sm text-slate-900">{g.text_preview}</p>
                  <p className="text-xs text-slate-500">{g.voice_name} - {g.language}</p>
                  {note && (
                    <p className={`text-xs ${g.status === 'FAILED' ? 'text-red-600' : 'text-slate-500'}`}>
                      {note}
                    </p>
                  )}
                </div>
                <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-medium ${s.style}`}>
                  {s.badge}
                </span>
              </div>
            )
          })
        )}
      </section>
    </div>
  )
}
