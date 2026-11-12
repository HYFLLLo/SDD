import { Alert, Layout, Spin } from 'antd'
import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useTopicLibraryStore } from '../stores/useTopicLibraryStore'
import AppHeader from './AppHeader'

const { Content } = Layout

export default function AppShell() {
  const location = useLocation()
  const loadLibrary = useTopicLibraryStore((state) => state.loadLibrary)
  const status = useTopicLibraryStore((state) => state.status)
  const errorMessage = useTopicLibraryStore((state) => state.errorMessage)

  useEffect(() => {
    void loadLibrary()
  }, [loadLibrary])

  return (
    <Layout className="app-layout">
      <AppHeader />
      <Content className="app-content">
        {status === 'loading' ? (
          <div className="page-stack">
            <Spin size="large" />
          </div>
        ) : null}
        {status === 'error' ? (
          <div className="page-stack">
            <Alert type="error" message="本地数据加载失败" description={errorMessage} showIcon />
          </div>
        ) : null}
        <Outlet key={location.pathname} />
      </Content>
    </Layout>
  )
}
