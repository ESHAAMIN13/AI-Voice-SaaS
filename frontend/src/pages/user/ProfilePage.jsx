import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import api from '../../services/api'
import { getErrorMessage } from '../../utils/apiError'

const LANGUAGES = [
    { value: 'en', label: 'English' },
    { value: 'hi', label: 'Hindi' },
    { value: 'ur', label: 'Urdu' },
]

export default function ProfilePage() {
    const { user, setUser } = useAuth()
    const [fullName, setFullName] = useState(user.full_name || '')
    const [language, setLanguage] = useState(user.preferred_language || 'en')
    const [message, setMessage] = useState('')
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)

    async function handleSubmit(e) {
        e.preventDefault()
        setMessage('')
        setError('')
        setSaving(true)
        try {
            const res = await api.put('/profile/', {
                full_name: fullName,
                preferred_language: language,
            })
            setUser(res.data.data)
            setMessage('Profile saved.')
        } catch (err) {
            setError(getErrorMessage(err))
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="max-w-md">
            <h1 className="text-xl font-semibold text-slate-900">Profile</h1>

            <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4 rounded-2xl bg-white p-6 shadow">
                {message && <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}
                {error && (
                    <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                        {error}
                    </p>
                )}

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Email
                    <input
                        value={user.email}
                        disabled
                        className="rounded-lg border border-slate-200 bg-slate-100 p-2 text-slate-500"
                    />
                </label>

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Full name
                    <input
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        maxLength={150}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    />
                </label>

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Preferred language
                    <select
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    >
                        {LANGUAGES.map((l) => (
                            <option key={l.value} value={l.value}>
                                {l.label}
                            </option>
                        ))}
                    </select>
                </label>

                <button
                    type="submit"
                    disabled={saving}
                    className="rounded-lg bg-indigo-600 p-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                    {saving ? 'Saving...' : 'Save'}
                </button>
            </form>
        </div>
    )
}