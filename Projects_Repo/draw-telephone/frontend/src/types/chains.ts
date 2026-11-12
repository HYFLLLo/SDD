import type { WorkAuthor } from './works'

/** 链成员 */
export interface ChainMember {
  id: string
  nickname: string
  avatar_url: string | null
}

/** 链节点（大厅进度） */
export interface ChainNode {
  seq: number
  type: 'draw' | 'describe'
  author: WorkAuthor
  is_ai: boolean
  submitted_at: string
}

/** POST /api/chains 创建链成功响应 data */
export interface Chain {
  id: string
  title: string
  chain_length: number
  visibility: 'invite' | 'public'
  room_code: string
  prompt_source: 'manual' | 'ai'
  prompt_text: string
  status: string
  creator_id: string
  created_at: string
  expires_at: string
}

/** POST /api/chains 请求体 */
export interface CreateChainRequest {
  title?: string
  chain_length: number
  visibility: 'invite' | 'public'
  prompt_source: 'manual' | 'ai'
  prompt_text?: string
}

/** GET /api/chains/{room_code} 加入前校验响应 data */
export interface ChainLookup {
  id: string
  title: string
  chain_length: number
  current_seq: number
  status: string
  is_full: boolean
  remaining_slots: number
  expires_at: string
}

/** POST /api/chains/{id}/join 响应 data */
export interface ChainJoinResponse {
  chain_id: string
  joined: boolean
}

/** GET /api/chains/{id} 链大厅详情 */
export interface ChainDetail {
  id: string
  title: string
  chain_length: number
  visibility: 'invite' | 'public'
  room_code: string
  prompt_source: 'manual' | 'ai'
  prompt_text: string
  status: string
  current_seq: number
  current_node_type: 'draw' | 'describe'
  current_author: WorkAuthor
  ai_countdown_at: string | null
  members: ChainMember[]
  nodes: ChainNode[]
  created_at: string
  expires_at: string
}
