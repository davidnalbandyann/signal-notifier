import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('tcm_token'))

  const isAuthenticated = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password)
    token.value = res.token
    localStorage.setItem('tcm_token', res.token)
  }

  function logout() {
    token.value = null
    localStorage.removeItem('tcm_token')
  }

  return { token, isAuthenticated, login, logout }
})
