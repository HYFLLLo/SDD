# 接口契约

> 前端 Mock 和后端实现的唯一对齐依据。任何变更必须同步更新本文件。
> 项目：画意接龙（draw-telephone）
> 最后更新：2026-08-19

## 通用约定

### 统一响应格式
- 成功：`{"code": 200, "message": "success", "data": { ... }}`
- 错误：`{"code": <错误码>, "message": "<错误描述>", "data": null}`
- 分页：`{"code": 200, "data": {"items": [...], "total": 100, "page": 1, "page_size": 20}}`

### HTTP 状态码约定
- 200 成功 / 400 参数错误 / 401 未认证 / 403 无权限 / 404 资源不存在 / 500 服务器内部错误

### 认证
- 除注册/登录/广场浏览/作品详情外，所有接口需 `Authorization: Bearer <access_token>` 头
- 游客可访问：GET /api/works、GET /api/works/{id}

### 数据类型
- `id` / `*_id`：uuid 字符串
- `datetime`：ISO 8601 字符串（如 "2026-08-19T13:49:07Z"）
- `chain_length`：整数 4-10
- `node_seq`：整数，从 0 开始

---

## 接口清单

### POST /api/auth/register
注册账号。

**请求体：**
```json
{"username": "string", "password": "string", "nickname": "string"}
```

**响应（成功 200）：**
```json
{"code": 200, "message": "success", "data": {"access_token": "string", "user": {"id": "uuid", "username": "string", "nickname": "string", "avatar_url": null}}}
```

**响应（失败 400）：**
```json
{"code": 400, "message": "用户名已存在", "data": null}
```

---

### POST /api/auth/login
登录。

**请求体：**
```json
{"username": "string", "password": "string"}
```

**响应（成功 200）：**
```json
{"code": 200, "message": "success", "data": {"access_token": "string", "user": {"id": "uuid", "username": "string", "nickname": "string", "avatar_url": null}}}
```

**响应（失败 401）：**
```json
{"code": 401, "message": "用户名或密码错误", "data": null}
```

---

### GET /api/works
广场作品流（游客可访问）。

**查询参数：**
- `page`：页码，默认 1
- `page_size`：每页条数，默认 20
- `sort`：排序，枚举 `latest`（最新，MVP 默认）/ `most_drift`（最跑偏，V1.1）/ `most_liked`（最多点赞，V1.2）

**响应（成功 200）：**
```json
{"code": 200, "data": {"items": [{"id": "uuid", "title": "戴帽子的猫", "chain_length": 6, "member_count": 5, "like_count": 128, "thumb_url": "string", "created_at": "datetime"}], "total": 100, "page": 1, "page_size": 20}}
```

---

### GET /api/works/{id}
作品详情（只读全链，游客可访问）。

**响应（成功 200）：**
```json
{"code": 200, "data": {"id": "uuid", "title": "戴帽子的猫", "chain_length": 6, "creator": {"id": "uuid", "nickname": "小A"}, "prompt_source": "ai", "prompt_text": "戴帽子的猫", "status": "completed", "created_at": "datetime", "completed_at": "datetime", "nodes": [{"id": "uuid", "seq": 0, "type": "draw", "author": {"id": "uuid", "nickname": "小A"}, "content_type": "image", "content_url": "string", "is_ai": false, "submitted_at": "datetime"}, {"id": "uuid", "seq": 1, "type": "describe", "author": {"id": "uuid", "nickname": "小B"}, "content_type": "text", "content_text": "一只戴礼帽的猫", "is_ai": false, "submitted_at": "datetime"}]}}
```

**响应（失败 404）：**
```json
{"code": 404, "message": "作品不存在", "data": null}
```

---

### POST /api/chains
创建链（需登录）。

**请求体：**
```json
{"title": "string（可选）", "chain_length": 6, "visibility": "invite", "prompt_source": "ai", "prompt_text": "string（prompt_source=manual 时必填）"}
```
- `visibility`：枚举 `invite`（邀请制）/ `public`（公开广场）
- `prompt_source`：枚举 `manual`（手动写题）/ `ai`（AI 生成）

**响应（成功 200）：**
```json
{"code": 200, "message": "success", "data": {"id": "uuid", "title": "戴帽子的猫", "chain_length": 6, "visibility": "invite", "room_code": "DRAW4", "prompt_source": "ai", "prompt_text": "戴帽子的猫", "status": "in_progress", "creator_id": "uuid", "created_at": "datetime", "expires_at": "datetime"}}
```

