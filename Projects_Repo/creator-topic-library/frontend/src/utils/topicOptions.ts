import type {
  TopicPriority,
  TopicPriorityFilter,
  TopicSortOption,
  TopicStatus,
  TopicStatusFilter,
  TopicTimeRange,
} from '../types/topic'

export const statusLabels: Record<TopicStatus, string> = {
  pending: '待验证',
  working: '创作中',
  published: '已发布',
  abandoned: '已放弃',
}

export const priorityLabels: Record<TopicPriority, string> = {
  high: '优先高',
  medium: '优先中',
  low: '优先低',
}

export const statusOptions: Array<{ label: string; value: TopicStatus }> = [
  { label: '待验证', value: 'pending' },
  { label: '创作中', value: 'working' },
  { label: '已发布', value: 'published' },
  { label: '已放弃', value: 'abandoned' },
]

export const priorityOptions: Array<{ label: string; value: TopicPriority }> = [
  { label: '优先高', value: 'high' },
  { label: '优先中', value: 'medium' },
  { label: '优先低', value: 'low' },
]

export const statusFilterOptions: Array<{ label: string; value: TopicStatusFilter }> = [
  { label: '全部状态', value: 'all' },
  { label: '待验证', value: 'pending' },
  { label: '创作中', value: 'working' },
  { label: '已发布', value: 'published' },
  { label: '已放弃', value: 'abandoned' },
]

export const priorityFilterOptions: Array<{ label: string; value: TopicPriorityFilter }> = [
  { label: '全部优先级', value: 'all' },
  { label: '优先高', value: 'high' },
  { label: '优先中', value: 'medium' },
  { label: '优先低', value: 'low' },
]

export const timeRangeOptions: Array<{ label: string; value: TopicTimeRange }> = [
  { label: '全部时间', value: 'all' },
  { label: '近7天', value: '7d' },
  { label: '近30天', value: '30d' },
]

export const sortOptions: Array<{ key?: string; label: string; value: TopicSortOption }> = [
  { key: 'default', label: '默认排序', value: 'updated_desc' },
  { key: 'created', label: '创建时间', value: 'created_desc' },
  { key: 'updated', label: '更新时间', value: 'updated_desc' },
  { key: 'priority', label: '优先级', value: 'priority_desc' },
]
