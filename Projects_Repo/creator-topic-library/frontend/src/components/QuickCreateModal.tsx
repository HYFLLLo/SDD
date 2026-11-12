import {
  App as AntdApp,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Typography,
} from 'antd'
import { useMemo, useState } from 'react'
import { useTopicLibraryStore } from '../stores/useTopicLibraryStore'
import type { TopicDraft, TopicPriority } from '../types/topic'
import { statusOptions } from '../utils/topicOptions'

interface QuickCreateModalProps {
  onCancel: () => void
  open: boolean
}

const initialValues: TopicDraft = {
  title: '',
  content: '',
  notes: '',
  source: '',
  tag_ids: [],
  status: 'pending',
  priority: 'medium',
}

const tagColorOptions = [
  '#C2571B',
  '#7A8B5C',
  '#4F6F8F',
  '#B07D4A',
  '#D98A4A',
  '#8E6C88',
  '#6B8E7B',
  '#B85C38',
]

const priorityQuickOptions: Array<{ label: string; value: TopicPriority }> = [
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' },
]

export default function QuickCreateModal({
  onCancel,
  open,
}: QuickCreateModalProps) {
  const [form] = Form.useForm<TopicDraft>()
  const tags = useTopicLibraryStore((state) => state.tags)
  const createTag = useTopicLibraryStore((state) => state.createTag)
  const createTopic = useTopicLibraryStore((state) => state.createTopic)
  const { message } = AntdApp.useApp()

  const [saving, setSaving] = useState(false)
  const [tagPanelOpen, setTagPanelOpen] = useState(false)
  const [tagName, setTagName] = useState('')
  const [tagColor, setTagColor] = useState(tagColorOptions[0])
  const [tagError, setTagError] = useState<string | null>(null)
  const [tagSaving, setTagSaving] = useState(false)

  const tagOptions = useMemo(
    () => tags.map((tag) => ({ label: tag.name, value: tag.id })),
    [tags],
  )

  const handleCancelTagPanel = () => {
    setTagPanelOpen(false)
    setTagName('')
    setTagColor(tagColorOptions[0])
    setTagError(null)
  }

  const handleCreateTag = async () => {
    const name = tagName.trim()

    if (!name) {
      setTagError('请输入标签名称')
      return
    }

    setTagSaving(true)
    const result = await createTag({
      name,
      color: tagColor,
    })
    setTagSaving(false)

    if (!result.ok || !result.tag) {
      setTagError(result.message)
      return
    }

    const selectedTagIds = (form.getFieldValue('tag_ids') as string[] | undefined) ?? []

    form.setFieldValue('tag_ids', [...selectedTagIds, result.tag.id])
    setTagPanelOpen(false)
    setTagName('')
    setTagColor(tagColorOptions[0])
    setTagError(null)
    message.success('标签已创建')
  }

  const handleSave = async () => {
    let values: TopicDraft

    try {
      values = await form.validateFields()
    } catch {
      return
    }

    setSaving(true)
    const created = await createTopic({
      title: values.title,
      content: values.content ?? '',
      notes: '',
      source: values.source ?? '',
      tag_ids: values.tag_ids ?? [],
      status: values.status,
      priority: values.priority,
    })
    setSaving(false)

    if (!created) {
      message.error('保存失败，请稍后重试')
      return
    }

    message.success('保存成功')
    onCancel()
  }

  return (
    <Modal
      cancelText="取消"
      className="quick-create-modal"
      confirmLoading={saving}
      okText="保存选题"
      open={open}
      title="快速灵感"
      width={560}
      afterOpenChange={(visible) => {
        if (!visible) {
          return
        }

        form.resetFields()
        setTagPanelOpen(false)
        setTagName('')
        setTagColor(tagColorOptions[0])
        setTagError(null)
      }}
      onCancel={onCancel}
      onOk={handleSave}
    >
      <Form
        form={form}
        initialValues={initialValues}
        layout="vertical"
        className="quick-create-modal__form"
      >
        <Form.Item
          label="标题"
          name="title"
          rules={[{ required: true, whitespace: true, message: '标题不能为空' }]}
        >
          <Input placeholder="用一句话概括选题" />
        </Form.Item>

        <Form.Item label="内容" name="content">
          <Input.TextArea
            autoSize={{ minRows: 3, maxRows: 6 }}
            placeholder="补充内容方向或切入点"
          />
        </Form.Item>

        <Form.Item label="来源" name="source">
          <Input placeholder="例如：评论区、播客、搜索" />
        </Form.Item>

        <Form.Item label="标签" name="tag_ids">
          <Select
            allowClear
            mode="multiple"
            options={tagOptions}
            placeholder="选择标签"
          />
        </Form.Item>

        {tagPanelOpen ? (
          <div className="quick-create-tag-panel">
            <Input
              autoFocus
              maxLength={20}
              placeholder="输入标签名称"
              status={tagError ? 'error' : undefined}
              value={tagName}
              onChange={(event) => {
                setTagName(event.target.value)
                setTagError(null)
              }}
            />
            <div className="quick-create-color-swatches">
              {tagColorOptions.map((color) => (
                <button
                  key={color}
                  aria-label={`选择颜色 ${color}`}
                  className={`quick-create-color-swatch${color === tagColor ? ' quick-create-color-swatch--active' : ''}`}
                  style={{ backgroundColor: color }}
                  type="button"
                  onClick={() => setTagColor(color)}
                />
              ))}
            </div>
            {tagError ? (
              <Typography.Text type="danger">{tagError}</Typography.Text>
            ) : null}
            <Space>
              <Button size="small" onClick={handleCancelTagPanel}>
                取消
              </Button>
              <Button
                size="small"
                type="primary"
                loading={tagSaving}
                onClick={handleCreateTag}
              >
                添加
              </Button>
            </Space>
          </div>
        ) : (
          <Button
            className="quick-create-tag-trigger"
            type="link"
            onClick={() => {
              setTagPanelOpen(true)
              setTagError(null)
            }}
          >
            新建标签
          </Button>
        )}

        <Form.Item label="状态" name="status">
          <Select options={statusOptions} />
        </Form.Item>

        <Form.Item label="优先级" name="priority">
          <Select options={priorityQuickOptions} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
