import { api } from './client'
import type { Notification } from '@/types'

export interface NotificationsResponse {
  items: Notification[]
  total: number
}

export function getNotifications(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString()
  return api.get<NotificationsResponse>(`/api/notifications${qs ? '?' + qs : ''}`)
}
