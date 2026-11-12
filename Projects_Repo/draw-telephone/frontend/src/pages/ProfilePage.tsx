import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { message } from 'antd'
import axios from 'axios'
import { getUserProfile, getMyWorks } from '../services/users'
import { useAuthStore } from '../stores/useAuthStore'
import type { MyWorkListItem, UserProfile } from '../types'
import './ProfilePage.css'

/**
 * P08 个人主页。
 * 个人资料（昵称、参与链数、创建链数）+ 我的作品卡片列表（与广场页样式一致）。
 * 调用真实 GET /api/users/me、GET /api/users/me/works。
 */
export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [works, setWorks] = useState<MyWorkListItem[]>([])
  const [loading, setLoading] = useState(true)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    let active = true
    Promise.all([getUserProfile(), getMyWorks()])
      .then(([pRes, wRes]) => {
        if (!active) return
        if (pRes.data) setProfile(pRes.data)
        if (wRes.data) setWorks(wRes.data.items)
      })
      .catch((err) => {
        if (!active) return
        // 401 已由拦截器统一提示「登录已过期」并触发跳转，此处不再重复报错
        if (!axios.isAxiosError(err) || err.response?.status !== 401) {
          message.error('加载个人主页失败')
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <div className="profile-page">
        <div className="empty">
          <div className="emoji-art">👤</div>
          <p>加载中…</p>
        </div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="profile-page">
        <div className="empty">
          <div className="emoji-art">🔍</div>
          <p>用户信息加载失败</p>
          <Link
            to="/login"
            className="btn btn-primary"
            onClick={() => logout()}
          >
            重新登录
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="profile-page">
      {/* 个人资料卡 */}
      <div className="profile-card">
        <div className="profile-avatar">{profile.nickname.charAt(0)}</div>
        <div className="profile-info">
          <h1 className="profile-nickname">{profile.nickname}</h1>
          <div className="profile-username">@{profile.username}</div>
          <div className="profile-stats">
            <span className="stat">
              <b>{profile.participated_chains}</b> 参与
            </span>
            <span className="stat-divider">·</span>
            <span className="stat">
              <b>{profile.created_chains}</b> 创建
            </span>
          </div>
        </div>
      </div>

      {/* 我的作品 */}
      <div className="my-works-head">
        <h2 className="section-title">我的作品</h2>
        <span className="section-count">共 {works.length} 条</span>
      </div>

      {works.length === 0 ? (
        <div className="empty">
          <div className="emoji-art">🎨</div>
          <p>还没有作品，去广场创建或加入一条链吧</p>
          <Link to="/" className="btn btn-primary">
            去广场
          </Link>
        </div>
      ) : (
        <div className="work-grid">
          {works.map((w) => (
            <MyWorkCard key={w.id} work={w} />
          ))}
        </div>
      )}
    </div>
  )
}

/** 我的作品卡片（与广场页 work-card 样式一致） */
function MyWorkCard({ work }: { work: MyWorkListItem }) {
  const statusLabel = work.status === 'completed' ? '已完成' : '进行中'
  const roleLabel = work.role === 'creator' ? '创建者' : '参与者'
  return (
    <Link to={`/work/${work.id}`} className="work-card">
      <div className="work-thumb">
        {work.thumb_url ? (
          <img
            className="thumb-img"
            src={work.thumb_url}
            alt={work.title}
            loading="lazy"
          />
        ) : (
          <div className="thumb-placeholder">
            <span className="thumb-char handwritten">{work.title.charAt(0)}</span>
          </div>
        )}
        <span className={`role-badge ${work.role}`}>{roleLabel}</span>
      </div>
      <div className="work-info">
        <div className="title">{work.title}</div>
        <div className="meta">
          <span>{work.chain_length} 节点</span>
          <span className={`status ${work.status}`}>{statusLabel}</span>
        </div>
      </div>
    </Link>
  )
}
