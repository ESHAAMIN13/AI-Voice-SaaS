import { useEffect, useState } from 'react'
import { LogOut, Menu } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { getHealth } from '../../services/healthService'

const STATUS_STYLES = {
    checking: { dot: 'bg-slate-400', text: 'Checking...' },
    online: { dot: 'bg-green-500', text: 'Online' },
    offline: { dot: 'bg-red-500', text: 'Offline' },
}

export default function Topbar({ onMenu }) {
    const { user, logout } = useAuth()
    const [status, setStatus] = useState('checking')
    const [loggingOut, setLoggingOut] = useState(false)

    useEffect(() => {
        let cancelled = false
        getHealth()
            .then((r) => !cancelled && setStatus(r.success ? 'online' : 'offline'))
            .catch(() => !cancelled && setStatus('offline'))
        return () => {
            cancelled = true
        }
    }, [])

    async function handleLogout() {
        setLoggingOut(true) // ignore extra clicks
        await logout()
    }

    const { dot, text } = STATUS_STYLES[status]

    return (
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4">
            <button onClick={onMenu} className="text-slate-600 md:hidden" aria-label="Open menu">
                <Menu size={22} />
            </button>

            <div className="flex items-center gap-2 text-sm text-slate-600">
                <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
                <span>Backend: {text}</span>
            </div>

            <div className="flex items-center gap-3">
                <span className="hidden text-sm text-slate-600 sm:inline">{user?.email}</span>
                <button
                    onClick={handleLogout}
                    disabled={loggingOut}
                    className="flex items-center gap-1 rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-900 disabled:opacity-60"
                >
                    <LogOut size={16} />
                    Log out
                </button>
            </div>
        </header>
    )
}