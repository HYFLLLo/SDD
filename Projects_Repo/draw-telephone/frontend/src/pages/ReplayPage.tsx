import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button, message } from 'antd'
import { getWorkDetail } from '../services/works'
import { submitVotes, getVoteResult } from '../services/votes'
import type { WorkDetail, WorkNode } from '../types'
import type { VoteDimension, VoteResultDetail } from '../types'
import './ReplayPage.css'

/** 三维度配置 */
const DIMENSIONS: { key: VoteDimension; label: string; emoji: string }[] = [
  { key: 'most_drift', label: '最跑偏', emoji: '🌀' },
  { key: 'best_draw', label: '最佳画', emoji: '🎨' },
  { key: 'best_describe', label: '最佳描述', emoji: '✍️' },
]

/** 每节点渐显间隔（ms）—— 验收要求约 2s */
const NODE_INTERVAL = 2000

/**
 * P07 整链回放页（含投票）。
 * 逐节点渐显回放（framer-motion，每节点 2s 间隔），回放后投票面板（三维度单选），
 * 提交后展示投票结果。调用真实 GET /api/works/{id}、POST /api/chains/{id}/votes、
 * GET /api/chains/{id}/votes/result，画作节点显示真实图片（content_url）。
 */
export default function ReplayPage() {
  const { id } = useParams<{ id: string }>()
  const [work, setWork] = useState<WorkDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [revealed, setRevealed] = useState(0)

  // 投票状态
  const [selections, setSelections] = useState<Record<VoteDimension, string>>({
    most_drift: '',
    best_draw: '',
    best_describe: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<VoteResultDetail | null>(null)
  const [resultLoading, setResultLoading] = useState(false)

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

  // 逐节点渐显定时器（2s 间隔）
  const nodeCount = work?.nodes.length ?? 0
  useEffect(() => {
    if (!work || revealed >= nodeCount) return
    const timer = window.setTimeout(() => {
      setRevealed((r) => Math.min(r + 1, nodeCount))
    }, NODE_INTERVAL)
    return () => window.clearTimeout(timer)
  }, [work, revealed, nodeCount])

  const replayDone = work ? revealed >= nodeCount : false

  const handleReplay = () => {
    setRevealed(0)
    setResult(null)
    setSelections({ most_drift: '', best_draw: '', best_describe: '' })
  }

  const handleSkip = () => {
    setRevealed(nodeCount)
  }

  const handleSelect = (dim: VoteDimension, nodeId: string) => {
    setSelections((prev) => ({ ...prev, [dim]: prev[dim] === nodeId ? '' : nodeId }))
  }

  const allSelected = useMemo(
    () => DIMENSIONS.every((d) => selections[d.key]),
    [selections],
  )

  const handleSubmit = () => {
    if (!id || !allSelected) return
    setSubmitting(true)
    const votes = DIMENSIONS.map((d) => ({
      dimension: d.key,
      target_node_id: selections[d.key],
    }))
    submitVotes(id, { votes })
      .then(() => {
        message.success('投票提交成功')
        setResultLoading(true)
        return getVoteResult(id)
      })
      .then((res) => {
        if (res.data) setResult(res.data)
      })
      .catch(() => {
        message.error('投票提交失败')
      })
      .finally(() => {
        setSubmitting(false)
        setResultLoading(false)
      })
  }

  if (loading) {
    return (
      <div className="replay-page">
        <div className="empty">
          <div className="emoji-art">🎬</div>
          <p>加载中…</p>
        </div>
      </div>
    )
  }

  if (!work) {
    return (
      <div className="replay-page">
        <div className="empty">
          <div className="emoji-art">🔍</div>
          <p>作品不存在</p>
        </div>
      </div>
    )
  }

  return (
    <div className="replay-page">
      {/* 头部 */}
      <div className="replay-head">
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

      {/* 回放控制条 */}
      <div className="replay-controls">
        <button className="btn" onClick={handleReplay} type="button">
          ↻ 重新回放
        </button>
        {!replayDone && (
          <button className="btn primary" onClick={handleSkip} type="button">
            ⏭ 跳过动画
          </button>
        )}
        <span className="progress">
          进度 <b>{revealed}</b> / {nodeCount}
        </span>
      </div>

      {/* 回放节点序列 */}
      <div className="replay-sequence">
        {work.nodes.slice(0, revealed).map((node, i) => (
          <ReplayNodeItem
            key={node.id}
            node={node}
            index={i}
            isLast={i === nodeCount - 1}
          />
        ))}
      </div>

      {/* 回放完成后：投票面板 / 投票结果 */}
      {replayDone && !result && (
        <VotePanel
          nodes={work.nodes}
          selections={selections}
          onSelect={handleSelect}
          onSubmit={handleSubmit}
          submitting={submitting}
          allSelected={allSelected}
        />
      )}

      {replayDone && result && <VoteResultView result={result} nodes={work.nodes} />}
      {replayDone && resultLoading && !result && (
        <div className="empty">
          <div className="emoji-art">📊</div>
          <p>加载投票结果…</p>
        </div>
      )}
    </div>
  )
}

/** 单个回放节点（framer-motion 渐显） */
function ReplayNodeItem({
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
    <>
      <motion.div
        className={`replay-node ${node.is_ai ? 'ai-node' : ''}`}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      >
        <div className="replay-node-meta">
          <span className="seq">第 {index + 1} 棒</span>
          <span className="type">{isDraw ? '画' : '述'}</span>
          <span className="author">{node.author.nickname}</span>
          {node.is_ai && <span className="ai-tag">AI 续</span>}
        </div>
        <div className="replay-node-content">
          {node.content_type === 'image' ? (
            <div className="replay-node-image">
              {node.content_url ? (
                <img
                  className="replay-node-img"
                  src={node.content_url}
                  alt={`第${index + 1}棒画作`}
                  loading="lazy"
                />
              ) : (
                <div className="replay-thumb">
                  <span className="thumb-char handwritten">🎨</span>
                </div>
              )}
            </div>
          ) : (
            <div className="replay-node-text handwritten">「{node.content_text}」</div>
          )}
        </div>
      </motion.div>
      {!isLast && <div className={`replay-connector ${node.is_ai ? 'ai' : ''}`} />}
    </>
  )
}

/** 投票面板（三维度单选） */
function VotePanel({
  nodes,
  selections,
  onSelect,
  onSubmit,
  submitting,
  allSelected,
}: {
  nodes: WorkNode[]
  selections: Record<VoteDimension, string>
  onSelect: (dim: VoteDimension, nodeId: string) => void
  onSubmit: () => void
  submitting: boolean
  allSelected: boolean
}) {
  return (
    <div className="vote-panel">
      <h3>🗳 为这条链投票</h3>
      <div className="hint">三个维度各投一票，选出你心目中的最佳</div>
      {DIMENSIONS.map((dim) => (
        <div className="vote-dim" key={dim.key}>
          <div className="vote-dim-title">
            <span className="dim-emoji">{dim.emoji}</span>
            {dim.label}
          </div>
          <div className="vote-opts">
            {nodes.map((n) => (
              <button
                key={n.id}
                className={`vote-opt ${selections[dim.key] === n.id ? 'selected' : ''}`}
                onClick={() => onSelect(dim.key, n.id)}
                type="button"
              >
                <span className="opt-type">{n.type === 'draw' ? '画' : '述'}</span>
                {n.author.nickname}
              </button>
            ))}
          </div>
        </div>
      ))}
      <div className="vote-submit-row">
        <Button
          className="btn-primary"
          onClick={onSubmit}
          disabled={!allSelected || submitting}
          loading={submitting}
        >
          提交投票
        </Button>
      </div>
    </div>
  )
}

/** 投票结果展示 */
function VoteResultView({
  result,
  nodes,
}: {
  result: VoteResultDetail
  nodes: WorkNode[]
}) {
  const maxVotes = Math.max(...result.results.map((r) => r.vote_count), 1)
  return (
    <div className="vote-result">
      <h3>📊 投票结果</h3>
      {result.results.map((r) => {
        const dim = DIMENSIONS.find((d) => d.key === r.dimension)
        const node = nodes.find((n) => n.id === r.target_node_id)
        return (
          <div className="result-dim" key={r.dimension}>
            <div className="result-dim-head">
              <span className="result-dim-name">
                {dim?.emoji} {dim?.label}
              </span>
              <span className="result-winner">
                🏆 <span className="winner-name">{r.target_author.nickname}</span>
              </span>
            </div>
            <div className="result-bar">
              <div
                className="result-bar-fill"
                style={{ width: `${(r.vote_count / maxVotes) * 100}%` }}
              />
            </div>
            <div className="result-votes">
              {r.vote_count} 票
              {node ? ` · 第 ${node.seq + 1} 棒（${node.type === 'draw' ? '画' : '述'}）` : ''}
            </div>
          </div>
        )
      })}
    </div>
  )
}
