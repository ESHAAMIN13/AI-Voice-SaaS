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