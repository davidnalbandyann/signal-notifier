import { api } from './client'
import type { Analysis } from '@/types'

export interface AnalysesResponse {
  items: Analysis[]
  total: number
}

export function getAnalyses(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString()
  return api.get<AnalysesResponse>(`/api/analyses${qs ? '?' + qs : ''}`)
}

export function getAnalysis(id: number) {
  return api.get<Analysis>(`/api/analyses/${id}`)
}

export function getScreenshot(id: number): Promise<Blob> {
  const token = localStorage.getItem('tcm_token')
  return fetch(`/api/analyses/${id}/screenshot`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }).then((r) => {
    if (!r.ok) throw new Error('No screenshot')
    return r.blob()
  })
}

export function resendNotification(id: number) {
  return api.post<{ ok: boolean }>(`/api/analyses/${id}/resend`)
}

export function reanalyze(id: number) {
  return api.post<{ ok: boolean }>(`/api/analyses/${id}/reanalyze`)
}
