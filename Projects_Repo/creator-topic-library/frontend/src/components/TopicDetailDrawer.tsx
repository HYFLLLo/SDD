import {
  App as AntdApp,
  Button,
  Drawer,
  Form,
  Input,
  Select,
  Tag as AntTag,
  Typography,
} from 'antd'
import { useMemo, useState, type ReactNode } from 'react'
import { useTopicLibraryStore } from '../stores/useTopicLibraryStore'
import type { Tag } from '../types/tag'
import type { Topic, TopicDraft, TopicStatus } from '../types/topic'
import {
  priorityLabels,
  priorityOptions,
  statusLabels,
  statusOptions,
} from '../utils/topicOptions'

interface TopicDetailDrawerProps {
  onClose: () => void
  open: boolean
  topic: Topic
}

interface DrawerFieldProps {
  children: ReactNode
  label: string
}

const statusColors: Record<TopicStatus, string> = {
  pending: '#D98A4A',
  working: '#4F6F8F',
  published: '#7A8B5C',
  abandoned: '#9A8C82',
}

function DrawerField({ children, label }: DrawerFieldProps) {
  return (
    <div className="topic-drawer__field">
      <div className="topic-drawer__label">{label}</div>
      <div className="topic-drawer__value">{children}</div>
    </div>
  )
}

export default function TopicDetailDrawer({
  onClose,
  open,
  topic,
}: TopicDetailDrawerProps) {
  const [form] = Form.useForm<TopicDraft>()
  const [editing, setEditing] = useState(false)
  const tags = useTopicLibraryStore((state) => state.tags)
  const deleteTopic = useTopicLibraryStore((state) => state.deleteTopic)
  const updateTopic = useTopicLibraryStore((state) => state.updateTopic)
  const { modal, message } = AntdApp.useApp()

  const initialValues = useMemo<TopicDraft>(
    () => ({
      title: topic.title,
      content: topic.content,
      notes: topic.notes,
      source: topic.source,
      tag_ids: topic.tag_ids,
      status: topic.status,
      priority: topic.priority,
    }),
    [topic],
  )

  const tagOptions = useMemo(
    () => tags.map((tag) => ({ label: tag.name, value: tag.id })),
    [tags],
  )

  const topicTags = useMemo(
    () =>
      topic.tag_ids
        .map((tagId) => tags.find((tag) => tag.id === tagId))
        .filter((tag): tag is Tag => Boolean(tag)),
    [tags, topic.tag_ids],
  )

  const handleEdit = () => {
    form.setFieldsValue(initialValues)
    setEditing(true)
  }

  const handleCancelEdit = () => {
    setEditing(false)
  }

  const handleSave = async () => {
    let draft: TopicDraft

    try {
      draft = await form.validateFields()
    } catch {
      return
    }

    const updated = await updateTopic(topic.id, draft)

    if (!updated) {
      message.error('保存失败，请稍后重试')
      return
    }

    message.success('保存成功')
    setEditing(false)
  }

  const handleDelete = () => {
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
          return
        }

        message.success('已删除')
        onClose()
      },
    })
  }

  const footer = editing ? (
    <div className="topic-drawer__footer">
      <Button onClick={handleCancelEdit}>取消</Button>
      <Button type="primary" onClick={handleSave}>
        保存
      </Button>
    </div>
  ) : (
    <div className="topic-drawer__footer">
      <Button danger onClick={handleDelete}>
        删除
      </Button>
      <Button type="primary" onClick={handleEdit}>
        编辑
      </Button>
    </div>
  )

  return (
    <Drawer
      className="topic-detail-drawer"
      footer={footer}
      open={open}
      size={560}
      title="选题详情"
      onClose={onClose}
    >
      <div className="topic-drawer__content">
        {editing ? (
          <Form
            form={form}
            initialValues={initialValues}
            layout="vertical"
            className="topic-drawer__form"
          >
            <Form.Item
              label="标题"
              name="title"
              rules={[{ required: true, whitespace: true, message: '标题不能为空' }]}
            >
              <Input placeholder="请输入标题" />
            </Form.Item>

            <Form.Item label="内容" name="content">
              <Input.TextArea
                autoSize={{ minRows: 4, maxRows: 8 }}
                placeholder="请输入内容"
              />
            </Form.Item>

            <Form.Item label="备注" name="notes">
              <Input.TextArea
                autoSize={{ minRows: 3, maxRows: 8 }}
                placeholder="请输入备注"
              />
            </Form.Item>

            <Form.Item label="来源" name="source">
              <Input placeholder="请输入来源" />
            </Form.Item>

            <Form.Item label="标签" name="tag_ids">
              <Select
                allowClear
                mode="multiple"
                options={tagOptions}
                placeholder="选择标签"
              />
            </Form.Item>

            <Form.Item label="状态" name="status">
              <Select options={statusOptions} />
            </Form.Item>

            <Form.Item label="优先级" name="priority">
              <Select options={priorityOptions} />
            </Form.Item>
          </Form>
        ) : (
          <div className="topic-drawer__fields">
            <DrawerField label="标题">
              <Typography.Title level={5} className="topic-drawer__title">
                {topic.title}
              </Typography.Title>
            </DrawerField>

            <DrawerField label="内容">
              <Typography.Paragraph className="topic-drawer__text">
                {topic.content || '—'}
              </Typography.Paragraph>
            </DrawerField>

            <DrawerField label="备注">
              <Typography.Paragraph className="topic-drawer__text">
                {topic.notes || '—'}
              </Typography.Paragraph>
            </DrawerField>

            <DrawerField label="来源">
              <Typography.Text>{topic.source || '—'}</Typography.Text>
            </DrawerField>

            <DrawerField label="标签">
              {topicTags.length > 0 ? (
                <div className="topic-drawer__tags">
                  {topicTags.map((tag) => (
                    <AntTag key={tag.id} color={tag.color}>
                      {tag.name}
                    </AntTag>
                  ))}
                </div>
              ) : (
                <Typography.Text type="secondary">暂无标签</Typography.Text>
              )}
            </DrawerField>

            <DrawerField label="状态">
              <AntTag color={statusColors[topic.status]}>
                {statusLabels[topic.status]}
              </AntTag>
            </DrawerField>

            <DrawerField label="优先级">
              <span className={`topic-priority topic-priority--${topic.priority}`}>
                {priorityLabels[topic.priority]}
              </span>
            </DrawerField>
          </div>
        )}

        <div className="topic-drawer__fields topic-drawer__timestamps">
          <DrawerField label="创建时间">
            <Typography.Text code>{topic.created_at}</Typography.Text>
          </DrawerField>
          <DrawerField label="更新时间">
            <Typography.Text code>{topic.updated_at}</Typography.Text>
          </DrawerField>
        </div>
      </div>
    </Drawer>
  )
}
