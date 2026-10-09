import { Navigate, Route, Routes } from 'react-router-dom'
import AdminRoute from './AdminRoute'
import GuestRoute from './GuestRoute'
import ProtectedRoute from './ProtectedRoute'
import AdminLayout from '../layouts/AdminLayout'
import UserLayout from '../layouts/UserLayout'
import LoginPage from '../pages/auth/LoginPage'
import RegisterPage from '../pages/auth/RegisterPage'
import DashboardPage from '../pages/user/DashboardPage'
import VoicesPage from '../pages/user/VoicesPage'
import GeneratePage from '../pages/user/GeneratePage'
import HistoryPage from '../pages/user/HistoryPage'
import ProfilePage from '../pages/user/ProfilePage'
import AdminDashboardPage from '../pages/admin/AdminDashboardPage'
import AdminUsersPage from '../pages/admin/AdminUsersPage'
import AdminVoicesPage from '../pages/admin/AdminVoicesPage'
import AdminGenerationsPage from '../pages/admin/AdminGenerationsPage'
import AdminUsagePage from '../pages/admin/AdminUsagePage'
import AdminReportsPage from '../pages/admin/AdminReportsPage'

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
                    <Route element={<AdminLayout />}>
                        <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
                        <Route path="/admin/users" element={<AdminUsersPage />} />
                        <Route path="/admin/voices" element={<AdminVoicesPage />} />
                        <Route path="/admin/generations" element={<AdminGenerationsPage />} />
                        <Route path="/admin/usage" element={<AdminUsagePage />} />
                        <Route path="/admin/reports" element={<AdminReportsPage />} />
                    </Route>
                </Route>
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
    )
}