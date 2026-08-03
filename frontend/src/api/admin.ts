import { api } from './client'

export interface AdminListResponse<T = Record<string, any>> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  columns: string[]
  pk: string
}

export interface AdminListParams {
  search?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
}

export async function fetchAdminList<T = Record<string, any>>(
  table: string,
  params: AdminListParams = {}
): Promise<AdminListResponse<T>> {
  const query = new URLSearchParams()
  if (params.search) query.set('search', params.search)
  if (params.page) query.set('page', params.page.toString())
  if (params.page_size) query.set('page_size', params.page_size.toString())
  if (params.sort_by) query.set('sort_by', params.sort_by)
  if (params.sort_dir) query.set('sort_dir', params.sort_dir)
  const queryString = query.toString()
  const path = `/api/admin/${table}${queryString ? `?${queryString}` : ''}`
  return api.get<AdminListResponse<T>>(path)
}

export async function fetchAdminDetail<T = Record<string, any>>(
  table: string,
  pkVal: string | number
): Promise<T> {
  return api.get<T>(`/api/admin/${table}/${pkVal}`)
}

export async function createAdminRecord<T = Record<string, any>>(
  table: string,
  data: Record<string, any>
): Promise<T> {
  return api.post<T>(`/api/admin/${table}`, data)
}

export async function updateAdminRecord<T = Record<string, any>>(
  table: string,
  pkVal: string | number,
  data: Record<string, any>
): Promise<T> {
  return api.put<T>(`/api/admin/${table}/${pkVal}`, data)
}

export async function deleteAdminRecord(
  table: string,
  pkVal: string | number
): Promise<{ status: string; id: string | number }> {
  return api.delete<{ status: string; id: string | number }>(`/api/admin/${table}/${pkVal}`)
}

export async function bulkDeleteAdminRecords(
  table: string,
  keysOrIds: (string | number)[]
): Promise<{ deleted_count: number }> {
  return api.post<{ deleted_count: number }>(`/api/admin/${table}/bulk-delete`, {
    ids: keysOrIds,
    keys: keysOrIds,
  })
}
