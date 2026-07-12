import { api } from './client'
import type { Settings } from '@/types'

export function getSettings() {
  return api.get<Settings>('/api/settings')
}

export function updateSettings(data: Partial<Settings>) {
  return api.put<{ ok: boolean }>('/api/settings', data)
}
