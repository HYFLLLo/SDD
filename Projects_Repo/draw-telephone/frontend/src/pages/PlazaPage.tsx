import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getWorks } from '../services/works'
import { useAuthStore } from '../stores/useAuthStore'
import type { WorkListItem } from '../types'
import './PlazaPage.css'

/**
 * P01 广场页。
 * Hero + 加入入口（房间码）+ 筛选 + 作品瀑布流。
 * 登录用户看到「创建」「加入」入口；游客看到「登录」引导。
 * 调用真实 GET /api/works，缩略图取链首张画作（thumb_url）。
 */
export default function PlazaPage() {
  const navigate = useNavigate()
  const { token } = useAuthStore()
  const [works, setWorks] = useState<WorkListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [roomCode, setRoomCode] = useState('')
  const [sort, setSort] = useState<'latest' | 'most_drift' | 'most_liked'>('latest')

  useEffect(() => {
    let active = true
    getWorks({ page: 1, page_size: 20, sort })
      .then((res) => {
        if (active && res.data) {
          setWorks(res.data.items)
        }
      })
      .catch(() => {
        // Mock 阶段不应失败；保持空列表
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [sort])

  const handleJoin = () => {
    if (roomCode.trim()) {
      navigate(`/join?code=${roomCode.trim()}`)
    }
  }

  return (
    <div className="plaza">
      {/* Hero */}
      <div className="hero">
        <span className="hero-deco left handwritten" aria-hidden="true">
          ~
        </span>
        <span className="hero-deco right handwritten" aria-hidden="true">
          ✦
        </span>
        <div className="hero-prompt handwritten">「戴帽子的猫」</div>
        <div className="hero-tagline">一条画 · 一条述 · 看一幅画如何跑偏</div>
        <div className="hero-cta">
          {token ? (
            <Link to="/create" className="btn btn-primary btn-lg">
              开始一条链
            </Link>
          ) : (
            <Link to="/login" className="btn btn-primary btn-lg">
              登录后开始
            </Link>
          )}
        </div>
      </div>

      {/* 加入入口 */}
      <div className="join-bar">
        <input
          className="input"
          placeholder="输入 6 位房间码加入接力"
          maxLength={6}
          value={roomCode}
          onChange={(e) => setRoomCode(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
        />
        <button
          type="button"
          className="btn btn-ghost"
          onClick={handleJoin}
          disabled={!roomCode.trim()}
        >
          加入
        </button>
      </div>

      {/* 筛选 */}
      <div className="filters">
        <button
          type="button"
          className={`filter-chip ${sort === 'latest' ? 'active' : ''}`}
          onClick={() => setSort('latest')}
        >
          最新
        </button>
        <button
          type="button"
          className={`filter-chip ${sort === 'most_drift' ? 'active' : ''}`}
          onClick={() => setSort('most_drift')}
        >
          最跑偏
        </button>
        <button
          type="button"
          className={`filter-chip ${sort === 'most_liked' ? 'active' : ''}`}
          onClick={() => setSort('most_liked')}
        >
          最多点赞
        </button>
      </div>

      {/* 作品瀑布流 */}
      {loading ? (
        <div className="empty">
          <div className="emoji-art">🎨</div>
          <p>加载中…</p>
        </div>
      ) : works.length === 0 ? (
        <div className="empty">
          <div className="emoji-art">🎨</div>
          <p>还没有作品，来画第一条吧</p>
        </div>
      ) : (
        <div className="work-grid">
          {works.map((w) => (
            <Link key={w.id} to={`/work/${w.id}`} className="work-card">
              <div className="work-thumb">
                <WorkThumb title={w.title} thumbUrl={w.thumb_url} />
              </div>
              <div className="work-info">
                <div className="title">{w.title}</div>
                <div className="meta">
                  <span>
                    {w.chain_length} 节点 · {w.member_count} 人
                  </span>
                  <span>❤ {w.like_count}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

/** 缩略图：有 thumb_url 显示真实画作，否则用首字占位 */
function WorkThumb({ title, thumbUrl }: { title: string; thumbUrl: string }) {
  if (thumbUrl) {
    return (
      <img
        className="thumb-img"
        src={thumbUrl}
        alt={title}
        loading="lazy"
      />
    )
  }
  return (
    <div className="thumb-placeholder">
      <span className="thumb-char handwritten">{title.charAt(0)}</span>
    </div>
  )
}
