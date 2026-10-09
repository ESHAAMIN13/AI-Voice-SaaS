import axios from 'axios'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './tokenStorage'

// One shared Axios client. Every API call in the app goes through this.
const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    timeout: 15000,
})

// 1) Attach the access token to every request
api.interceptors.request.use((config) => {
    const token = getAccessToken()
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// 2) On 401, try ONE refresh, then repeat the original request
let refreshPromise = null // shared, so parallel 401s trigger only one refresh

async function refreshAccessToken() {
    const refresh = getRefreshToken()
    if (!refresh) throw new Error('No refresh token')
    // Plain axios (not `api`) so this call can never loop into the interceptor
    const res = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL}/auth/refresh/`,
        { refresh },
        { timeout: 15000 },
    )
    setTokens(res.data.data) // rotation: new access AND new refresh
    return res.data.data.access
}

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config
        const isAuthCall = original?.url?.includes('/auth/')

        if (error.response?.status !== 401 || !original || original._retried || isAuthCall) {
            return Promise.reject(error)
        }
        original._retried = true

        try {
            refreshPromise = refreshPromise || refreshAccessToken()
            const newAccess = await refreshPromise
            original.headers.Authorization = `Bearer ${newAccess}`
            return api(original)
        } catch {
            clearTokens()
            window.dispatchEvent(new Event('auth:logout')) // AuthContext (14.4) listens
            return Promise.reject(error)
        } finally {
            refreshPromise = null
        }
    },
)

export default api