import { NavLink } from 'react-router-dom'
import { History, LayoutDashboard, Mic, Sparkles, User, X } from 'lucide-react'

const LINKS = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/voices', label: 'Voices', icon: Mic },
    { to: '/generate', label: 'Generate', icon: Sparkles },
    { to: '/history', label: 'History', icon: History },
    { to: '/profile', label: 'Profile', icon: User },
]

export default function Sidebar({ open, onClose }) {
    return (
        <>
            {/* dark overlay behind the sidebar on mobile */}
            {open && (
                <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} />
            )}

            <aside
                className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform md:static md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'
                    }`}
            >
                <div className="flex h-16 items-center justify-between px-4">
                    <div className="flex items-center gap-2 font-semibold text-slate-900">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                            <Mic size={16} />
                        </span>
                        AI Voice Studio
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
                                    ? 'bg-indigo-50 text-indigo-700'
                                    : 'text-slate-600 hover:bg-slate-100'
                                }`
                            }
                        >
                            <Icon size={18} />
                            {label}
                        </NavLink>
                    ))}
                </nav>
            </aside>
        </>
    )
}