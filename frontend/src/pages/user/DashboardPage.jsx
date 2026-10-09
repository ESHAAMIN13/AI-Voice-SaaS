import { useAuth } from '../../hooks/useAuth'

// PLACEHOLDER: replaced by the real dashboard in Phase 15
export default function DashboardPage() {
    const { user, logout } = useAuth()
    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 p-4">
            <h1 className="text-2xl font-semibold text-slate-900">
                Welcome, {user.full_name || user.email}
            </h1>
            <p className="text-sm text-slate-600">Role: {user.role}</p>
            <button
                onClick={logout}
                className="rounded-lg bg-slate-800 px-4 py-2 text-white hover:bg-slate-900"
            >
                Log out
            </button>
        </div>
    )
}