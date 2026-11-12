import { seedTags, seedTopics } from '../../mocks/library'
import type { StoredTag } from '../../types/tag'
import type { Topic } from '../../types/topic'

const TOPICS_STORAGE_KEY = 'creator-topic-library.topics.v1'
const TAGS_STORAGE_KEY = 'creator-topic-library.tags.v1'

function readJson<T>(key: string, fallback: T): T {
  const rawValue = localStorage.getItem(key)

  if (rawValue === null) {
    return fallback
  }

  try {
    return JSON.parse(rawValue) as T
  } catch {
    return fallback
  }
}

function writeJson<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value))
}

function ensureSeeded(): void {
  if (localStorage.getItem(TOPICS_STORAGE_KEY) === null) {
    writeJson(TOPICS_STORAGE_KEY, seedTopics)
  }

  if (localStorage.getItem(TAGS_STORAGE_KEY) === null) {
    writeJson(TAGS_STORAGE_KEY, seedTags)
  }
}

export function readTopics(): Topic[] {
  ensureSeeded()
  return readJson(TOPICS_STORAGE_KEY, seedTopics)
}

export function writeTopics(topics: Topic[]): void {
  writeJson(TOPICS_STORAGE_KEY, topics)
}

export function readTags(): StoredTag[] {
  ensureSeeded()
  return readJson(TAGS_STORAGE_KEY, seedTags)
}

export function writeTags(tags: StoredTag[]): void {
  writeJson(TAGS_STORAGE_KEY, tags)
}
