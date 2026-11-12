import type { ApiResponse, AuthResponse } from '../types'

/** POST /api/auth/login 成功（格式严格遵守 api-contracts.md） */
export const loginSuccessResponse: ApiResponse<AuthResponse> = {
  code: 200,
  message: 'success',
  data: {
    access_token: 'mock-token-xxx',
    user: {
      id: 'mock-uuid',
      username: 'mockuser',
      nickname: '[Mock] 小A',
      avatar_url: null,
    },
  },
}

/** POST /api/auth/login 失败（401） */
export const loginFailResponse: ApiResponse<null> = {
  code: 401,
  message: '用户名或密码错误',
  data: null,
}

/** POST /api/auth/register 成功 */
export const registerSuccessResponse: ApiResponse<AuthResponse> = {
  code: 200,
  message: 'success',
  data: {
    access_token: 'mock-token-xxx',
    user: {
      id: 'mock-uuid',
      username: 'mockuser',
      nickname: '[Mock] 小A',
      avatar_url: null,
    },
  },
}

/** POST /api/auth/register 失败（400） */
export const registerFailResponse: ApiResponse<null> = {
  code: 400,
  message: '用户名已存在',
  data: null,
}
