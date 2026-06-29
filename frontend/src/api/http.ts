import axios from 'axios'

function isDesktopEmbeddedRuntime() {
  if (typeof window === 'undefined') {
    return false
  }

  if (window.desktopApp?.isDesktopShell) {
    return true
  }

  try {
    return window.parent !== window
  } catch {
    return false
  }
}

function resolveApiBaseUrl() {
  const runtimeBackendUrl = isDesktopEmbeddedRuntime()
    ? localStorage.getItem('desktop_backend_url')?.trim()
    : ''
  const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()

  if (runtimeBackendUrl) {
    return `${runtimeBackendUrl.replace(/\/+$/, '')}/api/v1`
  }

  if (configuredApiBaseUrl) {
    return configuredApiBaseUrl.replace(/\/+$/, '')
  }

  return '/api/v1'
}

const apiBaseUrl = resolveApiBaseUrl()

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default http
