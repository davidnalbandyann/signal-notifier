import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('tcm_token'))
  const username = ref<string | null>(localStorage.getItem('tcm_username'))

  const isAuthenticated = computed(() => !!token.value)
  const initials = computed(() =>
    (username.value || '?').slice(0, 2).toUpperCase()
  )

  async function login(name: string, password: string) {
    const res = await apiLogin(name, password)
    token.value = res.token
    username.value = res.username
    localStorage.setItem('tcm_token', res.token)
    localStorage.setItem('tcm_username', res.username)
  }

  function logout() {
    token.value = null
    username.value = null
    localStorage.removeItem('tcm_token')
    localStorage.removeItem('tcm_username')
  }

  return { token, username, initials, isAuthenticated, login, logout }
})
