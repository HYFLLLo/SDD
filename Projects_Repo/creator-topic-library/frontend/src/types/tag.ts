export interface Tag {
  id: string
  name: string
  color: string
  created_at: string
  usage_count: number
}

export type StoredTag = Omit<Tag, 'usage_count'>

export interface TagListData {
  items: Tag[]
}

export type TagDraft = Pick<Tag, 'name' | 'color'>
