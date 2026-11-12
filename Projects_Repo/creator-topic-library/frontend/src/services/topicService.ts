import { readTopics, writeTopics } from '../adapters/persistence/localStorageAdapter'
import type { ApiResponse } from '../types/api'
import type { Topic, TopicDraft, TopicListData } from '../types/topic'

function toLocalIso(value: Date): string {
  const pad = (part: number) => String(part).padStart(2, '0')
  const offsetMinutes = -value.getTimezoneOffset()
  const offsetSign = offsetMinutes >= 0 ? '+' : '-'
  const offsetHours = Math.floor(Math.abs(offsetMinutes) / 60)
  const offsetRemainder = Math.abs(offsetMinutes) % 60

  return [
    `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`,
    `T${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`,
    `${offsetSign}${pad(offsetHours)}:${pad(offsetRemainder)}`,
  ].join('')
}

function createId(prefix: 'topic' | 'tag'): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export async function listTopics(): Promise<ApiResponse<TopicListData>> {
  const items = readTopics().sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  )

  return {
    code: 200,
    message: 'success',
    data: {
      items,
      total: items.length,
      page: 1,
      page_size: 20,
    },
  }
}

export async function createTopic(draft: TopicDraft): Promise<ApiResponse<Topic | null>> {
  const title = draft.title.trim()

  if (!title) {
    return {
      code: 400,
      message: '标题不能为空',
      data: null,
    }
  }

  const now = new Date()
  const nowIso = toLocalIso(now)
  const newTopic: Topic = {
    ...draft,
    id: createId('topic'),
    title,
    notes: draft.notes ?? '',
    source: draft.source ?? '',
    tag_ids: draft.tag_ids ?? [],
    status: draft.status ?? 'pending',
    priority: draft.priority ?? 'medium',
    created_at: nowIso,
    updated_at: nowIso,
  }
  const topics = readTopics()

  writeTopics([newTopic, ...topics])

  return {
    code: 200,
    message: 'success',
    data: newTopic,
  }
}

export async function deleteTopic(
  topicId: string,
): Promise<ApiResponse<{ deleted: boolean } | null>> {
  const topics = readTopics()
  const target = topics.find((topic) => topic.id === topicId)

  if (!target) {
    return {
      code: 404,
      message: '选题不存在',
      data: null,
    }
  }

  writeTopics(topics.filter((topic) => topic.id !== topicId))

  return {
    code: 200,
    message: 'success',
    data: {
      deleted: true,
    },
  }
}

export async function updateTopic(
  topicId: string,
  draft: TopicDraft,
): Promise<ApiResponse<Topic | null>> {
  const topics = readTopics()
  const targetIndex = topics.findIndex((topic) => topic.id === topicId)

  if (targetIndex === -1) {
    return {
      code: 404,
      message: '选题不存在',
      data: null,
    }
  }

  const updatedTopic: Topic = {
    ...topics[targetIndex],
    ...draft,
    updated_at: toLocalIso(new Date()),
  }
  const nextTopics = [...topics]
  nextTopics[targetIndex] = updatedTopic
  writeTopics(nextTopics)

  return {
    code: 200,
    message: 'success',
    data: updatedTopic,
  }
}
