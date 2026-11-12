import { Link } from 'react-router-dom'
import './PagePlaceholder.css'

interface PagePlaceholderProps {
  title: string
  description?: string
}

/** 占位页通用骨架：显示页面名 + （占位） */
export default function PagePlaceholder({ title, description }: PagePlaceholderProps) {
  return (
    <div className="page-head placeholder-page">
      <h1>
        {title}（占位）
      </h1>
      {description ? <p className="desc">{description}</p> : null}
      <div className="empty">
        <div className="emoji-art" aria-hidden="true">
          🖌️
        </div>
        <p>该页面将在后续任务中实现</p>
        <Link to="/" className="btn btn-ghost btn-sm">
          返回广场
        </Link>
      </div>
    </div>
  )
}
