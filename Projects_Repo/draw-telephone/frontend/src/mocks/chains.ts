import type { ApiResponse, Chain, ChainDetail, ChainLookup } from '../types'

/** POST /api/chains 创建链成功响应（按契约显式构造 DTO） */
export const createChainResponse: ApiResponse<Chain> = {
  code: 200,
  message: 'success',
  data: {
    id: 'chain-0001',
    title: '戴帽子的猫',
    chain_length: 6,
    visibility: 'invite',
    room_code: 'DRAW4',
    prompt_source: 'ai',
    prompt_text: '戴帽子的猫',
    status: 'in_progress',
    creator_id: 'mock-uuid',
    created_at: '2026-08-19T13:49:07Z',
    expires_at: '2026-08-26T13:49:07Z',
  },
}

/** GET /api/chains/{room_code} 加入前校验响应 */
export const chainLookupResponse: ApiResponse<ChainLookup> = {
  code: 200,
  message: 'success',
  data: {
    id: 'chain-0001',
    title: '戴帽子的猫',
    chain_length: 6,
    current_seq: 3,
    status: 'in_progress',
    is_full: false,
    remaining_slots: 2,
    expires_at: '2026-08-26T13:49:07Z',
  },
}

/** POST /api/chains/{id}/join 响应 */
export const chainJoinResponse: ApiResponse<{ chain_id: string; joined: boolean }> = {
  code: 200,
  message: 'success',
  data: {
    chain_id: 'chain-0001',
    joined: true,
  },
}

/** GET /api/chains/{id} 链大厅详情（6 节点进度：3 已完成 + 1 当前 + 2 待接，5 成员） */
export const chainDetailResponse: ApiResponse<ChainDetail> = {
  code: 200,
  message: 'success',
  data: {
    id: 'chain-0001',
    title: '戴帽子的猫',
    chain_length: 6,
    visibility: 'invite',
    room_code: 'DRAW4',
    prompt_source: 'ai',
    prompt_text: '戴帽子的猫',
    status: 'in_progress',
    current_seq: 3,
    current_node_type: 'draw',
    current_author: { id: 'mock-uuid-c', nickname: '小C' },
    ai_countdown_at: '2026-08-20T13:49:07Z',
    members: [
      { id: 'mock-uuid', nickname: '小A', avatar_url: null },
      { id: 'mock-uuid-b', nickname: '小B', avatar_url: null },
      { id: 'mock-uuid-c', nickname: '小C', avatar_url: null },
      { id: 'mock-uuid-d', nickname: '小D', avatar_url: null },
      { id: 'mock-uuid-e', nickname: '小E', avatar_url: null },
    ],
    nodes: [
      { seq: 0, type: 'draw', author: { id: 'mock-uuid', nickname: '小A' }, is_ai: false, submitted_at: '2026-08-19T13:49:07Z' },
      { seq: 1, type: 'describe', author: { id: 'mock-uuid-b', nickname: '小B' }, is_ai: false, submitted_at: '2026-08-19T14:10:07Z' },
      { seq: 2, type: 'draw', author: { id: 'mock-uuid-c', nickname: '小C' }, is_ai: false, submitted_at: '2026-08-19T15:02:07Z' },
      { seq: 3, type: 'describe', author: { id: 'mock-uuid-d', nickname: '小D' }, is_ai: false, submitted_at: '2026-08-19T16:30:07Z' },
      { seq: 4, type: 'draw', author: { id: 'mock-uuid-e', nickname: '小E' }, is_ai: false, submitted_at: '2026-08-19T17:00:07Z' },
      { seq: 5, type: 'describe', author: { id: 'mock-uuid', nickname: '小A' }, is_ai: false, submitted_at: '2026-08-19T18:00:07Z' },
    ],
    created_at: '2026-08-19T13:49:07Z',
    expires_at: '2026-08-26T13:49:07Z',
  },
}
