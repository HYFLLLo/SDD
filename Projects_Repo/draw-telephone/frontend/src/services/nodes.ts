import api from './api'
import type { ApiResponse, NodePrevious, SubmitNodeRequest, SubmitNodeResponse } from '../types'

/** GET /api/nodes/{id}/previous 获取上一节点内容 */
export async function getNodePrevious(id: string) {
  const res = await api.get<ApiResponse<NodePrevious>>(`/nodes/${id}/previous`)
  return res.data
}

/** POST /api/nodes/{id}/submit 提交节点 */
export async function submitNode(id: string, data: SubmitNodeRequest) {
  const res = await api.post<ApiResponse<SubmitNodeResponse>>(`/nodes/${id}/submit`, data)
  return res.data
}
