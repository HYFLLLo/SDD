import type { ApiResponse, PageResponse, Notification, NotificationReadResponse } from '../types'

/** GET /api/notifications 通知列表响应 */
export const notificationsListResponse: ApiResponse<PageResponse<Notification>> = {
  code: 200,
  message: 'success',
  data: {
    items: [
      {
        id: 'notif-0001',
        type: 'your_turn',
        chain_id: 'chain-0001',
        chain_title: '戴帽子的猫',
        read: false,
        created_at: '2026-08-19T13:49:07Z',
      },
      {
        id: 'notif-0002',
        type: 'node_submitted',
        chain_id: 'chain-0001',
        chain_title: '戴帽子的猫',
        read: false,
        created_at: '2026-08-19T12:00:07Z',
      },
      {
        id: 'notif-0003',
        type: 'chain_done',
        chain_id: 'chain-0002',
        chain_title: '会飞的鱼',
        read: true,
        created_at: '2026-08-18T10:00:07Z',
      },
    ],
    total: 3,
    page: 1,
    page_size: 20,
  },
}

/** POST /api/notifications/read 响应 */
export const notificationsReadResponse: ApiResponse<NotificationReadResponse> = {
  code: 200,
  message: 'success',
  data: {
    read_count: 2,
  },
}
