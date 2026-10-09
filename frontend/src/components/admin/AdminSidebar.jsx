import { NavLink } from 'react-router-dom'
import {
    AudioLines,
    BarChart3,
    FileText,
    LayoutDashboard,
    Mic,
    ShieldCheck,
    Users,
    X,
} from 'lucide-react'

const LINKS = [
    { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/admin/users', label: 'Users', icon: Users },
    { to: '/admin/voices', label: 'Voices', icon: Mic },
    { to: '/admin/generations', label: 'Generations', icon: AudioLines },
    { to: '/admin/usage', label: 'Usage', icon: BarChart3 },
    { to: '/admin/reports', label: 'Reports', icon: FileText },
]

export default function AdminSidebar({ open, onClose }) {
    return (
        <>
            {open && (
                <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} />
            )}

            <aside
                className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform md:static md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'
                    }`}
            >
                <div className="flex h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-2 font-semibold text-slate-900">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-amber-600">
                            <ShieldCheck size={16} />
                        </span>
                        Admin Panel
                    </div>
                    <button onClick={onClose} className="text-slate-500 md:hidden" aria-label="Close menu">
                        <X size={20} />
                    </button>
                </div>

                <nav className="flex flex-col gap-1 p-3">
                    {LINKS.map(({ to, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            onClick={onClose}
                            className={({ isActive }) =>
                                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive
                                    ? 'bg-amber-50 text-amber-700'
                                    : 'text-slate-600 hover:bg-slate-100'
                                }`
                            }
                        >
                            <Icon size={18} />
                            {label}
                        </NavLink>
                    ))}
                </nav>

                <div className="mt-auto border-t border-slate-200 p-3">
                    <NavLink
                        to="/dashboard"
                        className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
                    >
                        <LayoutDashboard size={18} />
                        User panel
                    </NavLink>
                </div>
            </aside>
        </>
    )
}