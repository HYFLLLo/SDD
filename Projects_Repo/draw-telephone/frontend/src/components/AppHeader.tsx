import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { message } from 'antd'
import { useAuthStore } from '../stores/useAuthStore'
import { getNotifications, readNotifications } from '../services/notifications'
import type { Notification, NotificationType } from '../types'
import './AppHeader.css'

const NOTIF_ICON: Record<NotificationType, string> = {
  your_turn: '✏️',
  chain_done: '🎉',
  node_submitted: '📨',
}

const NOTIF_TEXT: Record<NotificationType, string> = {
  your_turn: '轮到你了',
  chain_done: '链完成',
  node_submitted: '节点提交',
}

/** 顶部导航栏：Logo「画意接龙」+ 广场/我的 + 通知铃铛 + 头像（下拉：我的主页/退出登录） */
export default function AppHeader() {
  const user = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)
  const nickname = user?.nickname ?? '未登录'
  const avatarText = nickname.charAt(0)
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [notifs, setNotifs] = useState<Notification[]>([])
  const [loadingNotifs, setLoadingNotifs] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const unreadCount = notifs.filter((n) => !n.read).length

  // 加载通知（仅登录用户）
  const loadNotifs = () => {
    if (!token) return
    setLoadingNotifs(true)
    getNotifications()
      .then((res) => {
        if (res.data) setNotifs(res.data.items)
      })
      .catch(() => {})
      .finally(() => setLoadingNotifs(false))
  }

  useEffect(() => {
    loadNotifs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // 点击外部关闭下拉（通知 + 头像菜单）
  useEffect(() => {
    if (!open && !menuOpen) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open, menuOpen])

  const handleBellClick = () => {
    if (!token) {
      navigate('/login')
      return
    }
    const next = !open
    setOpen(next)
    if (next && notifs.length === 0) loadNotifs()
  }

  const handleReadOne = (id: string) => {
    readNotifications({ notification_ids: [id] })
      .then(() => {
        setNotifs((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
      })
      .catch(() => message.error('标记已读失败'))
  }

  const handleReadAll = () => {
    const unreadIds = notifs.filter((n) => !n.read).map((n) => n.id)
    if (unreadIds.length === 0) return
    readNotifications({ notification_ids: unreadIds })
      .then(() => {
        setNotifs((prev) => prev.map((n) => ({ ...n, read: true })))
        message.success('已全部标记为已读')
      })
      .catch(() => message.error('标记已读失败'))
  }

  const handleAvatarClick = () => {
    if (!token) {
      navigate('/login')
      return
    }
    setMenuOpen((v) => !v)
    setOpen(false)
  }

  const handleLogout = () => {
    logout()
    setMenuOpen(false)
    message.success('已退出登录')
    navigate('/login')
  }

  const handleGoProfile = () => {
    setMenuOpen(false)
    navigate('/profile')
  }

  return (
    <header className="topbar">
      <Link to="/" className="logo">
        <span className="mark" aria-hidden="true" />
        画意接龙
      </Link>

      <nav className="nav-center">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
          广场
        </NavLink>
        <NavLink to="/profile" className={({ isActive }) => (isActive ? 'active' : '')}>
          我的
        </NavLink>
      </nav>

      <div className="nav-right" ref={ref}>
        <button type="button" className="bell" title="通知" aria-label="通知" onClick={handleBellClick}>
          <span aria-hidden="true">🔔</span>
          {unreadCount > 0 && <span className="dot" aria-hidden="true" />}
        </button>

        {open && token && (
          <div className="notif-dropdown">
            <div className="notif-head">
              <span className="notif-title">通知</span>
              {unreadCount > 0 && (
                <button type="button" className="notif-readall" onClick={handleReadAll}>
                  全部已读
                </button>
              )}
            </div>
            <div className="notif-list">
              {loadingNotifs && <div className="notif-empty">加载中…</div>}
              {!loadingNotifs && notifs.length === 0 && (
                <div className="notif-empty">暂无通知</div>
              )}
              {notifs.map((n) => (
                <div
                  key={n.id}
                  className={`notif-item ${n.read ? '' : 'unread'}`}
                  onClick={() => !n.read && handleReadOne(n.id)}
                  role="presentation"
                >
                  <span className="notif-icon">{NOTIF_ICON[n.type]}</span>
                  <div className="notif-body">
                    <div className="notif-line">
                      <span className="notif-type">{NOTIF_TEXT[n.type]}</span>
                      <span className="notif-chain">{n.chain_title}</span>
                    </div>
                    <div className="notif-time">{formatNotifTime(n.created_at)}</div>
                  </div>
                  {!n.read && <span className="notif-unread-dot" />}
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          type="button"
          className="avatar"
          title={nickname}
          onClick={handleAvatarClick}
          aria-label="账号菜单"
        >
          {avatarText}
        </button>

        {menuOpen && token && (
          <div className="avatar-dropdown">
            <div className="avatar-user">
              <span className="avatar-name">{nickname}</span>
              <span className="avatar-username">@{user?.username}</span>
            </div>
            <button type="button" className="avatar-menu-item" onClick={handleGoProfile}>
              我的主页
            </button>
            <button type="button" className="avatar-menu-item danger" onClick={handleLogout}>
              退出登录
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

function formatNotifTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}
