export type TopicStatus = 'pending' | 'working' | 'published' | 'abandoned'

export type TopicPriority = 'high' | 'medium' | 'low'

export type TopicViewMode = 'list' | 'kanban'

export type TopicTimeRange = 'all' | '7d' | '30d'

export type TopicSortOption = 'created_desc' | 'updated_desc' | 'priority_desc'

export type TopicStatusFilter = 'all' | TopicStatus

export type TopicPriorityFilter = 'all' | TopicPriority

export interface Topic {
  id: string
  title: string
  content: string
  notes: string
  source: string
  tag_ids: string[]
  status: TopicStatus
  priority: TopicPriority
  created_at: string
  updated_at: string
}

export type TopicDraft = Pick<
  Topic,
  'title' | 'content' | 'notes' | 'source' | 'tag_ids' | 'status' | 'priority'
>

export interface TopicListData {
  items: Topic[]
  total: number
  page: number
  page_size: number
}
