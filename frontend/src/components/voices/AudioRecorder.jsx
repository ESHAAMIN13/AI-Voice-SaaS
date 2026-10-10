import { Mic, RotateCcw, Square } from 'lucide-react'
import { MAX_SECONDS, MIN_SECONDS, useAudioRecorder } from '../../hooks/useAudioRecorder'

function formatTime(total) {
    const m = String(Math.floor(total / 60)).padStart(2, '0')
    const s = String(total % 60).padStart(2, '0')
    return `${m}:${s}`
}

export default function AudioRecorder({ onUse }) {
    const { status, seconds, recording, error, start, stop, reset } = useAudioRecorder()
    const tooShort = recording ? recording.seconds < MIN_SECONDS : false

    return (
        <div className="flex max-w-lg flex-col gap-3 rounded-2xl bg-white p-4 shadow">
            <h2 className="text-base font-semibold text-slate-900">Try recorder</h2>
            <p className="text-sm text-slate-500">
                Record {MIN_SECONDS} to {MAX_SECONDS} seconds of clear speech. The recording stays in
                your browser until upload is added.
            </p>

            {error && (
                <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                    {error}
                </p>
            )}

            {status === 'idle' && (
                <button
                    onClick={start}
                    className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 p-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                    <Mic size={16} />
                    Record
                </button>
            )}

            {status === 'recording' && (
                <div className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2 text-sm font-medium text-red-600">
                        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
                        Recording {formatTime(seconds)} / {formatTime(MAX_SECONDS)}
                    </span>
                    <button
                        onClick={stop}
                        className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-sm text-white hover:bg-slate-900"
                    >
                        <Square size={14} />
                        Stop
                    </button>
                </div>
            )}

            {status === 'recorded' && recording && (
                <div className="flex flex-col gap-3">
                    <audio controls src={recording.url} className="w-full" />
                    <p className="text-sm text-slate-600">Length: {formatTime(recording.seconds)}</p>
                    {tooShort && (
                        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
                            Too short. Please record at least {MIN_SECONDS} seconds.
                        </p>
                    )}
                    <div className="flex gap-2">
                        <button
                            onClick={reset}
                            className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
                        >
                            <RotateCcw size={14} />
                            Record again
                        </button>
                        <button
                            onClick={() => onUse?.(recording)}
                            disabled={tooShort}
                            className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                        >
                            Use this recording
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}