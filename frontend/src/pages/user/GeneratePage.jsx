import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { createGeneration, listGenerations } from '../../services/generationService'
import { listVoices } from '../../services/voiceService'
import { getErrorMessage } from '../../utils/apiError'

const MAX_CHARS = 200 // same as the server (TTS_MAX_TEXT_CHARS)
const LANGUAGES = [
    { value: 'en', label: 'English' },
    { value: 'hi', label: 'Hindi' },
]

export default function GeneratePage() {
    const [voices, setVoices] = useState([])
    const [items, setItems] = useState([])
    const [loading, setLoading] = useState(true)
    const [voiceId, setVoiceId] = useState('')
    const [language, setLanguage] = useState('en')
    const [text, setText] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [message, setMessage] = useState('')
    const [error, setError] = useState('')

    useEffect(() => {
        let cancelled = false
        Promise.all([listVoices(), listGenerations()])
            .then(([v, g]) => {
                if (cancelled) return
                setVoices(v.filter((x) => x.status === 'APPROVED'))
                setItems(g)
            })
            .catch((err) => !cancelled && setError(getErrorMessage(err)))
            .finally(() => !cancelled && setLoading(false))
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
            setMessage('Request saved with status PENDING. Audio creation is not switched on yet.')
            setText('')
            setItems(await listGenerations())
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
                    <option value="">{loading ? 'Loading...' : 'Choose a voice'}</option>
                    {voices.map((v) => (
                        <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                </select>
                {!loading && voices.length === 0 && (
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
                    {submitting ? 'Saving...' : 'Generate'}
                </button>
            </form>

            <section className="flex flex-col gap-3">
                <h2 className="text-base font-semibold text-slate-900">Your requests</h2>
                {items.length === 0 ? (
                    <p className="text-sm text-slate-500">Nothing yet.</p>
                ) : (
                    items.map((g) => (
                        <div key={g.id} className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow">
                            <div className="min-w-0">
                                <p className="truncate text-sm text-slate-900">{g.text_preview}</p>
                                <p className="text-xs text-slate-500">{g.voice_name} · {g.language}</p>
                            </div>
                            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                                {g.status}
                            </span>
                        </div>
                    ))
                )}
            </section>
        </div>
    )
}