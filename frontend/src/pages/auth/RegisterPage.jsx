import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mic } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { getErrorMessage } from '../../utils/apiError'

export default function RegisterPage() {
    const { register } = useAuth()
    const navigate = useNavigate()
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirm, setConfirm] = useState('')
    const [error, setError] = useState('')
    const [submitting, setSubmitting] = useState(false)

    async function handleSubmit(e) {
        e.preventDefault()
        setError('')
        if (password !== confirm) {
            setError('Passwords do not match.')
            return
        }
        setSubmitting(true)
        try {
            await register({ fullName, email, password })
            navigate('/dashboard', { replace: true })
        } catch (err) {
            setError(getErrorMessage(err))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
            <form
                onSubmit={handleSubmit}
                className="flex w-full max-w-sm flex-col gap-4 rounded-2xl bg-white p-8 shadow-lg"
            >
                <div className="flex flex-col items-center gap-2">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                        <Mic size={24} />
                    </div>
                    <h1 className="text-xl font-semibold text-slate-900">Create account</h1>
                </div>

                {error && (
                    <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                        {error}
                    </p>
                )}

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Full name
                    <input
                        type="text"
                        autoComplete="name"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    />
                </label>

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Email
                    <input
                        type="email"
                        required
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    />
                </label>

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Password
                    <input
                        type="password"
                        required
                        autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    />
                </label>

                <label className="flex flex-col gap-1 text-sm text-slate-700">
                    Confirm password
                    <input
                        type="password"
                        required
                        autoComplete="new-password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    />
                </label>

                <button
                    type="submit"
                    disabled={submitting}
                    className="rounded-lg bg-indigo-600 p-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                    {submitting ? 'Creating...' : 'Register'}
                </button>

                <p className="text-center text-sm text-slate-600">
                    Already have an account?{' '}
                    <Link to="/login" className="text-indigo-600 hover:underline">
                        Log in
                    </Link>
                </p>
            </form>
        </div>
    )
}