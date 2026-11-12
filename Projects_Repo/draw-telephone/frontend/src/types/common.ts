/** 统一响应格式（api-contracts.md 通用约定） */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/** 分页响应 */
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
