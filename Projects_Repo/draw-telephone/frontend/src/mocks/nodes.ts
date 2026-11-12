import type { ApiResponse, NodePrevious, SubmitNodeResponse } from '../types'

/** GET /api/nodes/{id}/previous 上一节点内容（画节点上一节点是述） */
export const nodePreviousTextResponse: ApiResponse<NodePrevious> = {
  code: 200,
  message: 'success',
  data: {
    node_id: 'node-0002',
    seq: 2,
    type: 'draw',
    content_type: 'text',
    content_text: '一只戴礼帽的猫',
  },
}

/** GET /api/nodes/{id}/previous 上一节点内容（述节点上一节点是画） */
export const nodePreviousImageResponse: ApiResponse<NodePrevious> = {
  code: 200,
  message: 'success',
  data: {
    node_id: 'node-0003',
    seq: 3,
    type: 'describe',
    content_type: 'image',
    content_url: '/mock-thumbs/cat-hat.svg',
  },
}

/** POST /api/nodes/{id}/submit 响应 */
export const submitNodeResponse: ApiResponse<SubmitNodeResponse> = {
  code: 200,
  message: 'success',
  data: {
    node_id: 'node-0004',
    seq: 3,
    status: 'submitted',
    next_seq: 4,
    chain_status: 'in_progress',
  },
}

/** 403 未轮到响应 */
export const nodeNotYourTurnResponse: ApiResponse<null> = {
  code: 403,
  message: '当前未轮到你',
  data: null,
}
