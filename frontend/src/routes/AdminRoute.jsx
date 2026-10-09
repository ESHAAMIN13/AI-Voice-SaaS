import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// Only for ADMIN role. This hides pages only; the backend enforces the real rule.
export default function AdminRoute() {
    const { isAdmin } = useAuth()
    if (!isAdmin) {
        return <Navigate to="/dashboard" replace />
    }
    return <Outlet />
}