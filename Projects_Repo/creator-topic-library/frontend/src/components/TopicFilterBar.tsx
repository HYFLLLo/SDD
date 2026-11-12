import { Button, Select, Tag as AntTag } from 'antd'
import type { Tag } from '../types/tag'
import type {
  TopicPriorityFilter,
  TopicSortOption,
  TopicStatusFilter,
  TopicTimeRange,
} from '../types/topic'
import {
  priorityFilterOptions,
  sortOptions,
  statusFilterOptions,
  timeRangeOptions,
} from '../utils/topicOptions'

interface TopicFilterBarProps {
  onClear: () => void
  onPriorityChange: (value: TopicPriorityFilter) => void
  onSortChange: (value: TopicSortOption) => void
  onStatusChange: (value: TopicStatusFilter) => void
  onTagToggle: (tagId: string, checked: boolean) => void
  onTimeRangeChange: (value: TopicTimeRange) => void
  priority: TopicPriorityFilter
  selectedTagIds: string[]
  sort: TopicSortOption
  status: TopicStatusFilter
  tags: Tag[]
  timeRange: TopicTimeRange
}

export default function TopicFilterBar({
  onClear,
  onPriorityChange,
  onSortChange,
  onStatusChange,
  onTagToggle,
  onTimeRangeChange,
  priority,
  selectedTagIds,
  sort,
  status,
  tags,
  timeRange,
}: TopicFilterBarProps) {
  return (
    <div className="topic-filter-bar">
      <div className="topic-filter-bar__tags">
        {tags.map((tag) => (
          <AntTag.CheckableTag
            key={tag.id}
            checked={selectedTagIds.includes(tag.id)}
            onChange={(checked) => onTagToggle(tag.id, checked)}
          >
            {tag.name}
          </AntTag.CheckableTag>
        ))}
      </div>

      <div className="topic-filter-bar__selects">
        <Select
          className="topic-filter-select"
          value={status}
          options={statusFilterOptions}
          onChange={(value) => onStatusChange(value as TopicStatusFilter)}
        />
        <Select
          className="topic-filter-select"
          value={priority}
          options={priorityFilterOptions}
          onChange={(value) => onPriorityChange(value as TopicPriorityFilter)}
        />
        <Select
          className="topic-filter-select"
          value={timeRange}
          options={timeRangeOptions}
          onChange={(value) => onTimeRangeChange(value as TopicTimeRange)}
        />
        <Select
          className="topic-filter-select"
          value={sort}
          options={sortOptions}
          onChange={(value) => onSortChange(value as TopicSortOption)}
        />
      </div>

      <Button type="link" onClick={onClear}>
        清除
      </Button>
    </div>
  )
}
