import { Mic } from 'lucide-react'

export default function App() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="flex w-full max-w-md flex-col items-center gap-4 rounded-2xl bg-white p-8 shadow-lg">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
          <Mic size={28} />
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">AI Voice Studio</h1>
        <p className="text-center text-sm text-slate-500">
          Frontend setup is working. Tailwind and Lucide icons are ready.
        </p>
      </div>
    </div>
  )
}