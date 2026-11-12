import { useState } from 'react'
import { Button, Form, Input, Tabs, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/useAuthStore'
import './LoginPage.css'

type TabKey = 'login' | 'register'

interface LocationFromState {
  from?: string
}

/**
 * P09 登录/注册页。
 * 登录/注册 Tab 切换、用户名+密码表单、注册多一个昵称字段、「先逛逛」游客入口。
 * VITE_USE_MOCK=false 时调用真实后端 /api/auth/register、/api/auth/login。
 */
export default function LoginPage() {
  const navigate = useNavigate()
  const { login, register, loginStatus } = useAuthStore()
  const [tab, setTab] = useState<TabKey>('login')
  const [loginForm] = Form.useForm()
  const [registerForm] = Form.useForm()

  const loading = loginStatus === 'loading'

  const redirectTo = (state: unknown) => {
    const from = (state as LocationFromState | null)?.from
    navigate(from ?? '/', { replace: true })
  }

  const handleLogin = async (values: { username: string; password: string }) => {
    try {
      await login(values)
      message.success('登录成功')
      redirectTo((history.state as { usr?: { from?: string } })?.usr)
    } catch {
      message.error('用户名或密码错误')
    }
  }

  const handleRegister = async (values: {
    username: string
    password: string
    nickname: string
  }) => {
    try {
      await register(values)
      message.success('注册成功')
      navigate('/', { replace: true })
    } catch {
      message.error('用户名已存在')
    }
  }

  const handleGuest = () => {
    navigate('/', { replace: true })
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-mark" aria-hidden="true" />
          <h1 className="brand-title">画意接龙</h1>
          <p className="brand-sub">一条画 · 一条述 · 看一幅画如何跑偏</p>
        </div>

        <Tabs
          activeKey={tab}
          onChange={(k) => setTab(k as TabKey)}
          centered
          className="login-tabs"
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form
                  form={loginForm}
                  layout="vertical"
                  onFinish={handleLogin}
                  requiredMark={false}
                  className="login-form"
                >
                  <Form.Item
                    name="username"
                    label="用户名"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input placeholder="输入用户名" autoComplete="username" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    label="密码"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password placeholder="输入密码" autoComplete="current-password" />
                  </Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    block
                    className="btn-primary"
                  >
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form
                  form={registerForm}
                  layout="vertical"
                  onFinish={handleRegister}
                  requiredMark={false}
                  className="login-form"
                >
                  <Form.Item
                    name="username"
                    label="用户名"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input placeholder="给自己起个用户名" autoComplete="username" />
                  </Form.Item>
                  <Form.Item
                    name="nickname"
                    label="昵称"
                    rules={[{ required: true, message: '请输入昵称' }]}
                  >
                    <Input placeholder="展示给其他人的名字" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    label="密码"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password placeholder="设置密码" autoComplete="new-password" />
                  </Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    block
                    className="btn-primary"
                  >
                    注册
                  </Button>
                </Form>
              ),
            },
          ]}
        />

        <div className="guest-entry">
          <button type="button" className="guest-link" onClick={handleGuest}>
            先逛逛 →
          </button>
        </div>
      </div>
    </div>
  )
}
