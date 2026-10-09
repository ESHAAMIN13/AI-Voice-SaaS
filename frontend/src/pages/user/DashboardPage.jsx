import { Link } from 'react-router-dom'
import { AudioLines, Coins, Mic, Sparkles } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

// Numbers are 0 until the voices/generations APIs exist (Phase 17 and 26).
// Then only the STATS and RECENT values below need to come from the API.
const STATS = {
    voices: 0,
    generations: 0,
    credits: null, // null = credits system not built yet (Phase 35)
}

function StatCard({ icon: Icon, label, value }) {
    return (
        <div className="flex flex-1 items-center gap-3 rounded-2xl bg-white p-4 shadow">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
                <Icon size={20} />
            </span>
            <div>
                <p className="text-sm text-slate-500">{label}</p>
                <p className="text-xl font-semibold text-slate-900">{value}</p>
            </div>
        </div>
    )
}

export default function DashboardPage() {
    const { user } = useAuth()
    const name = user.full_name || user.email
    const recent = [] // filled from the API in Phase 31

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-xl font-semibold text-slate-900">Hello, {name}</h1>
                    <p className="text-sm text-slate-500">Here is a summary of your account.</p>
                </div>
                <Link
                    to="/generate"
                    className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                    <Sparkles size={16} />
                    Quick Generate
                </Link>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row">
                <StatCard icon={Mic} label="Voice profiles" value={STATS.voices} />
                <StatCard icon={AudioLines} label="Generated audio" value={STATS.generations} />
                <StatCard
                    icon={Coins}
                    label="Credits"
                    value={STATS.credits === null ? 'Not set up yet' : STATS.credits}
                />
            </div>

            <section className="rounded-2xl bg-white p-4 shadow">
                <h2 className="text-base font-semibold text-slate-900">Recent generations</h2>
                {recent.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-500">
                        Nothing yet. Create a voice profile, then generate your first audio.
                    </p>
                ) : null}
            </section>
        </div>
    )
}