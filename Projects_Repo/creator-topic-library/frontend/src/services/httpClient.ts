import axios from 'axios'

export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

httpClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
)
