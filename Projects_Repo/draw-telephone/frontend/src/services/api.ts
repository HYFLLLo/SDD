import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

/** 401 回调：由 main.tsx 注入（清 store + 提示 + 路由跳转），避免此处整页刷新丢 SPA 状态 */
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? ''
    // 登录/注册接口的 401 是「凭据错误」业务反馈，不能当登录过期处理（否则登录失败也被踢去登录页）
    const isAuthEndpoint = url.startsWith('/auth/')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      // 统一清空 token + user（此前只删 token 导致 user 残留、状态不一致）
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      onUnauthorized?.()
    }
    return Promise.reject(error)
  },
)

export default api
