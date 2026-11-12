import type { WorkAuthor } from './works'

/** 投票维度 */
export type VoteDimension = 'most_drift' | 'best_draw' | 'best_describe'

/** POST /api/chains/{id}/votes 请求体 */
export interface VoteRequest {
  votes: { dimension: VoteDimension; target_node_id: string }[]
}

/** POST /api/chains/{id}/votes 响应 data */
export interface VoteResult {
  results: { dimension: VoteDimension; target_node_id: string; vote_count: number }[]
}

/** GET /api/chains/{id}/votes/result 响应 data */
export interface VoteResultDetail {
  results: {
    dimension: VoteDimension
    target_node_id: string
    target_author: WorkAuthor
    vote_count: number
  }[]
}
