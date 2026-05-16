import { defineStore } from 'pinia'
import { me } from '@/api/auth'
import { useWorkspaceStore } from './workspace'

interface UserProfile {
  id: number
  username: string
  real_name: string
  roles: string[]
}

function readTokenFromStorage() {
  const accessToken = localStorage.getItem('access_token')
  if (accessToken) {
    return accessToken
  }

  const legacyToken = localStorage.getItem('token')
  if (legacyToken) {
    localStorage.setItem('access_token', legacyToken)
    localStorage.removeItem('token')
    return legacyToken
  }

  return ''
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: readTokenFromStorage(),
    user: null as UserProfile | null
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token)
  },
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('access_token', token)
      localStorage.removeItem('token')
    },
    clearAuth() {
      const workspace = useWorkspaceStore()
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('access_token')
      workspace.clearWorkspace()
    },
    setUser(user: UserProfile) {
      this.user = user
    },
    async ensureUserLoaded() {
      if (!this.token) {
        this.user = null
        return null
      }
      if (this.user) {
        return this.user
      }
      try {
        const profile = await me()
        this.user = profile
        return profile
      } catch {
        this.clearAuth()
        return null
      }
    }
  }
})
