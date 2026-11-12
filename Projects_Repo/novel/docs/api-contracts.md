---

## description: API 契约（反向整理 + 新增上传图书接口）。现有接口由代码库逆向，新增接口为本需求定义。

# novel API 契约

> 现有接口部分由代码库反向整理（来源：`src/main/java/io/github/xxyopen/novel/controller/**` 与 `dto/**`），供本次开发对齐；标注 `[现有]`。新增接口为本需求定义，标注 `[新增]`。
>
> **全局统一响应封装 `RestResp`**：
> ```json
> { "code": "00000", "message": "成功", "data": <业务数据|null> }
> ```
> - `code`：字符串，"00000" 为成功；`A` 前缀=用户端错误，`B` 前缀=系统错误，`C` 前缀=第三方错误。
> - 所有 `Number` 字段（含 ID）在 JSON 中一律序列化为 **字符串**（`jackson.write-numbers-as-strings: true`，避免前端精度丢失）。

---

## 1. 新增接口：上传图书 `[新增]`

### 1.1 `POST /api/front/resource/book/upload` — 上传并解析电子书

> 归属说明：该接口放在 **前台 `front/resource`** 下（与现有 `POST /api/front/resource/image` 同级），**免登录**，无 AuthInterceptor 拦截（`WebConfig` 的拦截范围只有 `/api/front/user/**`、`/api/author/**`、`/api/admin/**`）。

#### 请求

- 内容类型：`multipart/form-data`
- 请求参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | MultipartFile | 是 | 电子书文件，仅接受 `.txt` / `.epub`，大小上限 100MB |
| `bookName` | String | 是 | 书名（表单） |
| `authorName` | String | 否 | 作者名（表单），为空默认「匿名用户」 |
| `workDirection` | Integer | 是 | 作品方向：0-男频 1-女频 |
| `categoryId` | Long | 是 | 分类 ID（来自 `GET /api/front/book/category/list`） |
| `categoryName` | String | 是 | 分类名称 |
| `bookDesc` | String | 否 | 书籍简介 |

#### 响应 `RestResp<BookUploadRespDto>`

| 字段 | 类型 | 说明 |
|------|------|------|
| `bookId` | String(Long) | 新上传图书的 ID（字符串） |
| `bookName` | String | 书名 |
| `chapterCount` | Integer | 解析出的章节数量 |
| `wordCount` | Integer | 总字数 |
| `message` | String | 成功提示语（如「上传成功，共解析 N 章」） |

示例：
```json
{
  "code": "00000",
  "message": "成功",
  "data": {
    "bookId": "1334318182169681920",
    "bookName": "示例小说",
    "chapterCount": 13,
    "wordCount": 12890,
    "message": "上传成功，共解析 13 章"
  }
}
```

#### 错误响应（`RestResp.fail(...)`）

| code | message | 触发条件 |
|------|---------|----------|
| `A0702` | 文件大小超过限制 | 超过 max-file-size |
| `A0703` | 不支持的文件格式 | 非 .txt/.epub |
| `A0704` | 图书文件解析失败 | 解析异常 / 无有效章节 |
| `A0705` | 书名已存在 | 同名书已存在（复用作者后台 `AUTHOR_BOOK_NAME_EXIST` 语义） |
| `A0706` | 文件为空 | 上传了空文件 |

> 若新增错误码需在 `ErrorCodeEnum` 中注册（A0702~A0706 为建议值，可调整）。

### 1.2 技术实现要点（写入契约供 Developer 对齐）

- **解析库**：txt 用 JDK 内置字符集识别 + 正则切章；epub 用 JDK 内置 zip + 新增 `jsoup` 依赖提取正文。
- **入库事务**：整本上传作为一个事务（建书 + 全量章节），任一步失败全部回滚，不产生半本书。
- **author_id 归属**：`0`（匿名），`author_name` 取表单值（默认「匿名用户」）。
- **章节写入**：复用 `book_chapter` / `book_content` 的 MP `BaseMapper.insert`，`chapter_num` 从 0 递增，`wordCount = content.length()`，更新 `book_info.lastChapter*` / `wordCount`。
- **缓存**：写入后清理对应 `book_info` / 章节 Caffeine 缓存。
- **MQ**：`spring.amqp.enabled=false`（关闭），章节变更 MQ 在事务提交后发送但不会真正投递，不影响功能。

---

## 1A. 新增接口：我的上传（管理员管理上传图书）`[新增 2026-10-20]`

> 与第 1 节「上传图书」同属前台资源链路，但归属与权限语义不同：本节接口**需要登录**且**仅管理员可用**。

