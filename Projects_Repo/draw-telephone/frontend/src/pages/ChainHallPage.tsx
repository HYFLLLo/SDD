import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { message } from 'antd'
import { getChainDetail } from '../services/chains'
import { connectRoomSocket, type RoomSocket } from '../services/ws'
import { useAuthStore } from '../stores/useAuthStore'
import type { ChainDetail, WsServerMessage } from '../types'
import './ChainHallPage.css'

/** 笔迹点（来自 WS stroke 事件） */
interface StrokePoint {
  x: number
  y: number
  pressure: number
}

/**
 * P04 链大厅页。
 * ★签名锚点：进度节点链（脉冲动画）。VITE_USE_MOCK=false 时调用真实后端 GET /api/chains/{id}/detail。
 * 实时围观通过真实 WebSocket /ws/room/{chain_id} 接收作画者 stroke 笔迹 + notify 通知。
 */
export default function ChainHallPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuthStore()
  const [detail, setDetail] = useState<ChainDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [strokes, setStrokes] = useState<StrokePoint[][]>([])
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const socketRef = useRef<RoomSocket | null>(null)

  useEffect(() => {
    if (!id) return
    let active = true
    getChainDetail(id)
      .then((res) => {
        if (active && res.data) setDetail(res.data)
      })
      .catch(() => {
        if (active) message.error('加载链详情失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [id])

  // 实时围观：建立 WebSocket 连接，接收 stroke 笔迹 + notify 通知
  useEffect(() => {
    if (!id || !detail || detail.status === 'completed') return
    const socket = connectRoomSocket(id, {
      onMessage: (msg: WsServerMessage) => {
        if (msg.type === 'stroke') {
          // 追加笔迹点到 canvas（按 node_id 分组为一条笔迹）
          setStrokes((prev) => {
            const idx = prev.findIndex(
              (_, i) => i === prev.length - 1 && prev[i].length < 200,
            )
            if (idx >= 0) {
              const updated = [...prev]
              updated[idx] = [...updated[idx], ...msg.points]
              return updated
            }
            return [...prev, [...msg.points]]
          })
        } else if (msg.type === 'notify') {
          // 通知事件：刷新链详情 + 提示
          getChainDetail(id)
            .then((res) => {
              if (res.data) setDetail(res.data)
            })
            .catch(() => {})
          if (msg.event === 'your_turn') {
            message.info('轮到你了！')
          } else if (msg.event === 'chain_done') {
            message.success('链已完成！')
          } else if (msg.event === 'node_submitted') {
            message.info('有新节点提交')
          }
        }
      },
    })
    socketRef.current = socket
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [id, detail])

  // canvas 重绘笔迹
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    // 画所有笔迹
    strokes.forEach((stroke) => {
      if (stroke.length === 0) return
      ctx.beginPath()
      ctx.moveTo(stroke[0].x, stroke[0].y)
      for (let i = 1; i < stroke.length; i++) {
        ctx.lineTo(stroke[i].x, stroke[i].y)
      }
      ctx.strokeStyle = '#2B2622'
      ctx.lineWidth = 2
      ctx.stroke()
    })
  }, [strokes])

  if (loading) {
    return (
      <div className="chain-hall">
        <div className="empty">
          <div className="emoji-art">🎨</div>
          <p>加载中…</p>
        </div>
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="chain-hall">
        <div className="empty">
          <div className="emoji-art">🔍</div>
          <p>链不存在或无权访问</p>
        </div>
      </div>
    )
  }

  const isCompleted = detail.status === 'completed'
  const isMyTurn = user?.id === detail.current_author.id

  // 计算倒计时（Mock：ai_countdown_at 与当前时间差）
  const countdown = detail.ai_countdown_at
    ? formatCountdown(detail.ai_countdown_at)
    : null

  const handleCopyLink = () => {
    const url = `${window.location.origin}/join?code=${detail.room_code}`
    navigator.clipboard?.writeText(url)
    message.success('邀请链接已复制')
  }

  return (
    <div className="chain-hall">
      {/* 房间头部 */}
      <div className="room-head">
        <div>
          <div className="title">{detail.title}</div>
          <div className="meta">
            链长 {detail.chain_length} 节点 ·{' '}
            {detail.visibility === 'invite' ? '邀请制' : '公开广场'} · 创建者{' '}
            {detail.members[0]?.nickname ?? '未知'}
          </div>
        </div>
        <div className="room-code">
          <span className="code">{detail.room_code}</span>
          <button type="button" onClick={handleCopyLink}>
            复制链接
          </button>
        </div>
      </div>

      {/* ★ 签名锚点：进度节点链 */}
      <div className="card panel progress-panel">
        <h3>接力进度</h3>
        <div className="chain-progress">
          {detail.nodes.map((node, i) => {
            const isDone = node.seq < detail.current_seq
            const isCurrent = node.seq === detail.current_seq
            const typeLabel = node.type === 'draw' ? '画' : '述'
            const authorLabel = isDone
              ? `${node.author.nickname}·${typeLabel}`
              : isCurrent
                ? `${node.author.nickname}·${typeLabel}`
                : `待接·${typeLabel}`
            return (
              <div key={node.seq} className="node-row">
                <div
                  className={`node-dot ${isDone ? 'done' : ''} ${isCurrent ? 'current' : ''}`}
                >
                  <div className="circle">{i + 1}</div>
                  <div className="label">{authorLabel}</div>
                </div>
                {i < detail.nodes.length - 1 && (
                  <div className={`node-link ${isDone ? 'done' : ''}`} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="room-layout">
        {/* 左侧面板 */}
        <div className="side-panel">
          {/* 成员 */}
          <div className="card panel">
            <h3>成员（{detail.members.length}）</h3>
            <div className="members">
              {detail.members.map((m) => {
                const isCurrent = m.id === detail.current_author.id
                return (
                  <div
                    key={m.id}
                    className={`member ${isCurrent ? 'current' : ''}`}
                  >
                    <div className="av">{m.nickname.charAt(0)}</div>
                    <div className="name">{m.nickname}</div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* AI 补位倒计时 */}
          {countdown && !isCompleted && (
            <div className="ai-countdown">
              <div className="icon">🤖</div>
              <div className="txt">
                <div>当前节点 AI 补位倒计时</div>
                <div className="time">{countdown}</div>
              </div>
            </div>
          )}

          {/* 链信息 */}
          <div className="card panel">
            <h3>链信息</h3>
            <div className="info-rows">
              起手题：
              <span className="handwritten prompt-text">
                「{detail.prompt_text}」
              </span>
              <br />
              起手来源：{detail.prompt_source === 'ai' ? 'AI 生成' : '手动'}
              <br />
              过期时间：{formatExpiry(detail.expires_at)}
              <br />
              状态：{isCompleted ? '已完成' : '进行中'}
            </div>
          </div>
        </div>

        {/* 右侧实时围观 */}
        <div className="card watch-area">
          <div className="watch-label">
            <div className="who">
              <b>{detail.current_author.nickname}</b> 正在
              {detail.current_node_type === 'draw' ? '画' : '写'}第{' '}
              {detail.current_seq + 1} 节点
            </div>
            <div className="live-dot">实时围观</div>
          </div>
          <div className="canvas-area watch-canvas">
            <canvas
              ref={canvasRef}
              width={200}
              height={200}
              className="watch-canvas-el"
            />
            <div className="watch-hint">
              笔迹实时推送中 · WebSocket
            </div>
          </div>

          {/* 轮到你 / 回放 */}
          <div className="your-turn">
            {isCompleted ? (
              <Link to={`/work/${detail.id}/replay`} className="btn btn-primary btn-lg">
                回放整链
              </Link>
            ) : isMyTurn ? (
              <Link
                to={`/chain/${detail.id}/relay`}
                className="btn btn-primary btn-lg"
              >
                开始接力
              </Link>
            ) : (
              <div className="waiting-hint">
                等待 {detail.current_author.nickname} 完成第{' '}
                {detail.current_seq + 1} 节点…
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/** 格式化倒计时（ai_countdown_at 与当前时间差） */
function formatCountdown(targetIso: string): string {
  const target = new Date(targetIso).getTime()
  const now = Date.now()
  const diff = Math.max(0, target - now)
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  return `${hours} 时 ${minutes} 分`
}

/** 格式化过期时间（简单显示天数差） */
function formatExpiry(expiryIso: string): string {
  const target = new Date(expiryIso).getTime()
  const now = Date.now()
  const days = Math.ceil((target - now) / 86400000)
  return days > 0 ? `${days} 天后` : '已过期'
}
