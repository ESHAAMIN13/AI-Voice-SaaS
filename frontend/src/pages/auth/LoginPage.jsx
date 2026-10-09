import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Mic } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { getErrorMessage } from '../../utils/apiError'

export default function LoginPage() {
    const { login } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [submitting, setSubmitting] = useState(false)

    async function handleSubmit(e) {
        e.preventDefault()
        setError('')
        setSubmitting(true)
        try {
            const user = await login({ email, password })
            const fallback = user.role === 'ADMIN' ? '/admin/dashboard' : '/dashboard'
            navigate(location.state?.from || fallback, { replace: true })
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
                    <h1 className="text-xl font-semibold text-slate-900">Log in</h1>
                </div>

                {error && (
                    <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                        {error}
                    </p>
                )}

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
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="rounded-lg border border-slate-300 p-2 outline-none focus:border-indigo-500"
                    />
                </label>

                <button
                    type="submit"
                    disabled={submitting}
                    className="rounded-lg bg-indigo-600 p-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                    {submitting ? 'Logging in...' : 'Log in'}
                </button>

                <p className="text-center text-sm text-slate-600">
                    No account?{' '}
                    <Link to="/register" className="text-indigo-600 hover:underline">
                        Register
                    </Link>
                </p>
            </form>
        </div>
    )
}