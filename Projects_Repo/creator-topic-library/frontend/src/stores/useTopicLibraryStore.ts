import { create } from 'zustand'
import {
  createTag as createTagService,
  deleteTag as deleteTagService,
  listTags,
  updateTag as updateTagService,
} from '../services/tagService'
import {
  createTopic as createTopicService,
  deleteTopic as deleteTopicService,
  listTopics,
  updateTopic as updateTopicService,
} from '../services/topicService'
import type { Tag, TagDraft } from '../types/tag'
import type { Topic, TopicDraft } from '../types/topic'

type LibraryStatus = 'idle' | 'loading' | 'success' | 'error'

interface CreateTagResult {
  ok: boolean
  message: string
  tag: Tag | null
}

interface TopicLibraryState {
  topics: Topic[]
  tags: Tag[]
  status: LibraryStatus
  errorMessage: string | null
  loadLibrary: () => Promise<void>
  createTopic: (draft: TopicDraft) => Promise<boolean>
  createTag: (draft: TagDraft) => Promise<CreateTagResult>
  deleteTag: (tagId: string) => Promise<boolean>
  deleteTopic: (topicId: string) => Promise<boolean>
  updateTag: (tagId: string, draft: TagDraft) => Promise<CreateTagResult>
  updateTopic: (topicId: string, draft: TopicDraft) => Promise<boolean>
}

export const useTopicLibraryStore = create<TopicLibraryState>((set) => ({
  topics: [],
  tags: [],
  status: 'idle',
  errorMessage: null,
  loadLibrary: async () => {
    set({ status: 'loading', errorMessage: null })

    const [topicResponse, tagResponse] = await Promise.all([listTopics(), listTags()])

    if (topicResponse.code !== 200 || tagResponse.code !== 200) {
      set({
        status: 'error',
        errorMessage: topicResponse.message || tagResponse.message || '本地数据加载失败',
      })
      return
    }

    set({
      topics: topicResponse.data.items,
      tags: tagResponse.data.items,
      status: 'success',
    })
  },
  createTopic: async (draft) => {
    const response = await createTopicService(draft)

    if (response.code !== 200 || !response.data) {
      set({
        errorMessage: response.message,
      })
      return false
    }

    set((state) => ({
      topics: [response.data as Topic, ...state.topics],
    }))

    return true
  },
  createTag: async (draft) => {
    const response = await createTagService(draft)

    if (response.code !== 200 || !response.data) {
      return {
        ok: false,
        message: response.message,
        tag: null,
      }
    }

    set((state) => ({
      tags: [...state.tags, response.data as Tag],
    }))

    return {
      ok: true,
      message: 'success',
      tag: response.data,
    }
  },
  deleteTag: async (tagId) => {
    const response = await deleteTagService(tagId)

    if (response.code !== 200) {
      set({
        errorMessage: response.message,
      })
      return false
    }

    set((state) => ({
      tags: state.tags.filter((tag) => tag.id !== tagId),
      topics: state.topics.map((topic) => ({
        ...topic,
        tag_ids: topic.tag_ids.filter((id) => id !== tagId),
      })),
    }))

    return true
  },
  deleteTopic: async (topicId) => {
    const response = await deleteTopicService(topicId)

    if (response.code !== 200) {
      set({
        errorMessage: response.message,
      })
      return false
    }

    set((state) => ({
      topics: state.topics.filter((topic) => topic.id !== topicId),
    }))

    return true
  },
  updateTag: async (tagId, draft) => {
    const response = await updateTagService(tagId, draft)

    if (response.code !== 200 || !response.data) {
      return {
        ok: false,
        message: response.message,
        tag: null,
      }
    }

    set((state) => ({
      tags: state.tags.map((tag) => (tag.id === tagId ? response.data as Tag : tag)),
    }))

    return {
      ok: true,
      message: 'success',
      tag: response.data,
    }
  },
  updateTopic: async (topicId, draft) => {
    const response = await updateTopicService(topicId, draft)

    if (response.code !== 200 || !response.data) {
      set({
        errorMessage: response.message,
      })
      return false
    }

    const updatedTopic = response.data

    set((state) => ({
      topics: state.topics.map((topic) =>
        topic.id === topicId ? updatedTopic : topic,
      ),
    }))

    return true
  },
}))
