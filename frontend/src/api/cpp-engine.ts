import { api } from './client'
import type { CppEngineStatus } from '@/types'

export function getEngineStatus() {
  return api.get<CppEngineStatus>('/api/cpp-engine/status')
}

export function startEngine() {
  return api.post<{ ok: boolean; pid: number }>('/api/cpp-engine/start')
}

export function stopEngine() {
  return api.post<{ ok: boolean }>('/api/cpp-engine/stop')
}

export function getEngineLogs() {
  return api.get<{ lines: string[] }>('/api/cpp-engine/logs')
}
