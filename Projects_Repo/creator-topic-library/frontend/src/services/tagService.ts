import {
  readTags,
  readTopics,
  writeTags,
  writeTopics,
} from '../adapters/persistence/localStorageAdapter'
import type { ApiResponse } from '../types/api'
import type { StoredTag, Tag, TagDraft, TagListData } from '../types/tag'
import type { Topic } from '../types/topic'

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

function createTagId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `tag-${crypto.randomUUID()}`
  }

  return `tag-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export async function listTags(): Promise<ApiResponse<TagListData>> {
  const topics = readTopics()
  const items = readTags().map((tag) => ({
    ...tag,
    usage_count: countTagUsage(tag.id, topics),
  }))

  return {
    code: 200,
    message: 'success',
    data: {
      items,
    },
  }
}

export async function createTag(draft: TagDraft): Promise<ApiResponse<Tag | null>> {
  const name = draft.name.trim()

  if (!name) {
    return {
      code: 400,
      message: '标签名称不能为空',
      data: null,
    }
  }

  const tags = readTags()
  const duplicated = tags.some((tag) => tag.name.trim() === name)

  if (duplicated) {
    return {
      code: 400,
      message: '标签名称已存在',
      data: null,
    }
  }

  const newTag: StoredTag = {
    id: createTagId(),
    name,
    color: draft.color,
    created_at: toLocalIso(new Date()),
  }

  writeTags([...tags, newTag])

  return {
    code: 200,
    message: 'success',
    data: {
      ...newTag,
      usage_count: 0,
    },
  }
}

export async function updateTag(
  tagId: string,
  draft: TagDraft,
): Promise<ApiResponse<Tag | null>> {
  const name = draft.name.trim()

  if (!name) {
    return {
      code: 400,
      message: '标签名称不能为空',
      data: null,
    }
  }

  const tags = readTags()
  const target = tags.find((tag) => tag.id === tagId)

  if (!target) {
    return {
      code: 404,
      message: '标签不存在',
      data: null,
    }
  }

  const duplicated = tags.some((tag) => tag.id !== tagId && tag.name.trim() === name)

  if (duplicated) {
    return {
      code: 400,
      message: '标签名称已存在',
      data: null,
    }
  }

  const updatedTag: StoredTag = {
    ...target,
    name,
    color: draft.color,
  }

  writeTags(tags.map((tag) => (tag.id === tagId ? updatedTag : tag)))

  return {
    code: 200,
    message: 'success',
    data: {
      ...updatedTag,
      usage_count: countTagUsage(tagId, readTopics()),
    },
  }
}

export async function deleteTag(
  tagId: string,
): Promise<ApiResponse<{ deleted: boolean } | null>> {
  const tags = readTags()

  if (!tags.some((tag) => tag.id === tagId)) {
    return {
      code: 404,
      message: '标签不存在',
      data: null,
    }
  }

  writeTags(tags.filter((tag) => tag.id !== tagId))

  const topics = readTopics()
  writeTopics(
    topics.map((topic) => ({
      ...topic,
      tag_ids: topic.tag_ids.filter((id) => id !== tagId),
    })),
  )

  return {
    code: 200,
    message: 'success',
    data: {
      deleted: true,
    },
  }
}

function countTagUsage(tagId: string, topics: Topic[]): number {
  return topics.reduce(
    (count, topic) => (topic.tag_ids.includes(tagId) ? count + 1 : count),
    0,
  )
}
