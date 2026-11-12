import { Layout, Menu, Typography } from 'antd'
import { Link, useLocation } from 'react-router-dom'

const { Header } = Layout

const navigationItems = [
  {
    key: '/',
    label: <Link to="/">选题库</Link>,
  },
  {
    key: '/tags',
    label: <Link to="/tags">标签管理</Link>,
  },
]

export default function AppHeader() {
  const location = useLocation()

  if (location.pathname === '/') {
    return null
  }

  const selectedKey = location.pathname === '/tags' ? '/tags' : '/'

  return (
    <Header className="app-header">
      <div className="app-header__inner">
        <Link to="/" className="app-brand">
          <Typography.Title level={4}>创作者选题灵感库</Typography.Title>
        </Link>
        <Menu
          className="app-nav"
          mode="horizontal"
          items={navigationItems}
          selectedKeys={[selectedKey]}
        />
      </div>
    </Header>
  )
}
