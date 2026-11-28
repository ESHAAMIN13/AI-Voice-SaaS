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
export async function fetchHistory({ page = 1, status = '' } = {}) {
  const params = { page }
  if (status) params.status = status
  const res = await api.get('/generations/history/', { params })
  return res.data.data
}

export async function deleteGeneration(id) {
  await api.delete(`/generations/${id}/`)
}
