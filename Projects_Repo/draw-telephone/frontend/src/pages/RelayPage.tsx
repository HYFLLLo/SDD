import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, message } from 'antd'
import { getNodePrevious, submitNode } from '../services/nodes'
import { uploadImage } from '../services/upload'
import { aiAssist } from '../services/ai'
import { connectRoomSocket, type RoomSocket } from '../services/ws'
import type { NodePrevious, WsServerMessage } from '../types'
import './RelayPage.css'

const CANVAS_W = 600
const CANVAS_H = 400
const MAX_TEXT = 30
const STROKE_FLUSH_INTERVAL = 200 // 笔迹推送节流间隔（ms）

const COLORS = ['#2B2622', '#C8643C', '#6B7A8F', '#5B8C5A', '#B8A890']
const SIZES = [2, 4, 8, 12]

interface StrokeSeg {
  x: number
  y: number
}

/**
 * P05 接力作画/描述页。
 * 上一节点展示区（只看上一节点防剧透）+ 画布涂鸦（canvas 2D + pointer）+
 * 文字描述输入（述节点 ≤30字）+ 提交。
 * VITE_USE_MOCK=false 时调用真实后端 GET /api/nodes/{id}/previous、POST /api/nodes/{id}/submit、POST /api/upload/image。
 * 画节点作画时通过 WebSocket /ws/room/{chain_id} 推送 stroke 笔迹（围观者实时看到）。
 */
