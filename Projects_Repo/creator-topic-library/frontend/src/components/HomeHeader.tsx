import { Button, Input, Segmented, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { TopicViewMode } from '../types/topic'

interface HomeHeaderProps {
  keyword: string
  onKeywordChange: (keyword: string) => void
  onQuickCreate: () => void
  onRandomPick: () => void
  onViewModeChange: (mode: TopicViewMode) => void
  viewMode: TopicViewMode
}

export default function HomeHeader({
  keyword,
  onKeywordChange,
  onQuickCreate,
  onRandomPick,
  onViewModeChange,
  viewMode,
}: HomeHeaderProps) {
  const navigate = useNavigate()

  return (
    <header className="home-header">
      <div className="home-header__inner">
        <Typography.Title level={4} className="home-header__brand">
          创作者选题灵感库
        </Typography.Title>

        <Input
          className="home-header__search"
          value={keyword}
          placeholder="搜索标题、内容或标签"
          allowClear
          onChange={(event) => onKeywordChange(event.target.value)}
        />

        <Segmented
          value={viewMode}
          options={[
            { label: '列表', value: 'list' },
            { label: '看板', value: 'kanban' },
          ]}
          onChange={(value) => onViewModeChange(value as TopicViewMode)}
        />

        <div className="home-header__actions">
          <Button onClick={onQuickCreate}>快速记录</Button>
          <Button onClick={onRandomPick}>随机选题</Button>
          <Button onClick={() => navigate('/tags')}>标签管理</Button>
        </div>
      </div>
    </header>
  )
}
