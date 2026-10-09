import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import Topbar from '../components/layout/Topbar'

export default function UserLayout() {
    const [menuOpen, setMenuOpen] = useState(false)

    return (
        <div className="flex min-h-screen bg-slate-50">
            <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
            <div className="flex min-w-0 flex-1 flex-col">
                <Topbar onMenu={() => setMenuOpen(true)} />
                <main className="flex-1 p-4 md:p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}