**响应（失败 400）：**
```json
{"code": 400, "message": "链长必须在 4-10 之间", "data": null}
```

---

### POST /api/ai/prompt
AI 起手题生成（需登录，调 DeepSeek）。

**请求体：**
```json
{"count": 1}
```

**响应（成功 200）：**
```json
{"code": 200, "data": {"prompts": ["戴帽子的猫"]}}
```

**响应（失败 503，AI 服务不可用）：**
```json
{"code": 503, "message": "AI 服务暂不可用，请手动输入题词", "data": null}
```

---

### GET /api/chains/{room_code}
按房间码查询链（加入前校验，需登录）。

**响应（成功 200）：**
```json
{"code": 200, "data": {"id": "uuid", "title": "戴帽子的猫", "chain_length": 6, "current_seq": 3, "status": "in_progress", "is_full": false, "remaining_slots": 2, "expires_at": "datetime"}}
```

**响应（失败 404）：**
```json
{"code": 404, "message": "房间码无效或链已过期", "data": null}
```

---

### POST /api/chains/{id}/join
加入链（需登录）。

**请求体：** 无

**响应（成功 200）：**
```json
{"code": 200, "data": {"chain_id": "uuid", "joined": true}}
```

**响应（失败 403）：**
```json
{"code": 403, "message": "链已满或已过期", "data": null}
```

---

### GET /api/chains/{id}
链大厅详情（链状态/进度/成员/当前节点，需链成员权限）。

**响应（成功 200）：**
```json
{"code": 200, "data": {"id": "uuid", "title": "戴帽子的猫", "chain_length": 6, "visibility": "invite", "room_code": "DRAW4", "prompt_source": "ai", "prompt_text": "戴帽子的猫", "status": "in_progress", "current_seq": 3, "current_node_type": "draw", "current_author": {"id": "uuid", "nickname": "小C"}, "ai_countdown_at": "datetime", "members": [{"id": "uuid", "nickname": "小A", "avatar_url": null}], "nodes": [{"seq": 0, "type": "draw", "author": {"id": "uuid", "nickname": "小A"}, "is_ai": false, "submitted_at": "datetime"}], "created_at": "datetime", "expires_at": "datetime"}}
```
- `ai_countdown_at`：当前节点 AI 补位触发时间（24h 倒计时终点），null 表示非当前责任人或无需倒计时

**响应（失败 403）：**
```json
{"code": 403, "message": "无权访问该链", "data": null}
```

---

### GET /api/nodes/{id}/previous
获取上一节点内容（接力作画/描述页，防剧透，只能看上一节点）。

**响应（成功 200）：**
```json
{"code": 200, "data": {"node_id": "uuid", "seq": 2, "type": "draw", "content_type": "image", "content_url": "string"}}
```
- 描述节点的上一节点是画（content_type=image）；画节点的上一节点是述（content_type=text, content_text）

**响应（失败 403）：**
```json
{"code": 403, "message": "当前未轮到你", "data": null}
```

---

### POST /api/nodes/{id}/submit
提交节点（接力，需当前节点责任人）。

**请求体（画节点）：**
```json
{"content_type": "image", "content_url": "string（上传后的图像 URL）"}
```

**请求体（描述节点）：**
```json
{"content_type": "text", "content_text": "一只戴礼帽的猫"}
```

**响应（成功 200）：**
```json
{"code": 200, "data": {"node_id": "uuid", "seq": 2, "status": "submitted", "next_seq": 3, "chain_status": "in_progress"}}
```

**响应（失败 403）：**
```json
{"code": 403, "message": "当前未轮到你", "data": null}
```

---

### POST /api/upload/image
上传画作图片（画节点提交前，需登录）。

**请求体：** `multipart/form-data`，字段 `file`（PNG，固定画布尺寸）

**响应（成功 200）：**
```json
{"code": 200, "data": {"url": "string", "size": 102400}}
```

**响应（失败 400）：**
```json
{"code": 400, "message": "文件格式不支持", "data": null}
```

---

### POST /api/chains/{id}/votes
提交投票（链完成后，需链成员权限，三维度各一票）。

