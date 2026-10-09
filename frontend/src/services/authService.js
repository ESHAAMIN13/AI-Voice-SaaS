import api from './api'

export async function registerRequest({ email, password, fullName }) {
    const res = await api.post('/auth/register/', {
        email,
        password,
        full_name: fullName,
    })
    return res.data.data
}

export async function loginRequest({ email, password }) {
    const res = await api.post('/auth/login/', { email, password })
    return res.data.data // { access, refresh, user }
}

export async function logoutRequest(refresh) {
    await api.post('/auth/logout/', { refresh })
}

export async function fetchProfile() {
    const res = await api.get('/profile/')
    return res.data.data
}