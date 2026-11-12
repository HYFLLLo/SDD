# 测试报告：T-002 txt 解析与章节入库（含前端联调）

**测试时间**：2026-09-14 15:48 ~ 16:02
**Tester Agent ID**：tester (Claude Code subagent)

## 结果：PASS

> 第 3 轮复审。第 2 轮发现的 `book_desc` NOT NULL 缺陷已修复：`doUploadBook()` 对空简介兜底为空串，真实上传「简介留空」合法 txt → `code:00000`、`book_desc` 落库为空串（`LENGTH=0`）满足 NOT NULL。全部 6 条 acceptanceCriteria + 上轮缺陷回归 + 全链路真实联调均通过，测试数据已清理。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 合法 .txt 上传 → 成功 + 展示章节/字数 | **PASS** | 真实 multipart 上传 2 章 UTF-8 txt：`code:00000`，`chapterCount:2`，`wordCount:32`。另验证「简介留空」「简介空串」两种边界均为 `00000`。 |
| 2 | 上传后出现在首页推荐或搜索结果 | **PASS** | `/api/front/search/books?keyword=书名` → `total:1` 精确命中（ES disabled，DB 搜索，UTF-8 无乱码）。 |
| 3 | 点击可正常分章阅读，章节内容与 txt 一致 | **PASS** | 详情 `GET /front/book/{id}`（`picUrl=/img/default-cover.gif`）、章节列表（2 章名正确）、`content/{chapterId}` 正文顶层 `bookContent` 字段与上传 txt 逐字一致。 |
| 4 | >100MB → 「文件大小超过限制」 | **PASS（代码路径）** | `application.yml` `max-file-size:100MB`；`CommonExceptionHandler.handlerMaxUploadSizeExceededException` → `A0702`（专用 handler 优先于 `Exception` 兜底）。静态验证成立。 |
| 5 | 非 txt/epub（.pdf）→ 「不支持的文件格式」 | **PASS** | 实测上传 `.pdf` → `{"code":"A0703","message":"不支持的文件格式"}`。 |
| 6 | 空文件/无有效章节 → 提示解析失败，不产生脏数据 | **PASS** | 实测空 txt → `{"code":"A0706","message":"文件为空"}`，DB 0 落库。 |

## 上轮缺陷回归（book_desc NOT NULL）

| 场景 | 结果 | 证据 |
|--------|------|------|
| 简介留空上传（表单不带 bookDesc，前端允许选填） | **PASS** | `code:00000`，`SELECT LENGTH(book_desc)` = 0（空串落库，满足 NOT NULL）。本次复审的复现点，已消除。 |
| 简介为空串显式传 | **PASS** | `code:00000`，`LENGTH(book_desc)=0`。 |
| 正常简介上传 | **PASS** | `code:00000`，简介正确落库。 |
| 上轮 picUrl 缺陷 | **PASS** | `setPicUrl("/img/default-cover.gif")` 在 insert 前；`pic_url` 落库 `/img/default-cover.gif`；静态封面 `GET /img/default-cover.gif` → 200 image/gif 10189B。 |

## 数据库落盘验证（真实数据）

| 验证项 | 结果 | 证据 |
|--------|------|------|
| `book_info` 建书 | PASS | pic_url/book_name/author_id/author_name/book_desc/score 全赋值，INSERT 成功 |
| `book_info.word_count` / `last_chapter_id` | PASS | word_count=32，last 章正确 |
| `book_chapter`（2 章） | PASS | chapter_num 0/1，章名正确 |
| `book_content` 正文 | PASS | 2 行，UTF-8 逐字无损 |
| 事务完整性 | PASS | 空文件/pdf/同名等失败路径均无任何脏数据——confirm 无半本书 |

## 代码质量抽检

- `book_desc` 兜底：`setBookDesc(StringUtils.hasText(dto.getBookDesc()) ? dto.getBookDesc().trim() : "")`（`BookUploadServiceImpl.java:137-139`）——正确，空串满足 NOT NULL
- `book_name` 兜底：`"未命名书籍-" + 时间戳`（`:130-132`）——空名也有占位，`@ModelAttribute` 绑定漏带/空白均安全
- `pic_url` 兜底（上轮已修）：`:141` `setPicUrl("/img/default-cover.gif")`，insert 前
- 对照 `SHOW COLUMNS WHERE Null='NO' AND Default IS NULL`：book_info 剩余 NOT NULL 无默认列 = id(auto)/pic_url/book_name/author_id/author_name/book_desc/score — 全部在 doUploadBook 显式赋值
- `@Transactional(rollbackFor = Exception.class)` 完整；无硬编码新密钥、无 TODO/FIXME/HACK；缓存清理在事务内

## 前端集成验证

- `BookUpload.vue`：无 Mock 残留，`uploadBook()` 走真实 API；`form.bookDesc` 可空（选填）逻辑正确
- `src/api/book.js`：`uploadBook` → `POST /front/resource/book/upload`，`headers:{'Content-Type': undefined}`（FormData boundary）
- `.env.development`：`VUE_APP_BASE_API_URL = http://127.0.0.1:8888/api` 指向真实后端
- 路由：`/book_upload`（顶层）+ `/book/:id`（上传成功后跳阅读页）均已注册
- `npm run build` 成功，dist 含「上传图书」入口文案

## 环境验证

- 后端：PID 8240（java，2026-09-14 15:48 启动，`logs/bugfix-run.log` 显示 Tomcat started on 8888），对应当前源码
- 静态资源：`target/classes/static/img/default-cover.gif` 已随构建打包，`/img/**` HTTP 200
- MySQL 3306（测试库 novel）/ Redis 6379 正常
- 回归：`GET /api/front/home/books` → `code:00000`（31 本）
- **清理确认**：本轮 3 本测试书（约 6 章节）已删；`book_info=107`、`book_chapter=11137`、`book_content=11137`（与测试前基线一致），seed 未动，无残留

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | seed 107 本封面 `/localPic/**` 本地后端未服务（仅 `/image/**` 读磁盘），本地详情页封面 404，线上由 CDN 提供 | 仓库既有状态 | 非本缺陷，不做处理 |

## 系统级经验

（第 2 轮已记录：数据库写入类任务必须对照 `SHOW COLUMNS WHERE Null='NO' AND Default IS NULL` 穷尽赋值 + 可空表单字段单独构造留空真实请求。本轮验证该规则生效——修复按此执行并通过。）