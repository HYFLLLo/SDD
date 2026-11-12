import type { ApiResponse, VoteResult, VoteResultDetail } from '../types'

/** POST /api/chains/{id}/votes 提交投票响应 */
export const voteSubmitResponse: ApiResponse<VoteResult> = {
  code: 200,
  message: 'success',
  data: {
    results: [
      { dimension: 'most_drift', target_node_id: 'node-0005', vote_count: 3 },
      { dimension: 'best_draw', target_node_id: 'node-0003', vote_count: 2 },
      { dimension: 'best_describe', target_node_id: 'node-0006', vote_count: 4 },
    ],
  },
}

/** GET /api/chains/{id}/votes/result 投票结果响应 */
export const voteResultResponse: ApiResponse<VoteResultDetail> = {
  code: 200,
  message: 'success',
  data: {
    results: [
      { dimension: 'most_drift', target_node_id: 'node-0005', target_author: { id: 'mock-uuid-e', nickname: '小E' }, vote_count: 3 },
      { dimension: 'best_draw', target_node_id: 'node-0003', target_author: { id: 'mock-uuid-c', nickname: '小C' }, vote_count: 2 },
      { dimension: 'best_describe', target_node_id: 'node-0006', target_author: { id: 'mock-uuid', nickname: '小A' }, vote_count: 4 },
    ],
  },
}
