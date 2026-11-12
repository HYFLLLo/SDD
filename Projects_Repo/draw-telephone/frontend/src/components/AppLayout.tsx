import { Outlet } from 'react-router-dom'
import AppHeader from './AppHeader'

/** 全局布局：AppHeader + 页面内容 */
export default function AppLayout() {
  return (
    <>
      <AppHeader />
      <main className="container">
        <Outlet />
      </main>
    </>
  )
}
