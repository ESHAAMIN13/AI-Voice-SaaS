import api from './api'

export async function createGeneration({ voiceProfile, language, text }) {
    const res = await api.post('/generations/', {
        voice_profile: voiceProfile,
        language,
        text,
    })
    return res.data.data
}

export async function listGenerations() {
    const res = await api.get('/generations/')
    return res.data.data
}