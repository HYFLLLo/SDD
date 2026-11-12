import { useState } from 'react'
import { Button, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { createChain } from '../services/chains'
import { generatePrompts } from '../services/ai'
import './CreateChainPage.css'

type Visibility = 'invite' | 'public'
type PromptSource = 'manual' | 'ai'

/** 题词池：AI 生成未联调前作为本地 fallback（T-015 接入真实 DeepSeek 后由后端返回） */
const PROMPT_POOL = [
  '戴帽子的猫',
  '会飞的鱼',
  '山与日',
  '眼睛里的海',
  '三棵树',
  '会跳舞的灯泡',
  '吃云朵的鲸',
  '打伞的蜗牛',
]

/**
 * P02 创建链页。
 * 链长滑块（4-10 默认6）、标题输入、公开性分段、起手题来源分段、AI 题词预览+换一个、提交。
 * VITE_USE_MOCK=false 时 POST /api/chains 调用真实后端（房间码由后端生成）。
 * AI 题词预览（POST /api/ai/prompt）在 T-015 接入真实 DeepSeek，当前用本地 fallback 池。
 */
export default function CreateChainPage() {
  const navigate = useNavigate()
  const [chainLength, setChainLength] = useState(6)
  const [title, setTitle] = useState('')
  const [visibility, setVisibility] = useState<Visibility>('invite')
  const [promptSource, setPromptSource] = useState<PromptSource>('ai')
  const [promptText, setPromptText] = useState('戴帽子的猫')
  const [manualPrompt, setManualPrompt] = useState('')
  const [generating, setGenerating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [poolIdx, setPoolIdx] = useState(0)

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await generatePrompts({ count: 1 })
      // T-015 前 AI 接口可能 fallback，本地轮换池子让「换一个」有变化
      const next = (poolIdx + 1) % PROMPT_POOL.length
      setPoolIdx(next)
      const word = res.data?.prompts[0] ?? PROMPT_POOL[next]
      setPromptText(PROMPT_POOL[next] || word)
    } catch {
      message.error('AI 服务暂不可用，请手动输入题词')
    } finally {
      setGenerating(false)
    }
  }

  const handleSubmit = async () => {
    const finalPrompt =
      promptSource === 'manual' ? manualPrompt.trim() : promptText
    if (promptSource === 'manual' && !finalPrompt) {
      message.error('请输入起手题词')
      return
    }
    setSubmitting(true)
    try {
      const res = await createChain({
        title: title.trim() || undefined,
        chain_length: chainLength,
        visibility,
        prompt_source: promptSource,
        prompt_text: finalPrompt,
      })
      message.success(`创建成功！房间码：${res.data.room_code}`)
      navigate(`/chain/${res.data.id}`)
    } catch {
      message.error('创建失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="create-page">
      <div className="card form-card">
        <h1>创建一条链</h1>
        <p className="desc">设定链长和起手题，邀请朋友来接力</p>

        {/* 链长 */}
        <div className="field">
          <label>链长（画-述交替，起手为画）</label>
          <div className="slider-row">
            <input
              type="range"
              min={4}
              max={10}
              value={chainLength}
              onChange={(e) => setChainLength(Number(e.target.value))}
            />
            <span className="slider-val">{chainLength}</span>
          </div>
          <div className="hint">4-10 节点，默认 6。第 1 节点为画，之后画-述交替。</div>
        </div>

        {/* 标题 */}
        <div className="field">
          <label>标题（可选）</label>
          <input
            className="input"
            placeholder="给这条链起个名字"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        {/* 公开性 */}
        <div className="field">
          <label>公开性</label>
          <div className="seg">
            <button
              type="button"
              className={visibility === 'invite' ? 'active' : ''}
              onClick={() => setVisibility('invite')}
            >
              邀请制
            </button>
            <button
              type="button"
              className={visibility === 'public' ? 'active' : ''}
              onClick={() => setVisibility('public')}
            >
              公开广场
            </button>
          </div>
          <div className="hint">
            邀请制：仅房间码可加入。公开广场：完成后可在广场浏览。
          </div>
        </div>

        {/* 起手题来源 */}
        <div className="field">
          <label>起手题来源</label>
          <div className="seg">
            <button
              type="button"
              className={promptSource === 'manual' ? 'active' : ''}
              onClick={() => setPromptSource('manual')}
            >
              自己写题
            </button>
            <button
              type="button"
              className={promptSource === 'ai' ? 'active' : ''}
              onClick={() => setPromptSource('ai')}
            >
              AI 生成
            </button>
          </div>

          {promptSource === 'ai' ? (
            <>
              <div className="prompt-preview">
                <div className="word handwritten">「{promptText}」</div>
                <div className="sub">AI 生成 · 具象但开放，易被误读</div>
              </div>
              <button
                type="button"
                className="gen-btn"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? '生成中…' : '↻ 换一个'}
              </button>
            </>
          ) : (
            <input
              className="input"
              placeholder="输入起手题词，如「戴帽子的猫」"
              value={manualPrompt}
              onChange={(e) => setManualPrompt(e.target.value)}
            />
          )}
        </div>

        {/* 提交 */}
        <Button
          type="primary"
          loading={submitting}
          onClick={handleSubmit}
          className="btn-primary btn-lg submit-btn"
        >
          创建并生成房间码
        </Button>
      </div>
    </div>
  )
}
