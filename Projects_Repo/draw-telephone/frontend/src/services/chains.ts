import api from './api'
import type {
  ApiResponse,
  Chain,
  ChainDetail,
  ChainJoinResponse,
  ChainLookup,
  CreateChainRequest,
} from '../types'

/** POST /api/chains 创建链 */
export async function createChain(data: CreateChainRequest) {
  const res = await api.post<ApiResponse<Chain>>('/chains', data)
  return res.data
}

/** GET /api/chains/{room_code} 按房间码查询链（加入前校验） */
export async function lookupChain(roomCode: string) {
  const res = await api.get<ApiResponse<ChainLookup>>(`/chains/${roomCode}`)
  return res.data
}

/** POST /api/chains/{id}/join 加入链 */
export async function joinChain(id: string) {
  const res = await api.post<ApiResponse<ChainJoinResponse>>(`/chains/${id}/join`)
  return res.data
}

/** GET /api/chains/{id}/detail 链大厅详情 */
export async function getChainDetail(id: string) {
  const res = await api.get<ApiResponse<ChainDetail>>(`/chains/${id}/detail`)
  return res.data
}
