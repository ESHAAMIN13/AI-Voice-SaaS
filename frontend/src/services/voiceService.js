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
export async function uploadSample(voiceId, file) {
    const form = new FormData()
    form.append('file', file)
    // The server measures the duration itself, so the client sends only the file.
    // The timeout is generous because the server checks the audio before saving it.
    const res = await api.post(`/voices/${voiceId}/upload/`, form, { timeout: 120000 })
    return res.data.data
}