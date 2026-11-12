/** 用户（api-contracts.md 通用数据类型） */
export interface User {
  id: string
  username: string
  nickname: string
  avatar_url: string | null
}

/** POST /api/auth/login 请求体 */
export interface LoginRequest {
  username: string
  password: string
}

/** POST /api/auth/register 请求体 */
export interface RegisterRequest {
  username: string
  password: string
  nickname: string
}

/** POST /api/auth/login | POST /api/auth/register 成功响应 data */
export interface AuthResponse {
  access_token: string
  user: User
}
