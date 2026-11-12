/** 作品作者（详情/节点内嵌） */
export interface WorkAuthor {
  id: string
  nickname: string
}

/** GET /api/works 列表项 */
export interface WorkListItem {
  id: string
  title: string
  chain_length: number
  member_count: number
  like_count: number
  thumb_url: string
  created_at: string
}

/** 作品节点 */
export interface WorkNode {
  id: string
  seq: number
  type: 'draw' | 'describe'
  author: WorkAuthor
  content_type: 'image' | 'text'
  content_url?: string
  content_text?: string
  is_ai: boolean
  submitted_at: string
}

/** GET /api/works/{id} 详情 */
export interface WorkDetail {
  id: string
  title: string
  chain_length: number
  creator: WorkAuthor
  prompt_source: 'manual' | 'ai'
  prompt_text: string
  status: string
  created_at: string
  completed_at: string
  nodes: WorkNode[]
}

/** GET /api/users/me/works 列表项 */
export interface MyWorkListItem {
  id: string
  title: string
  chain_length: number
  status: string
  role: string
  thumb_url: string
  created_at: string
}
