/** 通知类型 */
export type NotificationType = 'your_turn' | 'chain_done' | 'node_submitted'

/** GET /api/notifications 列表项 */
export interface Notification {
  id: string
  type: NotificationType
  chain_id: string
  chain_title: string
  read: boolean
  created_at: string
}

/** POST /api/notifications/read 请求体 */
export interface NotificationReadRequest {
  notification_ids: string[]
}

/** POST /api/notifications/read 响应 data */
export interface NotificationReadResponse {
  read_count: number
}
