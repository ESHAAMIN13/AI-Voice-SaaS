import api from './api'

export async function listVoices() {
    const res = await api.get('/voices/')
    return res.data.data
}

export async function createVoice({ name, description, consent }) {
    const res = await api.post('/voices/', { name, description, consent })
    return res.data.data
}

export async function deleteVoice(id) {
    await api.delete(`/voices/${id}/`)
}

export async function uploadSample(voiceId, file, durationSec) {
    const form = new FormData()
    form.append('file', file)
    if (durationSec) form.append('duration_sec', String(durationSec))
    const res = await api.post(`/voices/${voiceId}/upload/`, form, { timeout: 60000 })
    return res.data.data
}