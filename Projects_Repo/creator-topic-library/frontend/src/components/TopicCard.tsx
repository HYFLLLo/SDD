import { Button, Card, Dropdown, Tag as AntTag, Typography } from 'antd'
import type { Tag } from '../types/tag'
import type { Topic, TopicStatus } from '../types/topic'
import { priorityLabels, statusLabels, statusOptions } from '../utils/topicOptions'

interface TopicCardProps {
  onDelete: (topic: Topic) => void
  onOpen: (topic: Topic) => void
  onStatusChange?: (topic: Topic, status: TopicStatus) => void
  tags: Tag[]
  topic: Topic
}

const statusColors: Record<TopicStatus, string> = {
  pending: '#D98A4A',
  working: '#4F6F8F',
  published: '#7A8B5C',
  abandoned: '#9A8C82',
}

function formatTopicTime(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  return `${month}-${day} ${hours}:${minutes}`
}

export default function TopicCard({
  onDelete,
  onOpen,
  onStatusChange,
  tags,
  topic,
}: TopicCardProps) {
  const topicTags = topic.tag_ids
    .map((tagId) => tags.find((tag) => tag.id === tagId))
    .filter((tag): tag is Tag => Boolean(tag))

  return (
    <Card
      className="topic-card"
      bordered
      hoverable
      onClick={() => onOpen(topic)}
    >
      <div className="topic-card__main">
        <Typography.Title level={5} className="topic-card__title">
          {topic.title}
        </Typography.Title>
        <Typography.Paragraph className="topic-card__content">
          {topic.content}
        </Typography.Paragraph>
      </div>

      <div className="topic-card__tags">
        {topicTags.length > 0 ? (
          topicTags.map((tag) => (
            <AntTag key={tag.id} color={tag.color}>
              {tag.name}
            </AntTag>
          ))
        ) : (
          <span className="topic-card__no-tag">暂无标签</span>
        )}
      </div>

      <div className="topic-card__meta">
        <div className="topic-card__badges">
          {onStatusChange ? (
            <span
              className="topic-card__status-trigger"
              onClick={(event) => event.stopPropagation()}
            >
              <Dropdown
                menu={{
                  items: statusOptions.map((option) => ({
                    key: option.value,
                    label: option.label,
                  })),
                  onClick: ({ key }) => onStatusChange(topic, key as TopicStatus),
                }}
                trigger={['click']}
              >
                <AntTag color={statusColors[topic.status]}>
                  {statusLabels[topic.status]}
                </AntTag>
              </Dropdown>
            </span>
          ) : (
            <AntTag color={statusColors[topic.status]}>
              {statusLabels[topic.status]}
            </AntTag>
          )}
          <span className={`topic-priority topic-priority--${topic.priority}`}>
            {priorityLabels[topic.priority]}
          </span>
          <span className="topic-card__time">{formatTopicTime(topic.updated_at)}</span>
        </div>
        <Button
          type="link"
          danger
          size="small"
          onClick={(event) => {
            event.stopPropagation()
            onDelete(topic)
          }}
        >
          删除
        </Button>
      </div>
    </Card>
  )
}
