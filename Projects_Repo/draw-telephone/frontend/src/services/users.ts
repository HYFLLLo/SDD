import api from './api'
import type { ApiResponse, PageResponse, MyWorkListItem, UserProfile } from '../types'

/** GET /api/users/me 个人资料 */
export async function getUserProfile() {
  const res = await api.get<ApiResponse<UserProfile>>('/users/me')
  return res.data
}

/** GET /api/users/me/works 我的作品 */
export async function getMyWorks(params?: { page?: number; page_size?: number }) {
  const res = await api.get<ApiResponse<PageResponse<MyWorkListItem>>>('/users/me/works', { params })
  return res.data
}
