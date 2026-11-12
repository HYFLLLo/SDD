import type { ApiResponse, UserProfile } from '../types'

/** GET /api/users/me 个人资料响应 */
export const userProfileResponse: ApiResponse<UserProfile> = {
  code: 200,
  message: 'success',
  data: {
    id: 'mock-uuid',
    username: 'mockuser',
    nickname: '[Mock] 小A',
    avatar_url: null,
    created_at: '2026-08-01T00:00:00Z',
    participated_chains: 12,
    created_chains: 3,
  },
}

/** GET /api/users/me/works 我的作品响应 */
export const myWorksListResponse: ApiResponse<{
  items: {
    id: string
    title: string
    chain_length: number
    status: string
    role: string
    thumb_url: string
    created_at: string
  }[]
  total: number
  page: number
  page_size: number
}> = {
  code: 200,
  message: 'success',
  data: {
    items: [
      {
        id: 'work-0001',
        title: '戴帽子的猫',
        chain_length: 6,
        status: 'completed',
        role: 'creator',
        thumb_url: '/mock-thumbs/cat.svg',
        created_at: '2026-08-18T13:49:07Z',
      },
      {
        id: 'work-0002',
        title: '会飞的鱼',
        chain_length: 8,
        status: 'completed',
        role: 'member',
        thumb_url: '/mock-thumbs/fish.svg',
        created_at: '2026-08-17T10:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  },
}
