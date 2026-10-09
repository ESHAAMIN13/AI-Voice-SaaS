import { useAuth } from '../../hooks/useAuth'

// PLACEHOLDER: replaced by the real admin dashboard in Phase 16
export default function AdminDashboardPage() {
    const { user, logout } = useAuth()
    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 p-4">
            <h1 className="text-2xl font-semibold text-slate-900">Admin area</h1>
            <p className="text-sm text-slate-600">Logged in as {user.email}</p>
            <button
                onClick={logout}
                className="rounded-lg bg-slate-800 px-4 py-2 text-white hover:bg-slate-900"
            >
                Log out
            </button>
        </div>
    )
}