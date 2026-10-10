import { useCallback, useEffect, useState } from 'react'
import { Mic, Trash2 } from 'lucide-react'
import { createVoice, deleteVoice, listVoices } from '../../services/voiceService'
import { getErrorMessage } from '../../utils/apiError'
import AudioRecorder from '../../components/voices/AudioRecorder'

const CONSENT_TEXT =
    "I confirm this is my own voice, or I have the speaker's permission to clone it. I will not use it to impersonate anyone."

const STATUS_STYLES = {
    PENDING: 'bg-slate-100 text-slate-700',
    PROCESSING: 'bg-blue-100 text-blue-700',
    APPROVED: 'bg-green-100 text-green-700',
    REJECTED: 'bg-red-100 text-red-700',
    FAILED: 'bg-red-100 text-red-700',
}

export default function VoicesPage() {
    const [voices, setVoices] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [consent, setConsent] = useState(false)
    const [formError, setFormError] = useState('')
    const [saving, setSaving] = useState(false)
    const [deletingId, setDeletingId] = useState(null)
    const [chosenRecording, setChosenRecording] = useState(null)


    // Used after create/delete to refresh the list
    const load = useCallback(async () => {
        try {
            setVoices(await listVoices())
            setError('')
        } catch (err) {
            setError(getErrorMessage(err))
        }
    }, [])

    // First load: setState happens only after the await, never synchronously
    useEffect(() => {
        let cancelled = false
        listVoices()
            .then((data) => {
                if (!cancelled) setVoices(data)
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
    }, [])

    async function handleCreate(e) {
        e.preventDefault()
        setFormError('')
        setSaving(true)
        try {
            await createVoice({ name, description, consent })
            setName('')
            setDescription('')
            setConsent(false)
            await load()
        } catch (err) {
            setFormError(getErrorMessage(err))
        } finally {
            setSaving(false)
        }
    }

    async function handleDelete(voice) {
        if (!window.confirm(`Delete "${voice.name}"? This cannot be undone.`)) return
        setDeletingId(voice.id)
        try {
            await deleteVoice(voice.id)
            await load()
        } catch (err) {
            setError(getErrorMessage(err))
        } finally {
            setDeletingId(null)
        }
    }

    return (
        <div className="flex flex-col gap-6">
            <h1 className="text-xl font-semibold text-slate-900">Voices</h1>

            <form onSubmit={handleCreate} className="flex max-w-lg flex-col gap-3 rounded-2xl bg-white p-4 shadow">
                <h2 className="text-base font-semibold text-slate-900">Create voice profile</h2>
                {formError && (
                    <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                        {formError}
                    </p>
                )}
                <input
                    required
                    maxLength={100}
                    placeholder="Name (e.g. My Voice)"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-500"
                />
                <textarea
                    rows={2}
                    placeholder="Description (optional)"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-indigo-500"
                />
                <label className="flex items-start gap-2 text-sm text-slate-700">
                    <input
                        type="checkbox"
                        checked={consent}
                        onChange={(e) => setConsent(e.target.checked)}
                        className="mt-1"
                    />
                    {CONSENT_TEXT}
                </label>
                <button
                    type="submit"
                    disabled={saving || !consent}
                    className="rounded-lg bg-indigo-600 p-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                    {saving ? 'Creating...' : 'Create profile'}
                </button>
            </form>
            <div className="flex flex-col gap-2">
                <AudioRecorder onUse={setChosenRecording} />
                {chosenRecording && (
                    <p className="max-w-lg rounded-lg bg-green-50 p-3 text-sm text-green-700">
                        Recording ready ({chosenRecording.seconds}s, {chosenRecording.mimeType}). Uploading it to a
                        voice profile comes in Phase 19.
                    </p>
                )}
            </div>
            {error && (
                <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                    {error}
                </p>
            )}

            <section className="flex flex-col gap-3">
                <h2 className="text-base font-semibold text-slate-900">Your voice profiles</h2>
                {loading ? (
                    <p className="text-sm text-slate-500">Loading...</p>
                ) : voices.length === 0 ? (
                    <p className="text-sm text-slate-500">No voice profiles yet. Create your first one above.</p>
                ) : (
                    voices.map((v) => (
                        <div key={v.id} className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow">
                            <div className="flex min-w-0 items-center gap-3">
                                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                                    <Mic size={20} />
                                </span>
                                <div className="min-w-0">
                                    <p className="truncate font-medium text-slate-900">{v.name}</p>
                                    {v.description && <p className="truncate text-sm text-slate-500">{v.description}</p>}
                                </div>
                            </div>
                            <div className="flex shrink-0 items-center gap-3">
                                <span className={`rounded-full px-2 py-1 text-xs font-medium ${STATUS_STYLES[v.status]}`}>
                                    {v.status}
                                </span>
                                <button
                                    onClick={() => handleDelete(v)}
                                    disabled={deletingId === v.id}
                                    aria-label={`Delete ${v.name}`}
                                    className="text-slate-400 hover:text-red-600 disabled:opacity-50"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </section>
        </div>
    )
}