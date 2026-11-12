import { App as AntdApp, Empty, Typography } from 'antd'
import { useMemo, useState } from 'react'
import HomeHeader from '../components/HomeHeader'
import QuickCreateModal from '../components/QuickCreateModal'
import RandomPicker from '../components/RandomPicker'
import TopicCard from '../components/TopicCard'
import TopicDetailDrawer from '../components/TopicDetailDrawer'
import TopicFilterBar from '../components/TopicFilterBar'
import TopicKanban from '../components/TopicKanban'
import { useTopicLibraryStore } from '../stores/useTopicLibraryStore'
import type {
  Topic,
  TopicDraft,
  TopicPriorityFilter,
  TopicSortOption,
  TopicStatus,
  TopicStatusFilter,
  TopicTimeRange,
  TopicViewMode,
} from '../types/topic'

const DAY_MS = 24 * 60 * 60 * 1000

const priorityRank = {
  high: 3,
  medium: 2,
  low: 1,
} as const

export default function HomePage() {
  const topics = useTopicLibraryStore((state) => state.topics)
  const tags = useTopicLibraryStore((state) => state.tags)
  const status = useTopicLibraryStore((state) => state.status)
  const deleteTopic = useTopicLibraryStore((state) => state.deleteTopic)
  const updateTopic = useTopicLibraryStore((state) => state.updateTopic)
  const { message, modal } = AntdApp.useApp()

  const [keyword, setKeyword] = useState('')
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<TopicStatusFilter>('all')
  const [priorityFilter, setPriorityFilter] = useState<TopicPriorityFilter>('all')
  const [timeRange, setTimeRange] = useState<TopicTimeRange>('all')
  const [sort, setSort] = useState<TopicSortOption>('updated_desc')
  const [viewMode, setViewMode] = useState<TopicViewMode>('list')
  const [quickCreateOpen, setQuickCreateOpen] = useState(false)
  const [randomPickerOpen, setRandomPickerOpen] = useState(false)
  const [randomTopic, setRandomTopic] = useState<Topic | null>(null)
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)
  const [now] = useState(() => Date.now())

  const selectedTopic = useMemo(
    () => topics.find((topic) => topic.id === selectedTopicId) ?? null,
    [selectedTopicId, topics],
  )

  const tagNameMap = useMemo(
    () => new Map(tags.map((tag) => [tag.id, tag.name])),
    [tags],
  )

  const filteredTopics = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase()

    const matchedTopics = topics.filter((topic) => {
      if (normalizedKeyword) {
        const tagText = topic.tag_ids
          .map((tagId) => tagNameMap.get(tagId) ?? '')
          .join(' ')
        const searchableText = `${topic.title} ${topic.content} ${tagText}`.toLowerCase()

        if (!searchableText.includes(normalizedKeyword)) {
          return false
        }
      }

      if (
        selectedTagIds.length > 0
        && !selectedTagIds.every((tagId) => topic.tag_ids.includes(tagId))
      ) {
        return false
      }

      if (statusFilter !== 'all' && topic.status !== statusFilter) {
        return false
      }

      if (priorityFilter !== 'all' && topic.priority !== priorityFilter) {
        return false
      }

      if (timeRange === '7d') {
        if (now - Date.parse(topic.updated_at) > 7 * DAY_MS) {
          return false
        }
      }

      if (timeRange === '30d') {
        if (now - Date.parse(topic.updated_at) > 30 * DAY_MS) {
          return false
        }
      }

      return true
    })

    return matchedTopics.sort((left, right) => {
      if (sort === 'priority_desc') {
        const priorityDiff = priorityRank[right.priority] - priorityRank[left.priority]

        if (priorityDiff !== 0) {
          return priorityDiff
        }

        return Date.parse(right.updated_at) - Date.parse(left.updated_at)
      }

      if (sort === 'updated_desc') {
        return Date.parse(right.updated_at) - Date.parse(left.updated_at)
      }

      return Date.parse(right.created_at) - Date.parse(left.created_at)
    })
  }, [
    keyword,
    priorityFilter,
    selectedTagIds,
    sort,
    statusFilter,
    tagNameMap,
    timeRange,
    topics,
    now,
  ])

  const randomCandidates = useMemo(
    () => filteredTopics.filter(
      (topic) => topic.status !== 'published' && topic.status !== 'abandoned',
    ),
    [filteredTopics],
  )

  const emptyDescription =
    topics.length === 0
      ? '还没有选题，点击“快速记录”开始创建第一条选题'
      : '没有符合条件的选题，试试调整搜索或筛选条件'

  const handleTagToggle = (tagId: string, checked: boolean) => {
    setSelectedTagIds((currentTagIds) => {
      if (checked) {
        return currentTagIds.includes(tagId)
          ? currentTagIds
          : [...currentTagIds, tagId]
      }

      return currentTagIds.filter((currentTagId) => currentTagId !== tagId)
    })
  }

  const handleClearFilters = () => {
    setSelectedTagIds([])
    setStatusFilter('all')
    setPriorityFilter('all')
    setTimeRange('all')
    setSort('updated_desc')
  }

  const handleDelete = (topic: Topic) => {
    modal.confirm({
      title: '删除选题',
      content: `确定要删除“${topic.title}”吗？删除后无法恢复。`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: {
        danger: true,
      },
      onOk: async () => {
        const deleted = await deleteTopic(topic.id)

        if (!deleted) {
          modal.error({
            title: '删除失败',
            content: '请稍后重试',
          })
        }
      },
    })
  }

  const handleStatusChange = async (topic: Topic, nextStatus: TopicStatus) => {
    if (topic.status === nextStatus) {
      return
    }

    const draft: TopicDraft = {
      title: topic.title,
      content: topic.content,
      notes: topic.notes,
      source: topic.source,
      tag_ids: [...topic.tag_ids],
      status: nextStatus,
      priority: topic.priority,
    }

    const updated = await updateTopic(topic.id, draft)

    if (!updated) {
      message.error('状态修改失败，请稍后重试')
    }
  }

  const handleOpenRandomPicker = () => {
    if (randomCandidates.length === 0) {
      setRandomTopic(null)
    } else {
      setRandomTopic(randomCandidates[Math.floor(Math.random() * randomCandidates.length)])
    }

    setRandomPickerOpen(true)
  }

  const handleNextRandom = () => {
    if (randomCandidates.length === 0) {
      setRandomTopic(null)
      return
    }

    const nextCandidates =
      randomCandidates.length > 1
        ? randomCandidates.filter((topic) => topic.id !== randomTopic?.id)
        : randomCandidates
    const pool = nextCandidates.length > 0 ? nextCandidates : randomCandidates

    setRandomTopic(pool[Math.floor(Math.random() * pool.length)])
  }

  const handleOpenRandomTopic = (topic: Topic) => {
    setRandomPickerOpen(false)
    setSelectedTopicId(topic.id)
  }

  return (
    <div className="home-page">
      <HomeHeader
        keyword={keyword}
        viewMode={viewMode}
        onKeywordChange={setKeyword}
        onViewModeChange={setViewMode}
        onQuickCreate={() => setQuickCreateOpen(true)}
        onRandomPick={handleOpenRandomPicker}
      />

      <TopicFilterBar
        tags={tags}
        selectedTagIds={selectedTagIds}
        status={statusFilter}
        priority={priorityFilter}
        timeRange={timeRange}
        sort={sort}
        onTagToggle={handleTagToggle}
        onStatusChange={setStatusFilter}
        onPriorityChange={setPriorityFilter}
        onTimeRangeChange={setTimeRange}
        onSortChange={setSort}
        onClear={handleClearFilters}
      />

      <div className="topic-summary">
        <Typography.Text strong>全部</Typography.Text>
        <Typography.Text type="secondary">共 {filteredTopics.length} 条</Typography.Text>
      </div>

      {status === 'success' ? (
        filteredTopics.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={emptyDescription}
          />
        ) : viewMode === 'list' ? (
          <div className="topic-grid">
            {filteredTopics.map((topic) => (
              <TopicCard
                key={topic.id}
                topic={topic}
                tags={tags}
                onDelete={handleDelete}
                onOpen={(openedTopic) => setSelectedTopicId(openedTopic.id)}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        ) : (
          <TopicKanban
            topics={filteredTopics}
            tags={tags}
            onDelete={handleDelete}
            onOpen={(openedTopic) => setSelectedTopicId(openedTopic.id)}
            onStatusChange={handleStatusChange}
          />
        )
      ) : null}

      {selectedTopic ? (
        <TopicDetailDrawer
          key={selectedTopic.id}
          open
          topic={selectedTopic}
          onClose={() => setSelectedTopicId(null)}
        />
      ) : null}

      <RandomPicker
        open={randomPickerOpen}
        tags={tags}
        topic={randomTopic}
        onClose={() => setRandomPickerOpen(false)}
        onNext={handleNextRandom}
        onOpenTopic={handleOpenRandomTopic}
      />

      <QuickCreateModal
        open={quickCreateOpen}
        onCancel={() => setQuickCreateOpen(false)}
      />
    </div>
  )
}
