import type { WsClientMessage, WsServerMessage } from '../types'
import { useAuthStore } from '../stores/useAuthStore'

/**
 * WebSocket 封装：使用相对路径 /ws（经 Vite 代理转发到后端），
 * 禁止硬编码 ws://localhost:<port>。
 * 鉴权用 query param ?token=JWT（浏览器 WS 不能设自定义 header）。
 */
export class RoomSocket {
  private ws: WebSocket | null = null
  private chainId: string
  private onMessage: (msg: WsServerMessage) => void
  private onOpen?: () => void
  private onClose?: () => void
  private onError?: (err: Event) => void

  constructor(
    chainId: string,
    handlers: {
      onMessage: (msg: WsServerMessage) => void
      onOpen?: () => void
      onClose?: () => void
      onError?: (err: Event) => void
    },
  ) {
    this.chainId = chainId
    this.onMessage = handlers.onMessage
    this.onOpen = handlers.onOpen
    this.onClose = handlers.onClose
    this.onError = handlers.onError
  }

  connect() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const token = useAuthStore.getState().token || ''
    const url = `${proto}://${window.location.host}/ws/room/${this.chainId}?token=${encodeURIComponent(token)}`
    this.ws = new WebSocket(url)
    this.ws.onopen = () => {
      this.send({ type: 'subscribe', chain_id: this.chainId })
      this.onOpen?.()
    }
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsServerMessage
        this.onMessage(data)
      } catch {
        // 忽略非 JSON 消息
      }
    }
    this.ws.onclose = () => this.onClose?.()
    this.ws.onerror = (err) => this.onError?.(err)
  }

  send(msg: WsClientMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  close() {
    this.ws?.close()
    this.ws = null
  }
}

/** 便捷工厂：创建并连接房间 socket */
export function connectRoomSocket(
  chainId: string,
  handlers: {
    onMessage: (msg: WsServerMessage) => void
    onOpen?: () => void
    onClose?: () => void
    onError?: (err: Event) => void
  },
) {
  const socket = new RoomSocket(chainId, handlers)
  socket.connect()
  return socket
}
