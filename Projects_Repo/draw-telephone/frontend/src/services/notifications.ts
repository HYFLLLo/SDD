import api from './api'
import type {
  ApiResponse,
  Notification,
  NotificationReadRequest,
  NotificationReadResponse,
  PageResponse,
} from '../types'

/** GET /api/notifications 通知列表 */
export async function getNotifications(params?: { page?: number; page_size?: number; unread_only?: boolean }) {
  const res = await api.get<ApiResponse<PageResponse<Notification>>>('/notifications', { params })
  return res.data
}

/** POST /api/notifications/read 标记通知已读 */
export async function readNotifications(data: NotificationReadRequest) {
  const res = await api.post<ApiResponse<NotificationReadResponse>>('/notifications/read', data)
  return res.data
}
