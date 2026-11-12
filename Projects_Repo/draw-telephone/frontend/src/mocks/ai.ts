import type { ApiResponse, AiPromptResponse } from '../types'

/** POST /api/ai/prompt AI 起手题响应 */
export const aiPromptResponse: ApiResponse<AiPromptResponse> = {
  code: 200,
  message: 'success',
  data: {
    prompts: ['戴帽子的猫'],
  },
}

/** POST /api/ai/prompt AI 服务不可用响应 */
export const aiPromptUnavailableResponse: ApiResponse<null> = {
  code: 503,
  message: 'AI 服务暂不可用，请手动输入题词',
  data: null,
}
