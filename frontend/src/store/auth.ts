import { defineStore } from 'pinia'

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
    }
  }
})
