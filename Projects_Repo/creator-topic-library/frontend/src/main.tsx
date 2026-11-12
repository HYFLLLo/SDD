import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import { warmPaperTheme } from './styles/theme'
import './styles/global.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider locale={zhCN} theme={warmPaperTheme}>
      <App />
    </ConfigProvider>
  </StrictMode>,
)
