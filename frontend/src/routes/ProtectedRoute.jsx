import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// Only for logged-in users. Others are sent to /login and come back after login.
export default function ProtectedRoute() {
    const { user, loading } = useAuth()
    const location = useLocation()

    if (loading) {
        return <p className="p-6 text-center text-slate-500">Loading...</p>
    }
    if (!user) {
        return <Navigate to="/login" replace state={{ from: location.pathname }} />
    }
    return <Outlet />
}