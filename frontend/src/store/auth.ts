import { defineStore } from 'pinia'
import { me } from '@/api/auth'

interface UserProfile {
  id: number
  username: string
  real_name: string
  roles: string[]
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null as UserProfile | null
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token)
  },
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('token', token)
    },
    clearAuth() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
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