**请求体：**
```json
{"votes": [{"dimension": "most_drift", "target_node_id": "uuid"}, {"dimension": "best_draw", "target_node_id": "uuid"}, {"dimension": "best_describe", "target_node_id": "uuid"}]}
```
- `dimension`：枚举 `most_drift`（最跑偏）/ `best_draw`（最佳画）/ `best_describe`（最佳描述）

**响应（成功 200）：**
```json
{"code": 200, "data": {"results": [{"dimension": "most_drift", "target_node_id": "uuid", "vote_count": 3}, {"dimension": "best_draw", "target_node_id": "uuid", "vote_count": 2}, {"dimension": "best_describe", "target_node_id": "uuid", "vote_count": 4}]}}
```

**响应（失败 403）：**
```json
{"code": 403, "message": "链未完成或无权投票", "data": null}
```

---

### GET /api/chains/{id}/votes/result
投票结果（链完成后）。

**响应（成功 200）：**
```json
{"code": 200, "data": {"results": [{"dimension": "most_drift", "target_node_id": "uuid", "target_author": {"id": "uuid", "nickname": "小D"}, "vote_count": 3}, {"dimension": "best_draw", "target_node_id": "uuid", "target_author": {"id": "uuid", "nickname": "小E"}, "vote_count": 2}, {"dimension": "best_describe", "target_node_id": "uuid", "target_author": {"id": "uuid", "nickname": "小A"}, "vote_count": 4}]}}
```

---

### GET /api/users/me/works
我的作品（需登录）。

**查询参数：** `page`、`page_size`

**响应（成功 200）：**
```json
{"code": 200, "data": {"items": [{"id": "uuid", "title": "戴帽子的猫", "chain_length": 6, "status": "completed", "role": "creator", "thumb_url": "string", "created_at": "datetime"}], "total": 12, "page": 1, "page_size": 20}}
```

---

### GET /api/notifications
通知列表（需登录）。

**查询参数：** `page`、`page_size`、`unread_only`（bool，默认 false）

**响应（成功 200）：**
```json
{"code": 200, "data": {"items": [{"id": "uuid", "type": "your_turn", "chain_id": "uuid", "chain_title": "戴帽子的猫", "read": false, "created_at": "datetime"}], "total": 3, "page": 1, "page_size": 20}}
```
- `type`：枚举 `your_turn`（轮到你了）/ `chain_done`（链完成）/ `node_submitted`（节点提交）

---

### POST /api/notifications/read
标记通知已读。

**请求体：**
```json
{"notification_ids": ["uuid"]}
```

**响应（成功 200）：**
```json
{"code": 200, "data": {"read_count": 3}}
```

---

### GET /api/users/me
个人资料（需登录）。

**响应（成功 200）：**
```json
{"code": 200, "data": {"id": "uuid", "username": "string", "nickname": "string", "avatar_url": null, "created_at": "datetime", "participated_chains": 12, "created_chains": 3}}
```

---

## WebSocket 接口

### WS /ws/room/{chain_id}
链大厅实时围观 + 通知推送。

**客户端 → 服务端：**
```json
{"type": "subscribe", "chain_id": "uuid"}
```

**服务端 → 客户端（订阅确认）：**
```json
{"type": "subscribed", "chain_id": "uuid"}
```

**服务端 → 客户端（笔迹事件，广播给同房间在线成员）：**
```json
{"type": "stroke", "chain_id": "uuid", "node_id": "uuid", "points": [{"x": 120, "y": 80, "pressure": 0.5}], "color": "#2B2622", "size": 3}
```

**服务端 → 客户端（通知事件）：**
```json
{"type": "notify", "event": "your_turn", "chain_id": "uuid", "node_seq": 3}
```
- `event`：枚举 `your_turn` / `chain_done` / `node_submitted` / `ai_filled`（AI 补位完成）

**客户端 → 服务端（作画时推送笔迹，仅当前节点责任人）：**
```json
{"type": "stroke", "chain_id": "uuid", "node_id": "uuid", "points": [{"x": 120, "y": 80, "pressure": 0.5}], "color": "#2B2622", "size": 3}
```

**服务端 → 客户端（错误）：**
```json
{"type": "error", "message": "未认证"}
```

---

## 错误码汇总

| code | 含义 |
|------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 外部服务不可用（AI 服务降级） |
