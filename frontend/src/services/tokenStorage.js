// ALL token handling lives in this file (decision J3).
// Access token: kept in memory only (lost on page reload, which is intended).
// Refresh token: kept in localStorage so the user stays logged in.

const REFRESH_KEY = 'refresh_token'

let accessToken = null

export function getAccessToken() {
    return accessToken
}

export function getRefreshToken() {
    try {
        return localStorage.getItem(REFRESH_KEY)
    } catch {
        return null
    }
}

export function setTokens({ access, refresh }) {
    if (access) accessToken = access
    if (refresh) {
        try {
            localStorage.setItem(REFRESH_KEY, refresh)
        } catch {
            // storage blocked (private mode etc.): user will simply need to log in again
        }
    }
}

export function clearTokens() {
    accessToken = null
    try {
        localStorage.removeItem(REFRESH_KEY)
    } catch {
        // nothing to do
    }
}