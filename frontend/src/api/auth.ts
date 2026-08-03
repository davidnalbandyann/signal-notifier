import { api } from './client'

export interface LoginResponse {
  token: string
  username: string
  expires_in: number
}

export function login(username: string, password: string) {
  return api.post<LoginResponse>('/api/auth/login', { username, password })
}
