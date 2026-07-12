import { api } from './client'
import type { DashboardStatus } from '@/types'

export function getStatus() {
  return api.get<DashboardStatus>('/api/status')
}

export function triggerScan() {
  return api.post<{ ok: boolean }>('/api/scan/trigger')
}

export function pauseScan() {
  return api.post<{ ok: boolean }>('/api/scan/pause')
}

export function resumeScan() {
  return api.post<{ ok: boolean }>('/api/scan/resume')
}
