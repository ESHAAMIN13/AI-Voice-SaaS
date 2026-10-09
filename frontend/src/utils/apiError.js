// Turns an Axios error into one readable message for the user.
export function getErrorMessage(error) {
    if (!error.response) {
        return 'Cannot reach the server. Check your internet or try again later.'
    }
    const { status, data } = error.response
    if (status === 429) return 'Too many attempts. Please wait a minute and try again.'

    // Field errors, e.g. { password: ["This password is too common."] }
    if (data?.errors && typeof data.errors === 'object') {
        const first = Object.values(data.errors).flat()[0]
        if (first) return String(first)
    }
    return data?.message || 'Something went wrong. Please try again.'
}