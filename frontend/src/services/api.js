
import axios from 'axios'

// One shared Axios client. Every API call in the app goes through this.
const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    timeout: 15000,
})

export default api