export default function RelayPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [previous, setPrevious] = useState<NodePrevious | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  // 画布状态
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null)
  const [color, setColor] = useState(COLORS[0])
  const [size, setSize] = useState(SIZES[1])
  const [eraser, setEraser] = useState(false)
  const drawing = useRef(false)
  const strokesRef = useRef<StrokeSeg[][]>([])
  const currentStroke = useRef<StrokeSeg[]>([])
  const redoStack = useRef<StrokeSeg[][]>([])

  // WebSocket 连接（推送 stroke 笔迹给围观者）
  const socketRef = useRef<RoomSocket | null>(null)
  const lastFlushRef = useRef<number>(0)

  // 描述状态
  const [describeText, setDescribeText] = useState('')

  // AI 辅助状态
  const [aiLoading, setAiLoading] = useState(false)
  const [aiImageUrl, setAiImageUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let active = true
    getNodePrevious(id)
      .then((res) => {
        if (active && res.data) setPrevious(res.data)
      })
      .catch(() => {
        if (active) message.error('加载上一节点失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [id])

  // 建立 WebSocket 连接（画节点作画时推送 stroke 给围观者）
  useEffect(() => {
    if (!id || !previous) return
    const socket = connectRoomSocket(id, {
      onMessage: (msg: WsServerMessage) => {
        // 接力页主要角色是作画者推送，notify 事件由链大厅页处理
        // 此处监听是为了连接保活 + 提交后下一位接力时收到提示
        if (msg.type === 'notify' && msg.event === 'your_turn') {
          message.info('轮到你了！')
        }
      },
    })
    socketRef.current = socket
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [id, previous])

  const isDrawMode = previous?.content_type === 'text'

  const drawStroke = (ctx: CanvasRenderingContext2D, stroke: StrokeSeg[]) => {
    if (stroke.length < 2) {
      if (stroke.length === 1) {
        ctx.beginPath()
        ctx.arc(stroke[0].x, stroke[0].y, ctx.lineWidth / 2, 0, Math.PI * 2)
        ctx.fillStyle = ctx.strokeStyle
        ctx.fill()
      }
      return
    }
    ctx.beginPath()
    ctx.moveTo(stroke[0].x, stroke[0].y)
    for (let i = 1; i < stroke.length; i++) {
      ctx.lineTo(stroke[i].x, stroke[i].y)
    }
    ctx.stroke()
  }

  const redraw = () => {
    const ctx = ctxRef.current
    if (!ctx) return
    ctx.fillStyle = '#FFFBF3'
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)
    strokesRef.current.forEach((stroke) => {
      drawStroke(ctx, stroke)
    })
  }

  // 初始化 canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctxRef.current = ctx
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    redraw()
  }, [previous])

  const getPos = (e: React.PointerEvent): StrokeSeg => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    }
  }

  const startDraw = (e: React.PointerEvent) => {
    if (!isDrawMode) return
    e.preventDefault()
    drawing.current = true
    currentStroke.current = [getPos(e)]
    redoStack.current = []
    canvasRef.current?.setPointerCapture(e.pointerId)
  }

  const draw = (e: React.PointerEvent) => {
    if (!drawing.current || !isDrawMode) return
    const ctx = ctxRef.current
    if (!ctx) return
    const pos = getPos(e)
    currentStroke.current.push(pos)
    ctx.strokeStyle = eraser ? '#FFFBF3' : color
    ctx.fillStyle = eraser ? '#FFFBF3' : color
    ctx.lineWidth = eraser ? size * 3 : size
    // 增量绘制最后一段
    const stroke = currentStroke.current
    if (stroke.length >= 2) {
      ctx.beginPath()
      ctx.moveTo(stroke[stroke.length - 2].x, stroke[stroke.length - 2].y)
      ctx.lineTo(pos.x, pos.y)
      ctx.stroke()
    }
    // 推送 stroke 笔迹给围观者（节流，避免高频）
    flushStroke()
  }

  /** 节流推送当前笔迹给围观者（通过 WebSocket） */
  const flushStroke = () => {
    if (!id || !previous) return
    const now = Date.now()
    if (now - lastFlushRef.current < STROKE_FLUSH_INTERVAL) return
    lastFlushRef.current = now
    const points = currentStroke.current.map((p) => ({
      x: p.x,
      y: p.y,
      pressure: 0.5,
    }))
    if (points.length === 0) return
    socketRef.current?.send({
      type: 'stroke',
      chain_id: id,
      node_id: previous.node_id,
      points,
      color,
      size,
    })
  }

  const endDraw = (e: React.PointerEvent) => {
    if (!drawing.current) return
    drawing.current = false
    if (currentStroke.current.length > 0) {
      strokesRef.current.push([...currentStroke.current])
    }
    currentStroke.current = []
    canvasRef.current?.releasePointerCapture(e.pointerId)
  }

  const handleUndo = () => {
    if (strokesRef.current.length === 0) return
    redoStack.current.push(strokesRef.current.pop()!)
    redraw()
  }

  const handleRedo = () => {
    if (redoStack.current.length === 0) return
    strokesRef.current.push(redoStack.current.pop()!)
    redraw()
  }

  const handleClear = () => {
    strokesRef.current = []
    redoStack.current = []
    redraw()
  }

  const handleAiAssist = async () => {
    if (!id) return
    setAiLoading(true)
    try {
      const res = await aiAssist({ chain_id: id })
      if (!res.data) return
      if (isDrawMode && res.data.content_type === 'image' && res.data.content_url) {
        // 画节点：把 AI 生成的图贴到画布上（用户可继续涂鸦或直接提交）
        setAiImageUrl(res.data.content_url)
        const ctx = ctxRef.current
        const canvas = canvasRef.current
        if (!ctx || !canvas) return
        const img = new Image()
        img.crossOrigin = 'anonymous'
        img.onload = () => {
          ctx.fillStyle = '#FFFBF3'
          ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)
          // 等比缩放居中贴图
          const scale = Math.min(CANVAS_W / img.width, CANVAS_H / img.height)
          const w = img.width * scale
          const h = img.height * scale
          ctx.drawImage(img, (CANVAS_W - w) / 2, (CANVAS_H - h) / 2, w, h)
          strokesRef.current = [] // 清空手绘笔迹（AI 图为底）
          message.success('AI 已生成画作，可继续涂鸦或直接提交')
        }
        img.onerror = () => {
          message.error('AI 图片加载失败，可手绘提交')
        }
        img.src = res.data.content_url
      } else if (!isDrawMode && res.data.content_type === 'text' && res.data.content_text) {
        // 述节点：AI 生成的描述填入输入框
        setDescribeText(res.data.content_text)
        message.success('AI 已生成描述，可编辑后提交')
      }
    } catch {
      message.error('AI 辅助失败，请稍后重试')
    } finally {
      setAiLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!id || !previous) return
    setSubmitting(true)
    try {
      if (isDrawMode) {
        // 画节点：有 AI 图直接用其 URL；否则 canvas 导出 PNG → 上传 → 提交
        let imageUrl: string
        if (aiImageUrl) {
          imageUrl = aiImageUrl
        } else {
          const canvas = canvasRef.current!
          const blob = await new Promise<Blob | null>((resolve) =>
            canvas.toBlob(resolve, 'image/png'),
          )
          if (!blob) {
            message.error('画作导出失败')
            setSubmitting(false)
            return
          }
          const file = new File([blob], 'drawing.png', { type: 'image/png' })
          const uploadRes = await uploadImage(file)
          imageUrl = uploadRes.data.url
        }
        await submitNode(id, {
          content_type: 'image',
          content_url: imageUrl,
        })
      } else {
        // 述节点：提交文字
        if (!describeText.trim()) {
          message.warning('请输入描述')
          setSubmitting(false)
          return
        }
        await submitNode(id, {
          content_type: 'text',
          content_text: describeText.trim(),
        })
      }
      message.success('提交成功！')
      navigate(`/chain/${id}`, { replace: true })
    } catch {
      message.error('提交失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="relay-page">
        <div className="empty">
          <div className="emoji-art">🎨</div>
          <p>加载中…</p>
        </div>
      </div>
    )
  }

  if (!previous) {
    return (
      <div className="relay-page">
        <div className="empty">
          <div className="emoji-art">🔍</div>
          <p>无法获取上一节点</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relay-page">
      <div className="relay-head">
        <h1>接力 · 第 {previous.seq + 1} 棒</h1>
        <p className="desc">
          {isDrawMode ? '看上一棒的描述，画出你的理解' : '看上一棒的画，用文字描述它'}
        </p>
      </div>

      {/* 上一节点展示区（防剧透，只看上一节点） */}
      <div className="card prev-panel">
        <h3>上一节点（第 {previous.seq} 棒 · {previous.type === 'draw' ? '画' : '述'}）</h3>
        <div className="prev-content">
          {previous.content_type === 'image' ? (
            <div className="prev-image">
              <img src={previous.content_url} alt="上一节点画作" />
            </div>
          ) : (
            <div className="prev-text handwritten">「{previous.content_text}」</div>
          )}
        </div>
      </div>

      {/* 创作区 */}
      <div className="card create-panel">
        {isDrawMode ? (
          <>
            {/* 画布工具栏 */}
            <div className="canvas-toolbar">
              <div className="tool-group">
                <span className="tool-label">色板</span>
                {COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`swatch ${color === c && !eraser ? 'active' : ''}`}
                    style={{ background: c }}
                    onClick={() => {
                      setColor(c)
                      setEraser(false)
                    }}
                    aria-label={`颜色 ${c}`}
                  />
                ))}
              </div>
              <div className="divider" />
              <div className="tool-group">
                <span className="tool-label">粗细</span>
                {SIZES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`size-btn ${size === s ? 'active' : ''}`}
                    onClick={() => setSize(s)}
                  >
                    <span
                      className="size-dot"
                      style={{ width: s + 2, height: s + 2, background: color }}
                    />
                  </button>
                ))}
              </div>
              <div className="divider" />
              <div className="tool-group">
                <button
                  type="button"
                  className={`tool-btn ${eraser ? 'active' : ''}`}
                  onClick={() => setEraser(!eraser)}
                  title="橡皮"
                >
                  🧽
                </button>
                <button
                  type="button"
                  className="tool-btn"
                  onClick={handleUndo}
                  title="撤销"
                >
                  ↶
                </button>
                <button
                  type="button"
                  className="tool-btn"
                  onClick={handleRedo}
                  title="重做"
                >
                  ↷
                </button>
                <button
                  type="button"
                  className="tool-btn"
                  onClick={handleClear}
                  title="清空"
                >
                  ✕
                </button>
              </div>
              <div className="divider" />
              <div className="tool-group">
                <button
                  type="button"
                  className="ai-btn"
                  onClick={handleAiAssist}
                  disabled={aiLoading}
                  title="让 AI 帮我画"
                >
                  <AiIcon />
                  {aiLoading ? '生成中…' : 'AI 帮我画'}
                </button>
              </div>
            </div>

            {/* 画布 */}
            <div className="canvas-area relay-canvas">
              <canvas
                ref={canvasRef}
                width={CANVAS_W}
                height={CANVAS_H}
                className="draw-canvas"
                onPointerDown={startDraw}
                onPointerMove={draw}
                onPointerUp={endDraw}
                onPointerLeave={endDraw}
              />
            </div>
          </>
        ) : (
          /* 述节点：文字描述输入 */
          <div className="describe-area">
            <label>用文字描述这幅画（≤{MAX_TEXT}字）</label>
            <textarea
              className="input describe-input"
              placeholder="例如：一只戴礼帽的猫"
              maxLength={MAX_TEXT}
              value={describeText}
              onChange={(e) => setDescribeText(e.target.value)}
              rows={3}
            />
            <div className="describe-bottom">
              <div className="char-count">
                {describeText.length} / {MAX_TEXT}
              </div>
              <button
                type="button"
                className="ai-btn"
                onClick={handleAiAssist}
                disabled={aiLoading}
                title="让 AI 帮我写"
              >
                <AiIcon />
                {aiLoading ? '生成中…' : 'AI 帮我写'}
              </button>
            </div>
          </div>
        )}

        {/* 提交按钮 */}
        <div className="submit-row">
          <Button
            type="primary"
            onClick={handleSubmit}
            loading={submitting}
            className="btn-primary btn-lg"
          >
            提交接力
          </Button>
        </div>
      </div>
    </div>
  )
}

/** AI 辅助按钮图标：闪光星标，比 emoji 更精致 */
function AiIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z" />
      <path d="M19 14l.7 1.9L21.5 17l-1.8.7L19 19.5l-.7-1.8L16.5 17l1.8-.7L19 14z" />
    </svg>
  )
}
