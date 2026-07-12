import { api } from './client'

export function getStrategy() {
  return api.get<{ content: string }>('/api/strategy')
}

export function updateStrategy(content: string) {
  return api.put<{ ok: boolean }>('/api/strategy', { content })
}
