import api from './api'
import type { AiAssistRequest, AiAssistResponse, AiPromptRequest, AiPromptResponse, ApiResponse } from '../types'

/** POST /api/ai/prompt AI 起手题生成 */
export async function generatePrompts(data: AiPromptRequest) {
  const res = await api.post<ApiResponse<AiPromptResponse>>('/ai/prompt', data)
  return res.data
}

/** POST /api/ai/assist 接力页 AI 辅助创作（画节点文生图 / 述节点看图描述） */
export async function aiAssist(data: AiAssistRequest) {
  const res = await api.post<ApiResponse<AiAssistResponse>>('/ai/assist', data)
  return res.data
}
