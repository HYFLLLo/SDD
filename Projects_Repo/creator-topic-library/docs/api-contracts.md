# 接口契约

> 前端 Mock 和后端实现的唯一对齐依据。任何变更必须同步更新本文件。

## 通用约定

### 统一响应格式
成功：`{"code": 200, "message": "success", "data": { ... }}`
错误：`{"code": <错误码>, "message": "<错误描述>", "data": null}`
分页：`{"code": 200, "message": "success", "data": {"items": [...], "total": 100, "page": 1, "page_size": 20}}`

### HTTP 状态码
- 200：成功
- 400：参数错误
- 401：未认证
- 403：无权限
- 404：资源不存在
- 500：服务器内部错误

### 数据字段

选题 Topic：
- `id`: string
- `title`: string，必填
- `content`: string，可选
- `notes`: string，可选
- `source`: string，可选
- `tag_ids`: string[]，可选
- `status`: `pending | working | published | abandoned`
- `priority`: `high | medium | low`
- `created_at`: ISO 8601 datetime
- `updated_at`: ISO 8601 datetime

标签 Tag：
- `id`: string
- `name`: string，必填且唯一
- `color`: string，十六进制色值
- `created_at`: ISO 8601 datetime
- `usage_count`: number，关联选题数量

## 接口清单

### GET /api/topics

查询参数：
- `keyword`: string，可选，标题/内容/标签名称模糊搜索
- `status`: `pending | working | published | abandoned`，可选
- `priority`: `high | medium | low`，可选
- `tag_ids`: string，可选，逗号分隔的标签 ID
- `sort`: `created_desc | updated_desc | priority_desc`，可选，默认 `created_desc`
- `page`: number，默认 1
- `page_size`: number，默认 20

成功响应（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "topic-001",
        "title": "创作者如何建立自己的选题库",
        "content": "把零散灵感变成可检索、可执行的内容资产。",
        "notes": "",
        "source": "小红书评论区",
        "tag_ids": ["tag-001", "tag-002"],
        "status": "working",
        "priority": "high",
        "created_at": "2026-10-14T09:20:00+08:00",
        "updated_at": "2026-10-16T10:00:00+08:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

错误响应（400）：
```json
{"code": 400, "message": "status 参数不合法", "data": null}
```

### POST /api/topics

请求体：
```json
{
  "title": "创作者如何建立自己的选题库",
  "content": "把零散灵感变成可检索、可执行的内容资产。",
  "notes": "",
  "source": "小红书评论区",
  "tag_ids": ["tag-001", "tag-002"],
  "status": "pending",
  "priority": "medium"
}
```

成功响应（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "topic-001",
    "title": "创作者如何建立自己的选题库",
    "content": "把零散灵感变成可检索、可执行的内容资产。",
    "notes": "",
    "source": "小红书评论区",
    "tag_ids": ["tag-001", "tag-002"],
    "status": "pending",
    "priority": "medium",
    "created_at": "2026-10-16T10:20:00+08:00",
    "updated_at": "2026-10-16T10:20:00+08:00"
  }
}
```

错误响应（400）：
```json
{"code": 400, "message": "title 不能为空", "data": null}
```

### GET /api/topics/{id}

成功响应（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "topic-001",
    "title": "创作者如何建立自己的选题库",
    "content": "把零散灵感变成可检索、可执行的内容资产。",
    "notes": "",
    "source": "小红书评论区",
    "tag_ids": ["tag-001", "tag-002"],
    "status": "working",
    "priority": "high",
    "created_at": "2026-10-14T09:20:00+08:00",
    "updated_at": "2026-10-16T10:00:00+08:00"
  }
}
```

错误响应（404）：
```json
{"code": 404, "message": "选题不存在", "data": null}
```

### PUT /api/topics/{id}

请求体：
```json
{
  "title": "创作者如何建立自己的选题库",
  "content": "把零散灵感变成可检索、可执行的内容资产。",
  "notes": "补充标题角度",
  "source": "小红书评论区",
  "tag_ids": ["tag-001", "tag-002"],
  "status": "working",
  "priority": "high"
}
```

成功响应（200）：返回更新后的完整 Topic 对象，结构与 GET /api/topics/{id} 一致。

错误响应（400）：
```json
{"code": 400, "message": "title 不能为空", "data": null}
```

### DELETE /api/topics/{id}

成功响应（200）：
```json
{"code": 200, "message": "success", "data": {"deleted": true}}
```

错误响应（404）：
```json
{"code": 404, "message": "选题不存在", "data": null}
```

### GET /api/topics/random

查询参数：
- 使用当前筛选条件作为候选池，默认排除 `published`、`abandoned` 状态。
- `exclude_statuses`: string，可选，逗号分隔，默认 `published,abandoned`

成功响应（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "topic": {
      "id": "topic-003",
      "title": "一条视频如何拆成五个平台版本",
      "content": "围绕同一个选题，按平台语气改写标题、开头和结尾。",
      "notes": "",
      "source": "B站评论",
      "tag_ids": ["tag-003", "tag-004"],
      "status": "pending",
      "priority": "high",
      "created_at": "2026-10-15T21:10:00+08:00",
      "updated_at": "2026-10-15T21:10:00+08:00"
    }
  }
}
```

错误响应（200 空池）：
```json
{"code": 200, "message": "success", "data": {"topic": null}}
```

### GET /api/tags

查询参数：无

成功响应（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "tag-001",
        "name": "小红书",
        "color": "#C2571B",
        "created_at": "2026-10-01T09:00:00+08:00",
        "usage_count": 12
      }
    ]
  }
}
```

### POST /api/tags

请求体：
```json
{"name": "小红书", "color": "#C2571B"}
```

成功响应（200）：返回创建后的完整 Tag 对象。

错误响应（400）：
```json
{"code": 400, "message": "标签名称已存在", "data": null}
```

### PUT /api/tags/{id}

请求体：
```json
{"name": "小红书", "color": "#D98A4A"}
```

成功响应（200）：返回更新后的完整 Tag 对象。

错误响应（404）：
```json
{"code": 404, "message": "标签不存在", "data": null}
```

### DELETE /api/tags/{id}

成功响应（200）：
```json
{"code": 200, "message": "success", "data": {"deleted": true}}
```

错误响应（404）：
```json
{"code": 404, "message": "标签不存在", "data": null}
```
