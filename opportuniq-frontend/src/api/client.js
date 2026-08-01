import axios from 'axios'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/$/, '')

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
})

export default apiClient
