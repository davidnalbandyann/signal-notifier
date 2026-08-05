import { api } from './client'
import type { CppStrategyDefinition, Strategy } from '@/types'

export function getStrategies(type?: 'prompt' | 'cpp') {
  const q = type ? `?type=${type}` : ''
  return api.get<{ strategies: Strategy[] }>(`/api/strategies${q}`)
}

export function getStrategy(id: number) {
  return api.get<Strategy>(`/api/strategies/${id}`)
}

export function createStrategy(data: Partial<Strategy>) {
  return api.post<Strategy>('/api/strategies', data)
}

export function updateStrategy(id: number, data: Partial<Strategy>) {
  return api.put<Strategy>(`/api/strategies/${id}`, data)
}

export function deleteStrategy(id: number) {
  return api.delete<{ ok: boolean }>(`/api/strategies/${id}`)
}

export function activateStrategy(id: number) {
  return api.post<Strategy>(`/api/strategies/${id}/activate`)
}

export function duplicateStrategy(id: number) {
  return api.post<Strategy>(`/api/strategies/${id}/duplicate`)
}

export function getCppCatalog() {
  return api.get<{ catalog: CppStrategyDefinition[] }>('/api/strategies/catalog')
}
