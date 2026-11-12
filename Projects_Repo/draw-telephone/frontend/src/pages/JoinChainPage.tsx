import { useEffect, useRef, useState } from 'react'
import { Button, message } from 'antd'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { lookupChain, joinChain } from '../services/chains'
import type { ChainLookup } from '../types'
import './JoinChainPage.css'

const CODE_LENGTH = 6

/**
 * P03 加入链页。
 * 6 位房间码分格输入（已填陶土橙高亮）、校验按钮、邀请链接带码自动填入。
 * VITE_USE_MOCK=false 时调用真实后端 GET /api/chains/{room_code} 校验、POST /api/chains/{id}/join 加入。
 */
export default function JoinChainPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [codes, setCodes] = useState<string[]>(Array(CODE_LENGTH).fill(''))
  const [lookup, setLookup] = useState<ChainLookup | null>(null)
  const [checking, setChecking] = useState(false)
  const [joining, setJoining] = useState(false)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  // 邀请链接带码自动填入（?code=DRAW42）
  useEffect(() => {
    const code = searchParams.get('code') ?? ''
    if (code) {
      const chars = code.slice(0, CODE_LENGTH).split('')
      const next = [...Array(CODE_LENGTH).fill(''), ...chars].slice(-CODE_LENGTH)
      setCodes(next)
      // 自动校验
      if (next.every((c) => c)) {
        doLookup(next.join(''))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const handleChange = (index: number, value: string) => {
    const char = value.slice(-1).toUpperCase()
    const next = [...codes]
    next[index] = char
    setCodes(next)
    setLookup(null)
    // 自动跳到下一格
    if (char && index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !codes[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').toUpperCase().slice(0, CODE_LENGTH)
    if (pasted) {
      const next = [...Array(CODE_LENGTH).fill(''), ...pasted.split('')].slice(-CODE_LENGTH)
      setCodes(next)
      if (next.every((c) => c)) {
        doLookup(pasted)
      }
    }
  }

  const fullCode = codes.join('')

  const doLookup = async (code: string) => {
    setChecking(true)
    try {
      const res = await lookupChain(code)
      if (res.data) {
        setLookup(res.data)
      }
    } catch {
      message.error('房间码无效或链已过期')
    } finally {
      setChecking(false)
    }
  }

  const handleCheck = () => {
    if (fullCode.length !== CODE_LENGTH) {
      message.warning('请输入完整的 6 位房间码')
      return
    }
    doLookup(fullCode)
  }

  const handleJoin = async () => {
    if (!lookup) return
    setJoining(true)
    try {
      const res = await joinChain(lookup.id)
      if (res.data?.joined) {
        message.success('加入成功！')
        navigate(`/chain/${lookup.id}`)
      }
    } catch {
      message.error('链已满或已过期')
    } finally {
      setJoining(false)
    }
  }

  return (
    <div className="join-page">
      <div className="card form-card">
        <h1>加入接力</h1>
        <p className="desc">输入朋友发来的 6 位房间码</p>

        <div className="code-input" onPaste={handlePaste}>
          {codes.map((c, i) => (
            <input
              key={i}
              ref={(el) => {
                inputRefs.current[i] = el
              }}
              className={`code-box ${c ? 'filled' : ''}`}
              maxLength={1}
              value={c}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              inputMode="text"
              autoCapitalize="characters"
            />
          ))}
        </div>

        <Button
          type="primary"
          onClick={handleCheck}
          loading={checking}
          disabled={fullCode.length !== CODE_LENGTH}
          className="btn-primary btn-lg check-btn"
        >
          校验房间码
        </Button>

        {lookup && (
          <div className="chain-preview">
            <div className="row">
              <span>链标题</span>
              <span>{lookup.title}</span>
            </div>
            <div className="row">
              <span>链长</span>
              <span>{lookup.chain_length} 节点</span>
            </div>
            <div className="row">
              <span>当前进度</span>
              <span>
                第 {lookup.current_seq + 1} / {lookup.chain_length} 节点
              </span>
            </div>
            <div className="row">
              <span>剩余名额</span>
              <span>
                {lookup.is_full ? '已满' : `${lookup.remaining_slots} 人可加入`}
              </span>
            </div>
            <Button
              type="primary"
              onClick={handleJoin}
              loading={joining}
              disabled={lookup.is_full}
              className="btn-primary btn-lg join-btn"
            >
              {lookup.is_full ? '链已满' : '加入链'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
