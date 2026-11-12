import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { message } from 'antd'
import './styles/tokens.css'
import './styles/global.css'
import { router } from './router'
import { setupMock } from './mocks'
import { setUnauthorizedHandler } from './services/api'
import { useAuthStore } from './stores/useAuthStore'

// VITE_USE_MOCK=true 时启用 Mock（开发辅助）
if (import.meta.env.VITE_USE_MOCK === 'true') {
  setupMock()
}

// 401 统一处理：清登录态 + 提示；跳转由 ProtectedRoute 订阅 store.token 响应式完成（不整页刷新）
setUnauthorizedHandler(() => {
  useAuthStore.getState().logout()
  message.warning('登录已过期，请重新登录')
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
