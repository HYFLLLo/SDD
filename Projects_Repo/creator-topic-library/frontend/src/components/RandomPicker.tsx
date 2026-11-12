import { Button, Card, Empty, Modal, Tag as AntTag, Typography } from 'antd'
import type { Tag } from '../types/tag'
import type { Topic, TopicStatus } from '../types/topic'
import { priorityLabels, statusLabels } from '../utils/topicOptions'

interface RandomPickerProps {
  onClose: () => void
  onNext: () => void
  onOpenTopic: (topic: Topic) => void
  open: boolean
  tags: Tag[]
  topic: Topic | null
}

const statusColors: Record<TopicStatus, string> = {
  pending: '#D98A4A',
  working: '#4F6F8F',
  published: '#7A8B5C',
  abandoned: '#9A8C82',
}

export default function RandomPicker({
  onClose,
  onNext,
  onOpenTopic,
  open,
  tags,
  topic,
}: RandomPickerProps) {
  const topicTags = topic
    ? topic.tag_ids
        .map((tagId) => tags.find((tag) => tag.id === tagId))
        .filter((tag): tag is Tag => Boolean(tag))
    : []

  return (
    <Modal
      className="random-picker"
      footer={null}
      open={open}
      title="随机选题"
      width={560}
      onCancel={onClose}
    >
      {topic ? (
        <div className="random-picker__result">
          <Card
            className="random-picker__card"
            hoverable
            onClick={() => onOpenTopic(topic)}
          >
            <Typography.Title level={4} className="random-picker__title">
              {topic.title}
            </Typography.Title>
            <Typography.Paragraph className="random-picker__content">
              {topic.content}
            </Typography.Paragraph>
            <div className="random-picker__tags">
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
            <div className="random-picker__meta">
              <AntTag color={statusColors[topic.status]}>
                {statusLabels[topic.status]}
              </AntTag>
              <span className={`topic-priority topic-priority--${topic.priority}`}>
                {priorityLabels[topic.priority]}
              </span>
            </div>
          </Card>
          <div className="random-picker__footer">
            <Button onClick={onNext}>换一个</Button>
            <Button type="primary" onClick={() => onOpenTopic(topic)}>
              查看详情
            </Button>
          </div>
        </div>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="没有符合条件的选题，试试调整搜索或筛选条件"
        />
      )}
    </Modal>
  )
}
