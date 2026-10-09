import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// For /login and /register: a logged-in user is sent to their dashboard.
export default function GuestRoute() {
    const { user, loading, isAdmin } = useAuth()
    if (loading) {
        return <p className="p-6 text-center text-slate-500">Loading...</p>
    }
    if (user) {
        return <Navigate to={isAdmin ? '/admin/dashboard' : '/dashboard'} replace />
    }
    return <Outlet />
}