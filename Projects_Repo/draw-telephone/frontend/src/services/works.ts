import api from './api'
import type { ApiResponse, PageResponse, WorkDetail, WorkListItem } from '../types'

/** GET /api/works 广场作品流（游客可访问） */
export async function getWorks(params?: { page?: number; page_size?: number; sort?: string }) {
  const res = await api.get<ApiResponse<PageResponse<WorkListItem>>>('/works', { params })
  return res.data
}

/** GET /api/works/{id} 作品详情 */
export async function getWorkDetail(id: string) {
  const res = await api.get<ApiResponse<WorkDetail>>(`/works/${id}`)
  return res.data
}
