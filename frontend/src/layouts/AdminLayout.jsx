import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import AdminSidebar from '../components/admin/AdminSidebar'
import Topbar from '../components/layout/Topbar'

export default function AdminLayout() {
    const [menuOpen, setMenuOpen] = useState(false)

    return (
        <div className="flex min-h-screen bg-slate-50">
            <AdminSidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
            <div className="flex min-w-0 flex-1 flex-col">
                <Topbar onMenu={() => setMenuOpen(true)} />
                <main className="flex-1 p-4 md:p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}