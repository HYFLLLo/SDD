/** POST /api/ai/prompt 请求体 */
export interface AiPromptRequest {
  count: number
}

/** POST /api/ai/prompt 响应 data */
export interface AiPromptResponse {
  prompts: string[]
}

/** POST /api/ai/assist 请求体 */
export interface AiAssistRequest {
  chain_id: string
}

/** POST /api/ai/assist 响应 data */
export interface AiAssistResponse {
  content_type: string
  content_url: string | null
  content_text: string | null
}
