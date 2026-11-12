/** GET /api/nodes/{id}/previous 上一节点内容 */
export interface NodePrevious {
  node_id: string
  seq: number
  type: 'draw' | 'describe'
  content_type: 'image' | 'text'
  content_url?: string
  content_text?: string
}

/** POST /api/nodes/{id}/submit 请求体（画节点） */
export interface SubmitNodeImageRequest {
  content_type: 'image'
  content_url: string
}

/** POST /api/nodes/{id}/submit 请求体（描述节点） */
export interface SubmitNodeTextRequest {
  content_type: 'text'
  content_text: string
}

export type SubmitNodeRequest = SubmitNodeImageRequest | SubmitNodeTextRequest

/** POST /api/nodes/{id}/submit 响应 data */
export interface SubmitNodeResponse {
  node_id: string
  seq: number
  status: string
  next_seq: number
  chain_status: string
}
