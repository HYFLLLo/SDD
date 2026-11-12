import {
  App as AntdApp,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Modal,
  Typography,
} from 'antd'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTopicLibraryStore } from '../stores/useTopicLibraryStore'
import type { Tag, TagDraft } from '../types/tag'

interface TagFormValues {
  color: string
  name: string
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

const initialValues: TagFormValues = {
  name: '',
  color: tagColorOptions[0],
}

export default function TagManager() {
  const navigate = useNavigate()
  const tags = useTopicLibraryStore((state) => state.tags)
  const topics = useTopicLibraryStore((state) => state.topics)
  const createTag = useTopicLibraryStore((state) => state.createTag)
  const updateTag = useTopicLibraryStore((state) => state.updateTag)
  const deleteTag = useTopicLibraryStore((state) => state.deleteTag)
  const { message, modal } = AntdApp.useApp()

  const [form] = Form.useForm<TagFormValues>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingTag, setEditingTag] = useState<Tag | null>(null)
  const [selectedColor, setSelectedColor] = useState(tagColorOptions[0])
  const [saving, setSaving] = useState(false)

  const usageCounts = useMemo(() => {
    const counts = new Map<string, number>()

    topics.forEach((topic) => {
      topic.tag_ids.forEach((tagId) => {
        counts.set(tagId, (counts.get(tagId) ?? 0) + 1)
      })
    })

    return counts
  }, [topics])

  const openCreate = () => {
    setEditingTag(null)
    setSelectedColor(tagColorOptions[0])
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (tag: Tag) => {
    setEditingTag(tag)
    setSelectedColor(tag.color)
    form.setFieldsValue({
      name: tag.name,
      color: tag.color,
    })
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    form.resetFields()
  }

  const handleSave = async () => {
    let values: TagFormValues

    try {
      values = await form.validateFields()
    } catch {
      return
    }

    const draft: TagDraft = {
      name: values.name.trim(),
      color: selectedColor,
    }

    setSaving(true)
    const result = editingTag
      ? await updateTag(editingTag.id, draft)
      : await createTag(draft)
    setSaving(false)

    if (!result.ok) {
      message.error(result.message)
      return
    }

    message.success(editingTag ? '保存成功' : '标签已创建')
    closeModal()
  }

  const handleDelete = (tag: Tag) => {
    modal.confirm({
      title: '删除标签',
      content: `确定要删除“${tag.name}”吗？删除后无法恢复。`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: {
        danger: true,
      },
      onOk: async () => {
        const deleted = await deleteTag(tag.id)

        if (!deleted) {
          modal.error({
            title: '删除失败',
            content: '请稍后重试',
          })
        }
      },
    })
  }

  return (
    <div className="tag-manager page-stack">
      <div className="tag-manager__toolbar">
        <div className="tag-manager__toolbar-start">
          <Button onClick={() => navigate('/')}>返回选题库</Button>
          <Typography.Title level={2} className="tag-manager__title">
            标签管理
          </Typography.Title>
        </div>
        <Button type="primary" onClick={openCreate}>
          新建标签
        </Button>
      </div>

      <div className="tag-manager__summary">
        <Typography.Title level={3} className="tag-manager__section-title">
          全部标签
        </Typography.Title>
        <Typography.Text type="secondary">共 {tags.length} 个</Typography.Text>
      </div>

      {tags.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className="tag-manager__grid">
          {tags.map((tag) => (
            <Card className="tag-manager__card" key={tag.id}>
              <div className="tag-manager__card-main">
                <span
                  className="tag-manager__dot"
                  style={{ backgroundColor: tag.color }}
                />
                <Typography.Text className="tag-manager__name">
                  {tag.name}
                </Typography.Text>
                <Typography.Text type="secondary" className="tag-manager__usage">
                  使用 {usageCounts.get(tag.id) ?? 0} 次
                </Typography.Text>
              </div>
              <div className="tag-manager__card-actions">
                <Button type="default" size="small" onClick={() => openEdit(tag)}>
                  编辑
                </Button>
                <Button
                  className="tag-manager__delete-button"
                  type="default"
                  danger
                  size="small"
                  onClick={() => handleDelete(tag)}
                >
                  删除
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        cancelText="取消"
        confirmLoading={saving}
        okText="保存"
        open={modalOpen}
        title={editingTag ? '编辑标签' : '新建标签'}
        width={480}
        onCancel={closeModal}
        onOk={handleSave}
      >
        <Form
          className="tag-manager__form"
          form={form}
          initialValues={initialValues}
          layout="vertical"
        >
          <Form.Item
            label="标签名称"
            name="name"
            rules={[{ required: true, whitespace: true, message: '标签名称不能为空' }]}
          >
            <Input maxLength={20} placeholder="输入标签名称" />
          </Form.Item>

          <Form.Item label="颜色">
            <div className="tag-manager__color-swatches">
              {tagColorOptions.map((color) => (
                <button
                  key={color}
                  aria-label={`选择颜色 ${color}`}
                  className={`tag-manager__color-swatch${color === selectedColor ? ' tag-manager__color-swatch--active' : ''}`}
                  style={{ backgroundColor: color }}
                  type="button"
                  onClick={() => setSelectedColor(color)}
                />
              ))}
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
