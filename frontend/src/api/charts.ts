import { api } from './client'
import type { Chart } from '@/types'

export function getCharts() {
  return api.get<Chart[]>('/api/charts')
}

export function getChart(id: number) {
  return api.get<Chart>(`/api/charts/${id}`)
}

export function addChart(data: { name: string; url: string }) {
  return api.post<Chart>('/api/charts', data)
}

export function updateChart(id: number, data: Partial<Pick<Chart, 'name' | 'url' | 'enabled'>>) {
  return api.put<Chart>(`/api/charts/${id}`, data)
}

export function deleteChart(id: number) {
  return api.delete<{ ok: boolean }>(`/api/charts/${id}`)
}
