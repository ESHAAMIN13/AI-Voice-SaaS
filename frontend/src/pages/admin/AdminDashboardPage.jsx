import { AudioLines, CheckCircle2, Mic, UserCheck, Users, XCircle } from 'lucide-react'

// All values are 0 until the admin analytics API exists (Phase 39).
// No fake numbers are shown.
const STATS = [
    { label: 'Total users', value: 0, icon: Users },
    { label: 'Active users', value: 0, icon: UserCheck },
    { label: 'Voice profiles', value: 0, icon: Mic },
    { label: 'Total generations', value: 0, icon: AudioLines },
    { label: 'Successful', value: 0, icon: CheckCircle2 },
    { label: 'Failed', value: 0, icon: XCircle },
]

export default function AdminDashboardPage() {
    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="text-xl font-semibold text-slate-900">Admin dashboard</h1>
                <p className="text-sm text-slate-500">Overview of the whole platform.</p>
            </div>

            <div className="flex flex-wrap gap-4">
                {STATS.map(({ label, value, icon: Icon }) => (
                    <div
                        key={label}
                        className="flex min-w-[200px] flex-1 items-center gap-3 rounded-2xl bg-white p-4 shadow"
                    >
                        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-amber-600">
                            <Icon size={20} />
                        </span>
                        <div>
                            <p className="text-sm text-slate-500">{label}</p>
                            <p className="text-xl font-semibold text-slate-900">{value}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}