### 1A.1 `GET /api/front/upload/books` — 我的上传分页列表

#### 请求

- 认证：请求头 `Authorization: <JWT>`，需前台登录态 + 管理员账号。
- 查询参数（继承 `PageReqDto`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pageNum` | int | 否 | 页码，默认 1 |
| `pageSize` | int | 否 | 每页条数，默认 10 |
| `bookStatus` | Integer | 否 | 筛选：0-连载中 1-已完结；不传为全部 |

#### 响应 `RestResp<PageRespDto<UploadBookRespDto>>`

`UploadBookRespDto`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(Long) | 图书 ID（字符串） |
| `bookName` | String | 书名 |
| `authorName` | String | 作者名 |
| `categoryName` | String | 分类名 |
| `picUrl` | String | 封面地址 |
| `wordCount` | Integer | 总字数 |
| `chapterCount` | Integer | 章节数 |
| `bookStatus` | Integer | 0-连载中 1-已完结 |
| `createTime` | String | 上传时间（`yyyy-MM-dd HH:mm:ss`） |

排序：`create_time` 倒序；`uploader_id = 当前用户 id`。

示例：
```json
{
  "code": "00000",
  "message": "成功",
  "data": {
    "pageNum": 1,
    "pageSize": 10,
    "total": 1,
    "pages": 1,
    "list": [
      {
        "id": "1431630596354977796",
        "bookName": "仙逆",
        "authorName": "匿名用户",
        "categoryName": "仙侠",
        "picUrl": "/img/default-cover.gif",
        "wordCount": 12345,
        "chapterCount": 13,
        "bookStatus": 0,
        "createTime": "2026-10-20 15:19:31"
      }
    ]
  }
}
```

### 1A.2 `PUT /api/front/upload/book/{bookId}/status` — 切换图书状态

#### 请求

- 认证：同上（管理员）。
- 路径参数：`bookId`（Long）
- 请求体：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `bookStatus` | Integer | 是 | 目标状态：0-连载中 1-已完结 |

```json
{ "bookStatus": 1 }
```

#### 响应 `RestResp<Void>`

#### 错误响应

| code | message | 触发条件 |
|------|---------|----------|
| `A0230` | 用户登录已过期 | 未携带或无效 token |
| `A0301` | 访问未授权 | 已登录但非管理员 |
| `A2002` | 小说ID不存在 | bookId 不存在或不属于当前用户 |
| `A0400` | 用户请求参数错误 | `bookStatus` 不是 0/1 |

### 1A.3 `PUT /api/front/upload/book/{bookId}/author` — 修改上传图书作者名

#### 请求

- 认证：请求头 `Authorization: <JWT>`，需前台登录态 + 管理员账号。
- 路径参数：`bookId`（Long）
- 请求体：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `authorName` | String | 是 | 作者名（纯文字，最长 50 字符） |

```json
{ "authorName": "作者名" }
```

#### 响应 `RestResp<Void>`

#### 错误响应

| code | message | 触发条件 |
|------|---------|----------|
| `A0230` | 用户登录已过期 | 未携带或无效 token |
| `A0301` | 访问未授权 | 已登录但非管理员 |
| `A2002` | 小说ID不存在 | bookId 不存在或不属于当前用户 |
| `A0400` | 用户请求参数错误 | authorName 为空或超过 50 字符 |

> 说明：该接口只更新 `book_info.author_name`（纯文字），不修改 `author_id`，也不操作 `author_info` 作者表。
### 1A.4 技术实现要点（写入契约供 Developer 对齐）

- **归属字段**：`book_info` 新增 `uploader_id bigint unsigned NOT NULL DEFAULT 0`，加索引 `idx_uploader_id`。上传接口 `BookUploadServiceImpl` 在入库时读取 `UserHolder.getUserId()`（可为 null → 0）写入。
- **上传链路取登录态**：`/api/front/resource/**` 目前不被 `AuthInterceptor` 拦截、也没有 `TokenParseInterceptor`。需在 `WebConfig` 给 `/api/front/resource/book/upload` 挂 `TokenParseInterceptor`（只解析不拦截），使匿名上传仍可用、登录上传能取到 userId。
- **管理员账号初始化**：启动时幂等创建（`user_info.username = 'admin'` 不存在则插入，密码 `MD5("admin")`，`salt='0'`，`status=0`）。账号/密码可在 `application.yml` 的 `novel.admin.*` 配置，默认 `admin/admin`。**文档不写任何真实生产密码**。
- **管理员判定**：查询 `user_info` 的 `username` 是否为配置的管理员账号名；非管理员抛 `A0301`。
- **拦截配置**：`WebConfig` 把 `/api/front/upload/**` 加入 `AuthInterceptor` 拦截前缀。
- **缓存**：切换状态后清理 `BookInfoCacheManager` 的 Caffeine 缓存，保证前台详情页即时生效。

## 1B. 新增接口：用户阅读进度 `[新增 2026-10-21]`

> 阅读进度属于会员数据，挂载在 `/api/front/user/**` 下，走 `AuthInterceptor`，**需要前台登录态**。前端未登录时不调用。

### 1B.1 `POST /api/front/user/read_history` — 保存阅读进度

#### 请求

- 认证：请求头 `Authorization: <JWT>`。
- Content-Type：`application/json`。

```json
{
  "bookId": "1334332598936240128",
  "chapterId": "1334332601092112384"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `bookId` | Long | 是 | 小说 ID（JSON 中可传字符串） |
| `chapterId` | Long | 是 | 当前阅读章节 ID |

#### 响应

`RestResp<Void>`。成功时 `code=00000`。

#### 错误响应

| code | message | 触发条件 |
|------|---------|----------|
| `A0230` | 用户登录已过期 | 未携带或无效 token |
| `A2002` | 小说ID不存在 | 章节对应内容不存在 |
| `A0400` | 用户请求参数错误 | `bookId` / `chapterId` 为空 |

### 1B.2 `GET /api/front/user/read_history/{bookId}` — 查询阅读进度

#### 请求

- 认证：请求头 `Authorization: <JWT>`。
- 路径参数：`bookId`，小说 ID。

#### 响应 `RestResp<Long>`

返回上次阅读的**章节 ID**；无阅读记录时 `data=null`。

```json
{
  "code": "00000",
  "message": "成功",
  "data": "1334332601092112384"
}
```

### 1B.4 `GET /api/front/user/read_history/list` — 分页查询阅读历史

#### 请求

- 认证：请求头 `Authorization: <JWT>`。
- 查询参数（继承 `PageReqDto`）：`pageNum` 默认 1，`pageSize` 默认 10。

#### 响应 `RestResp<PageRespDto<UserReadHistoryRespDto>>`

`UserReadHistoryRespDto`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `bookId` | String(Long) | 小说 ID |
| `bookName` | String | 小说名 |
| `picUrl` | String | 封面地址 |
| `authorName` | String | 作者名 |
| `chapterId` | String(Long) | 上次阅读章节 ID |
| `chapterName` | String | 上次阅读章节名 |
| `updateTime` | String | 阅读时间，格式 `yyyy-MM-dd HH:mm` |

前端点击记录跳转：`/book/{bookId}/{chapterId}`。

### 1B.3 技术实现要点

- 表：`user_read_history`，唯一键 `uk_userId_bookId(user_id, book_id)`；`pre_content_id` 存 `book_content.id`，查询时再映射回 `book_content.chapter_id`。
- 保存为 upsert：存在 `(user_id, book_id)` 则更新 `pre_content_id/update_time`，否则插入。
- 前端：阅读页加载正文后保存进度；书籍详情页「点击阅读」优先使用查询到的章节 ID，无记录时回退 `BookInfoRespDto.firstChapterId`。

## 2. 现有接口索引（由代码库反向整理，本次只读/复用）`[现有]`

> 以下接口为项目现有一级路由，本次开发不在契约层面修改它们，仅供对齐调用关系。响应结构以 `RestResp` 统一封装。

### 2.1 前台 `front`

| 前缀 | 接口 | 方法 | 说明 |
|------|------|------|------|
| `/api/front/home` | `books` | GET | 首页推荐图书，`List<HomeBookRespDto>` |
| `/api/front/home` | `friend_Link/list` | GET | 友情链接 |
| `/api/front/book` | `category/list?workDirection=` | GET | 分类列表（上传页下拉用）`List<BookCategoryRespDto>` |
| `/api/front/book` | `{id}` | GET | 图书详情 `BookInfoRespDto` |
| `/api/front/book` | `chapter/list?bookId=` | GET | 章节目录 `List<BookChapterRespDto>` |
| `/api/front/book` | `content/{chapterId}` | GET | 章节正文 `RestResp<BookContentAboutRespDto>` |
| `/api/front/book` | `last_chapter/about` / `pre_chapter_id` / `next_chapter_id` | GET | 阅读辅助 |
| `/api/front/book` | `visit_rank` / `newest_rank` / `update_rank` | GET | 排行榜 |
| `/api/front/search` | `books` | GET | 关键词搜索 `PageRespDto<BookInfoRespDto>` |
| `/api/front/resource` | `img_verify_code` | GET | 图片验证码 |
| `/api/front/resource` | `image` | POST | 图片上传（封面/头像，`MultipartFile`） |
| `/api/front/news` | `latest_list`/`{id}` | GET | 新闻 |
| `/api/front/user/**` | 见下方 | — | 需登录（Auth 拦截） |

### 2.2 作家 `author`（需作家权限）

| 前缀 | 接口 | 方法 | 说明 |
|------|------|------|------|
| `/api/author` | `register` | POST | 作家注册（登录态） |
| `/api/author` | `status` | GET | 作家状态 |
| `/api/author` | `book` | POST | 新增图书（表单元数据）`BookAddReqDto` |
| `/api/author` | `books` | GET | 我的图书列表 |
| `/api/author` | `book/chapter/{bookId}` | POST | 发布章节 `ChapterAddReqDto`（content≥50字） |
| `/api/author` | `book/chapter/{chapterId}` | GET/PUT/DELETE | 章节查看/编辑/删除 |
| `/api/author` | `book/chapters/{bookId}` | GET | 书籍章节列表 |
| `/api/author/ai` | `expand/condense/continue/polish` | POST | AI 润色（text+ratio/length） |

### 2.3 管理员 `admin`

项目定义了 `/api/admin/**` 前缀与拦截器，但**没有 admin Controller**。本次及后续均不新增。

---

## 3. 关联 DTO 字段清单（用于数据对齐）

### `BookAddReqDto`（作者建书表单，`[现有]`）

`workDirection(Integer,必填)`、`categoryId(Long,必填)`、`categoryName(String,必填)`、`picUrl(String,必填)`、`bookName(String,必填)`、`bookDesc(String,必填)`、`isVip(Integer,必填)`

> 注意：作者建书**要求** `picUrl` 必填（封面）。**上传图书**不要求封面，允许 `pic_url` 为空/默认图。

### `BookInfoRespDto`（`[现有]`）

`id, categoryId, categoryName, picUrl, bookName, authorId, authorName, bookDesc, bookStatus, visitCount, wordCount, commentCount, firstChapterId, lastChapterId, lastChapterName, updateTime`

### `BookChapterRespDto`（`[现有]`）

`id, bookId, chapterNum, chapterName, chapterWordCount, chapterUpdateTime, isVip`

---

## 4. 统一错误码 `ErrorCodeEnum`（`[现有]`）

| code 前缀 | 含义 |
|-----------|------|
| `A0001` 级 | 用户端错误 |
| `A0100` | 注册 |
| `A0230` | 登录过期 |
| `A0301` | 访问未授权 |
| `A0700` / `A0701` | 上传异常 / 上传类型不匹配 |
| `A3001` | 小说名已存在 |
| `B0001` | 系统错误 |
| `C0001` 级 | 第三方错误 |

## 1C. 新增接口：管理员全站书籍管理 `[新增 2026-10-21]`

> 与“我的上传”同挂 `/api/front/upload/**`，需要前台登录态，且仅 `novel.admin.username` 配置的管理员账号可用。

### 1C.1 `GET /api/front/upload/books/admin` — 全站书籍分页列表

- 认证：`Authorization: <JWT>`，管理员。
- 查询参数：继承 `PageReqDto`；`bookName` 可选书名模糊查询；`bookStatus` 可选 0/1。
- 响应：`RestResp<PageRespDto<UploadBookRespDto>>`，列表项包含 `id/workDirection/categoryId/bookName/authorName/categoryName/picUrl/bookDesc/wordCount/chapterCount/bookStatus/lastChapterName/createTime/updateTime`。

### 1C.2 `PUT /api/front/upload/book/{bookId}` — 修改基础信息

请求体字段：`bookName`、`authorName`、`workDirection`、`categoryId`、`categoryName`、`bookDesc`、`bookStatus`。所有 NOT NULL 字段必填；书名/作者按唯一键 `uk_bookName_authorName` 校验。

### 1C.3 `PUT /api/front/upload/book/{bookId}/pic` — 修改封面

请求体字段：`picUrl`，来自 `POST /api/front/resource/image` 返回的相对路径。

### 1C.4 `POST /api/front/upload/book/{bookId}/content` — 替换全书内容

- Content-Type：`multipart/form-data`。
- 表单字段：`file`（.txt / .epub）。
- 行为：事务内删除旧章节与正文、重置该书阅读进度、重新解析写入全部章节、更新 `wordCount/lastChapter*`，并清理相关缓存。

### 1C.5 `DELETE /api/front/upload/book/{bookId}` — 删除书籍

- 行为：删除章节、正文、阅读历史、书架、首页推荐、评论及评论回复，最后删除 `book_info`。
