import { api } from './client'
import type { 
  CppStrategyDefinition, 
  AiStrategy, 
  CppStrategy, 
  ActiveStrategy, 
  Analysis 
} from '@/types'

// AI Strategies
export function getAiStrategies() {
  return api.get<{ strategies: AiStrategy[] }>('/api/strategies/ai')
}
export function getAiStrategy(id: number) {
  return api.get<AiStrategy>(`/api/strategies/ai/${id}`)
}
export function createAiStrategy(data: Partial<AiStrategy>) {
  return api.post<AiStrategy>('/api/strategies/ai', data)
}
export function updateAiStrategy(id: number, data: Partial<AiStrategy>) {
  return api.put<AiStrategy>(`/api/strategies/ai/${id}`, data)
}
export function deleteAiStrategy(id: number) {
  return api.delete<{ ok: boolean }>(`/api/strategies/ai/${id}`)
}

// CPP Strategies
export function getCppStrategies() {
  return api.get<{ strategies: CppStrategy[] }>('/api/strategies/cpp')
}
export function getCppStrategy(id: number) {
  return api.get<CppStrategy>(`/api/strategies/cpp/${id}`)
}
export function createCppStrategy(data: Partial<CppStrategy>) {
  return api.post<CppStrategy>('/api/strategies/cpp', data)
}
export function updateCppStrategy(id: number, data: Partial<CppStrategy>) {
  return api.put<CppStrategy>(`/api/strategies/cpp/${id}`, data)
}
export function deleteCppStrategy(id: number) {
  return api.delete<{ ok: boolean }>(`/api/strategies/cpp/${id}`)
}
export function getCppCatalog() {
  return api.get<{ catalog: CppStrategyDefinition[] }>('/api/strategies/cpp/catalog')
}

// Active Strategies
export function getActiveStrategies() {
  return api.get<{ active_strategies: ActiveStrategy[] }>('/api/strategies/active')
}
export function getActiveStrategy(id: number) {
  return api.get<ActiveStrategy>(`/api/strategies/active/${id}`)
}
export function createActiveStrategy(data: Partial<ActiveStrategy>) {
  return api.post<ActiveStrategy>('/api/strategies/active', data)
}
export function updateActiveStrategy(id: number, data: Partial<ActiveStrategy>) {
  return api.put<ActiveStrategy>(`/api/strategies/active/${id}`, data)
}
export function deleteActiveStrategy(id: number) {
  return api.delete<{ ok: boolean }>(`/api/strategies/active/${id}`)
}
export function duplicateActiveStrategy(id: number) {
  return api.post<ActiveStrategy>(`/api/strategies/active/${id}/duplicate`)
}
export function testRunActiveStrategy(id: number) {
  return api.post<{ success: boolean; result: Analysis }>(`/api/strategies/active/${id}/test-run`)
}
