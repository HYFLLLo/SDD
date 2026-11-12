import { Empty, Tag as AntTag, Typography } from 'antd'
import { useState, type DragEvent as ReactDragEvent } from 'react'
import type { Tag } from '../types/tag'
import type { Topic, TopicStatus } from '../types/topic'
import { statusLabels } from '../utils/topicOptions'
import TopicCard from './TopicCard'

interface TopicKanbanProps {
  onDelete: (topic: Topic) => void
  onOpen: (topic: Topic) => void
  onStatusChange: (topic: Topic, status: TopicStatus) => void
  tags: Tag[]
  topics: Topic[]
}

const statusColumns: TopicStatus[] = ['pending', 'working', 'published', 'abandoned']

export default function TopicKanban({
  onDelete,
  onOpen,
  onStatusChange,
  tags,
  topics,
}: TopicKanbanProps) {
  const [draggedTopicId, setDraggedTopicId] = useState<string | null>(null)
  const [dragOverStatus, setDragOverStatus] = useState<TopicStatus | null>(null)

  const handleDragStart = (topic: Topic) => (event: ReactDragEvent<HTMLDivElement>) => {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', topic.id)
    setDraggedTopicId(topic.id)
  }

  const handleDragEnd = () => {
    setDraggedTopicId(null)
    setDragOverStatus(null)
  }

  const handleDragOver = (status: TopicStatus) => (
    event: ReactDragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
    setDragOverStatus(status)
  }

  const handleDrop = (status: TopicStatus) => (event: ReactDragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const topic = topics.find((item) => item.id === draggedTopicId)

    if (topic && topic.status !== status) {
      onStatusChange(topic, status)
    }

    setDraggedTopicId(null)
    setDragOverStatus(null)
  }

  return (
    <div className="kanban-board">
      {statusColumns.map((status) => {
        const columnTopics = topics.filter((topic) => topic.status === status)

        return (
          <section className="kanban-column" key={status}>
            <div className="kanban-column__header">
              <Typography.Text strong>{statusLabels[status]}</Typography.Text>
              <AntTag>{columnTopics.length}</AntTag>
            </div>
            <div
              className={`kanban-column__body${
                dragOverStatus === status ? ' kanban-column__body--drag-over' : ''
              }`}
              onDragOver={handleDragOver(status)}
              onDrop={handleDrop(status)}
            >
              {columnTopics.length > 0 ? (
                columnTopics.map((topic) => (
                  <div
                    key={topic.id}
                    className={`kanban-card${
                      draggedTopicId === topic.id ? ' kanban-card--dragging' : ''
                    }`}
                    draggable
                    onDragEnd={handleDragEnd}
                    onDragStart={handleDragStart(topic)}
                  >
                    <TopicCard
                      topic={topic}
                      tags={tags}
                      onDelete={onDelete}
                      onOpen={onOpen}
                    />
                  </div>
                ))
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无选题" />
              )}
            </div>
          </section>
        )
      })}
    </div>
  )
}
