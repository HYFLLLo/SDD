import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button, message } from 'antd'
import { getWorkDetail } from '../services/works'
import type { WorkDetail, WorkNode } from '../types'
import './WorkDetailPage.css'

/**
 * P06 作品详情页（只读全链）。
 * 整链纵向展示（画→述→画→…），每节点作者署名，AI续标注冷灰蓝。
 * 调用真实 GET /api/works/{id}，画作节点显示真实图片（content_url）。
 */
export default function WorkDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [work, setWork] = useState<WorkDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    let active = true
    getWorkDetail(id)
      .then((res) => {
        if (active && res.data) setWork(res.data)
      })
      .catch(() => {
        if (active) message.error('加载作品失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [id])

  const handleShare = () => {
    const url = `${window.location.origin}/work/${id}`
    navigator.clipboard?.writeText(url)
    message.success('只读分享链接已复制')
  }

  if (loading) {
    return (
      <div className="work-detail">
        <div className="empty">
          <div className="emoji-art">🎨</div>
          <p>加载中…</p>
        </div>
      </div>
    )
  }

  if (!work) {
    return (
      <div className="work-detail">
        <div className="empty">
          <div className="emoji-art">🔍</div>
          <p>作品不存在</p>
        </div>
      </div>
    )
  }

  return (
    <div className="work-detail">
      {/* 头部 */}
      <div className="detail-head">
        <div>
          <h1 className="title">{work.title}</h1>
          <div className="meta">
            {work.chain_length} 节点 · 创建者 {work.creator.nickname} ·{' '}
            {work.prompt_source === 'ai' ? 'AI 起手' : '手动起手'}
          </div>
          <div className="prompt-row">
            起手题：
            <span className="handwritten prompt-text">「{work.prompt_text}」</span>
          </div>
        </div>
        <div className="head-actions">
          <Button onClick={handleShare} className="btn-ghost share-btn">
            分享链接
          </Button>
          <Link
            to={`/work/${work.id}/replay`}
            className="btn btn-primary replay-btn"
          >
            看回放
          </Link>
        </div>
      </div>

      {/* 全链纵向展示 */}
      <div className="chain-list">
        {work.nodes.map((node, i) => (
          <ChainNodeCard key={node.id} node={node} index={i} isLast={i === work.nodes.length - 1} />
        ))}
      </div>
    </div>
  )
}

/** 单个节点卡（纵向流） */
function ChainNodeCard({
  node,
  index,
  isLast,
}: {
  node: WorkNode
  index: number
  isLast: boolean
}) {
  const isDraw = node.type === 'draw'
  return (
    <div className={`node-card ${node.is_ai ? 'ai-node' : ''}`}>
      {/* 序号 + 署名 */}
      <div className="node-meta">
        <span className="node-seq">第 {index + 1} 棒</span>
        <span className="node-type">{isDraw ? '画' : '述'}</span>
        <span className="node-author">{node.author.nickname}</span>
        {node.is_ai && <span className="ai-tag">AI 续</span>}
      </div>

      {/* 节点内容 */}
      <div className="node-content">
        {node.content_type === 'image' ? (
          <div className="node-image">
            {node.content_url ? (
              <img
                className="node-img"
                src={node.content_url}
                alt={`第${index + 1}棒画作`}
                loading="lazy"
              />
            ) : (
              <div className="thumb-placeholder">
                <span className="thumb-char handwritten">🎨</span>
              </div>
            )}
          </div>
        ) : (
          <div className="node-text handwritten">「{node.content_text}」</div>
        )}
      </div>

      {/* 连接线（非最后节点） */}
      {!isLast && <div className={`node-connector ${node.is_ai ? 'ai' : ''}`} />}
    </div>
  )
}
