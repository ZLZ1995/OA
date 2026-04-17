import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default http
