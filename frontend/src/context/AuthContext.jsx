import { useCallback, useEffect, useMemo, useState } from 'react'
import { AuthContext } from './authContextObject'
import {
    fetchProfile,
    loginRequest,
    logoutRequest,
    registerRequest,
} from '../services/authService'
import { clearTokens, getRefreshToken, setTokens } from '../services/tokenStorage'
import api from '../services/api'


// One session restore per page load. React StrictMode runs effects twice in
// development, and refresh tokens can only be used once (rotation).
let restorePromise = null

async function restoreSession() {
    const refresh = getRefreshToken()
    if (!refresh) return null
    try {
        const res = await api.post('/auth/refresh/', { refresh })
        setTokens(res.data.data)
        return await fetchProfile()
    } catch {
        clearTokens()
        return null
    }
}

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true) // true while we check an existing session

    // On app start: if a refresh token exists, get a new access token and the user.
    useEffect(() => {
        let cancelled = false
        restorePromise = restorePromise || restoreSession()
        restorePromise.then((profile) => {
            if (cancelled) return
            setUser(profile)
            setLoading(false)
        })
        return () => {
            cancelled = true
        }
    }, [])


    // api.js fires this when a token refresh fails (session is over)
    useEffect(() => {
        const onForcedLogout = () => setUser(null)
        window.addEventListener('auth:logout', onForcedLogout)
        return () => window.removeEventListener('auth:logout', onForcedLogout)
    }, [])

    const login = useCallback(async (credentials) => {
        const data = await loginRequest(credentials)
        setTokens({ access: data.access, refresh: data.refresh })
        setUser(data.user)
        return data.user
    }, [])

    const register = useCallback(async (details) => {
        await registerRequest(details)
        // After registering, log in with the same credentials
        return login({ email: details.email, password: details.password })
    }, [login])

    const logout = useCallback(async () => {
        const refresh = getRefreshToken()
        try {
            if (refresh) await logoutRequest(refresh)
        } catch {
            // even if the server call fails, the user is logged out locally
        }
        clearTokens()
        setUser(null)
    }, [])

    const value = useMemo(
        () => ({ user, setUser, loading, isAdmin: user?.role === 'ADMIN', login, register, logout }),
        [user, loading, login, register, logout],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}