import api from './api'
import type { ApiResponse, VoteRequest, VoteResult, VoteResultDetail } from '../types'

/** POST /api/chains/{id}/votes 提交投票 */
export async function submitVotes(chainId: string, data: VoteRequest) {
  const res = await api.post<ApiResponse<VoteResult>>(`/chains/${chainId}/votes`, data)
  return res.data
}

/** GET /api/chains/{id}/votes/result 投票结果 */
export async function getVoteResult(chainId: string) {
  const res = await api.get<ApiResponse<VoteResultDetail>>(`/chains/${chainId}/votes/result`)
  return res.data
}
