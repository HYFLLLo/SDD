import type { ApiResponse, PageResponse, WorkDetail, WorkListItem } from '../types'

/** 内部 Mock 实体：作品（含画作 SVG 占位图，仅用于构造 DTO，不直接返回） */
interface WorkEntity {
  id: string
  title: string
  chain_length: number
  member_count: number
  like_count: number
  thumb_url: string
  created_at: string
  prompt_source: 'manual' | 'ai'
  prompt_text: string
  status: string
  completed_at: string
  nodes: {
    id: string
    seq: number
    type: 'draw' | 'describe'
    author: { id: string; nickname: string }
    content_type: 'image' | 'text'
    content_url?: string
    content_text?: string
    is_ai: boolean
    submitted_at: string
  }[]
}

const workEntities: WorkEntity[] = [
  {
    id: 'work-0001',
    title: '戴帽子的猫',
    chain_length: 6,
    member_count: 5,
    like_count: 128,
    thumb_url: '/mock-thumbs/cat.svg',
    created_at: '2026-08-18T13:49:07Z',
    prompt_source: 'ai',
    prompt_text: '戴帽子的猫',
    status: 'completed',
    completed_at: '2026-08-19T13:49:07Z',
    nodes: [
      {
        id: 'node-0001',
        seq: 0,
        type: 'draw',
        author: { id: 'mock-uuid', nickname: '小A' },
        content_type: 'image',
        content_url: '/mock-thumbs/cat.svg',
        is_ai: false,
        submitted_at: '2026-08-18T13:49:07Z',
      },
      {
        id: 'node-0002',
        seq: 1,
        type: 'describe',
        author: { id: 'mock-uuid-b', nickname: '小B' },
        content_type: 'text',
        content_text: '一只戴礼帽的猫',
        is_ai: false,
        submitted_at: '2026-08-18T14:10:07Z',
      },
      {
        id: 'node-0003',
        seq: 2,
        type: 'draw',
        author: { id: 'mock-uuid-c', nickname: '小C' },
        content_type: 'image',
        content_url: '/mock-thumbs/cat-hat.svg',
        is_ai: false,
        submitted_at: '2026-08-18T15:02:07Z',
      },
      {
        id: 'node-0004',
        seq: 3,
        type: 'describe',
        author: { id: 'mock-uuid-d', nickname: '小D' },
        content_type: 'text',
        content_text: '猫的礼帽里飞出一只鸽子',
        is_ai: false,
        submitted_at: '2026-08-18T16:30:07Z',
      },
      {
        id: 'node-0005',
        seq: 4,
        type: 'draw',
        author: { id: 'ai-agent', nickname: 'AI 续' },
        content_type: 'image',
        content_url: '/mock-thumbs/dove.svg',
        is_ai: true,
        submitted_at: '2026-08-19T09:12:07Z',
      },
      {
        id: 'node-0006',
        seq: 5,
        type: 'describe',
        author: { id: 'mock-uuid', nickname: '小A' },
        content_type: 'text',
        content_text: '鸽子衔着月亮飞向云端',
        is_ai: false,
        submitted_at: '2026-08-19T13:49:07Z',
      },
    ],
  },
  {
    id: 'work-0002',
    title: '会飞的鱼',
    chain_length: 8,
    member_count: 6,
    like_count: 96,
    thumb_url: '/mock-thumbs/fish.svg',
    created_at: '2026-08-17T10:00:00Z',
    prompt_source: 'ai',
    prompt_text: '会飞的鱼',
    status: 'completed',
    completed_at: '2026-08-18T10:00:00Z',
    nodes: [],
  },
  {
    id: 'work-0003',
    title: '机器人',
    chain_length: 6,
    member_count: 4,
    like_count: 73,
    thumb_url: '/mock-thumbs/robot.svg',
    created_at: '2026-08-16T09:00:00Z',
    prompt_source: 'ai',
    prompt_text: '机器人',
    status: 'completed',
    completed_at: '2026-08-17T09:00:00Z',
    nodes: [],
  },
  {
    id: 'work-0004',
    title: '山与日',
    chain_length: 4,
    member_count: 4,
    like_count: 54,
    thumb_url: '/mock-thumbs/mountain.svg',
    created_at: '2026-08-15T08:00:00Z',
    prompt_source: 'ai',
    prompt_text: '山与日',
    status: 'completed',
    completed_at: '2026-08-16T08:00:00Z',
    nodes: [],
  },
  {
    id: 'work-0005',
    title: '眼睛里的海',
    chain_length: 10,
    member_count: 8,
    like_count: 211,
    thumb_url: '/mock-thumbs/eye-sea.svg',
    created_at: '2026-08-14T07:00:00Z',
    prompt_source: 'ai',
    prompt_text: '眼睛里的海',
    status: 'completed',
    completed_at: '2026-08-15T07:00:00Z',
    nodes: [],
  },
  {
    id: 'work-0006',
    title: '三棵树',
    chain_length: 6,
    member_count: 5,
    like_count: 67,
    thumb_url: '/mock-thumbs/trees.svg',
    created_at: '2026-08-13T06:00:00Z',
    prompt_source: 'ai',
    prompt_text: '三棵树',
    status: 'completed',
    completed_at: '2026-08-14T06:00:00Z',
    nodes: [],
  },
]

/** GET /api/works 列表响应（按契约显式构造 DTO） */
export const worksListResponse: ApiResponse<PageResponse<WorkListItem>> = {
  code: 200,
  message: 'success',
  data: {
    items: workEntities.map((w) => ({
      id: w.id,
      title: w.title,
      chain_length: w.chain_length,
      member_count: w.member_count,
      like_count: w.like_count,
      thumb_url: w.thumb_url,
      created_at: w.created_at,
    })),
    total: workEntities.length,
    page: 1,
    page_size: 20,
  },
}

/** GET /api/works/{id} 详情响应（按契约显式构造 DTO） */
export function buildWorkDetailResponse(id: string): ApiResponse<WorkDetail> {
  const work = workEntities.find((w) => w.id === id) ?? workEntities[0]
  return {
    code: 200,
    message: 'success',
    data: {
      id: work.id,
      title: work.title,
      chain_length: work.chain_length,
      creator: { id: work.nodes[0]?.author.id ?? 'mock-uuid', nickname: work.nodes[0]?.author.nickname ?? '小A' },
      prompt_source: work.prompt_source,
      prompt_text: work.prompt_text,
      status: work.status,
      created_at: work.created_at,
      completed_at: work.completed_at,
      nodes: work.nodes.map((n) => ({
        id: n.id,
        seq: n.seq,
        type: n.type,
        author: n.author,
        content_type: n.content_type,
        ...(n.content_url ? { content_url: n.content_url } : {}),
        ...(n.content_text ? { content_text: n.content_text } : {}),
        is_ai: n.is_ai,
        submitted_at: n.submitted_at,
      })),
    },
  }
}

/** GET /api/works/{id} 404 响应 */
export const workNotFoundResponse: ApiResponse<null> = {
  code: 404,
  message: '作品不存在',
  data: null,
}
