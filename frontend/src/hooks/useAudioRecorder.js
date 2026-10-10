import { useCallback, useEffect, useRef, useState } from 'react'

export const MIN_SECONDS = 10 // R-3
export const MAX_SECONDS = 60 // R-2

// R-4: use what the browser supports; no forced conversion (FFmpeg does that in Phase 21)
const MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']

function pickMimeType() {
    if (typeof MediaRecorder === 'undefined') return ''
    return MIME_CANDIDATES.find((t) => MediaRecorder.isTypeSupported(t)) || ''
}

// R-5: safe, readable messages
function micErrorMessage(err) {
    switch (err?.name) {
        case 'NotAllowedError':
        case 'SecurityError':
            return 'Microphone permission was denied. Allow it in your browser settings and try again.'
        case 'NotFoundError':
        case 'OverconstrainedError':
            return 'No microphone was found on this device.'
        case 'NotReadableError':
            return 'The microphone is being used by another app. Close it and try again.'
        default:
            return 'Could not start recording. Please try again.'
    }
}

export function useAudioRecorder() {
    const [status, setStatus] = useState('idle') // idle | recording | recorded
    const [seconds, setSeconds] = useState(0)
    const [recording, setRecording] = useState(null) // { blob, url, seconds, mimeType }
    const [error, setError] = useState('')

    const recorderRef = useRef(null)
    const streamRef = useRef(null)
    const timerRef = useRef(null)
    const startedAtRef = useRef(0)
    const urlRef = useRef(null)

    // Turns the mic off (the browser's mic light goes out) and stops the timer
    const stopStream = useCallback(() => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
    }, [])

    // R-7: free the preview URL so memory is not leaked
    const revokeUrl = useCallback(() => {
        if (urlRef.current) {
            URL.revokeObjectURL(urlRef.current)
            urlRef.current = null
        }
    }, [])

    // Release everything. Used on reset and when the page is left.
    const release = useCallback(() => {
        const rec = recorderRef.current
        if (rec) {
            rec.onstop = null
            rec.ondataavailable = null
            if (rec.state !== 'inactive') rec.stop()
            recorderRef.current = null
        }
        stopStream()
        revokeUrl()
    }, [stopStream, revokeUrl])

    useEffect(() => release, [release])

    const stop = useCallback(() => {
        const rec = recorderRef.current
        if (rec && rec.state !== 'inactive') rec.stop()
    }, [])

    const start = useCallback(async () => {
        setError('')
        if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
            setError('Your browser does not support audio recording. Try a recent Chrome, Edge, Firefox or Safari.')
            return
        }

        release()
        setRecording(null)

        let stream
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        } catch (err) {
            setError(micErrorMessage(err))
            return
        }
        streamRef.current = stream

        const mimeType = pickMimeType()
        let rec
        try {
            rec = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
        } catch {
            stopStream()
            setError('Could not start recording in this browser.')
            return
        }

        const chunks = []
        rec.ondataavailable = (e) => {
            if (e.data.size > 0) chunks.push(e.data)
        }
        rec.onstop = () => {
            const elapsed = Math.min(
                MAX_SECONDS,
                Math.round((Date.now() - startedAtRef.current) / 1000),
            )
            const type = rec.mimeType || mimeType || 'audio/webm'
            const blob = new Blob(chunks, { type })
            stopStream()
            recorderRef.current = null
            if (blob.size === 0) {
                setError('Nothing was recorded. Please try again.')
                setStatus('idle')
                return
            }
            const url = URL.createObjectURL(blob)
            urlRef.current = url
            setRecording({ blob, url, seconds: elapsed, mimeType: type })
            setStatus('recorded')
        }

        recorderRef.current = rec
        startedAtRef.current = Date.now()
        setSeconds(0)
        setStatus('recording')
        rec.start()

        timerRef.current = setInterval(() => {
            const s = Math.floor((Date.now() - startedAtRef.current) / 1000)
            setSeconds(Math.min(s, MAX_SECONDS))
            if (s >= MAX_SECONDS) stop() // R-2: auto-stop at 60 seconds
        }, 500)
    }, [release, stop, stopStream])

    const reset = useCallback(() => {
        release()
        setRecording(null)
        setSeconds(0)
        setError('')
        setStatus('idle')
    }, [release])

    return { status, seconds, recording, error, start, stop, reset }
}