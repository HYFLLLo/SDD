/** WebSocket 消息（api-contracts.md WS 接口） */

/** 客户端 → 服务端：订阅 */
export interface WsSubscribeMessage {
  type: 'subscribe'
  chain_id: string
}

/** 客户端 → 服务端：推送笔迹 */
export interface WsStrokeMessage {
  type: 'stroke'
  chain_id: string
  node_id: string
  points: { x: number; y: number; pressure: number }[]
  color: string
  size: number
}

/** 服务端 → 客户端：订阅确认 */
export interface WsSubscribedMessage {
  type: 'subscribed'
  chain_id: string
}

/** 服务端 → 客户端：笔迹事件 */
export interface WsStrokeEvent {
  type: 'stroke'
  chain_id: string
  node_id: string
  points: { x: number; y: number; pressure: number }[]
  color: string
  size: number
}

/** 服务端 → 客户端：通知事件 */
export interface WsNotifyEvent {
  type: 'notify'
  event: 'your_turn' | 'chain_done' | 'node_submitted' | 'ai_filled'
  chain_id: string
  node_seq: number
}

/** 服务端 → 客户端：错误 */
export interface WsErrorEvent {
  type: 'error'
  message: string
}

export type WsServerMessage = WsSubscribedMessage | WsStrokeEvent | WsNotifyEvent | WsErrorEvent
export type WsClientMessage = WsSubscribeMessage | WsStrokeMessage
