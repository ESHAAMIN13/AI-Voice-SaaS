import { Navigate, Route, Routes } from 'react-router-dom'
import AdminRoute from './AdminRoute'
import GuestRoute from './GuestRoute'
import ProtectedRoute from './ProtectedRoute'
import UserLayout from '../layouts/UserLayout'
import LoginPage from '../pages/auth/LoginPage'
import RegisterPage from '../pages/auth/RegisterPage'
import DashboardPage from '../pages/user/DashboardPage'
import VoicesPage from '../pages/user/VoicesPage'
import GeneratePage from '../pages/user/GeneratePage'
import HistoryPage from '../pages/user/HistoryPage'
import ProfilePage from '../pages/user/ProfilePage'
import AdminDashboardPage from '../pages/admin/AdminDashboardPage'

export default function AppRoutes() {
    return (
        <Routes>
            <Route element={<GuestRoute />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
            </Route>

            <Route element={<ProtectedRoute />}>
                <Route element={<UserLayout />}>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/voices" element={<VoicesPage />} />
                    <Route path="/generate" element={<GeneratePage />} />
                    <Route path="/history" element={<HistoryPage />} />
                    <Route path="/profile" element={<ProfilePage />} />
                </Route>

                <Route element={<AdminRoute />}>
                    <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
                </Route>
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
    )
}