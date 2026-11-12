---

## description: 开发计划（反向整理 + 上传图书功能的开发清单）。

# novel 开发计划 Plan

> 由「导入已有项目」反向整理。标注 `[现有]` 的为已实现，`[新增]` 的为本次「上传图书」需求。

## 1. 运行信息（既有，非默认端口表）

| 项 | 值 |
|----|----|
| 后端端口 | `8888` |
| 前端端口 | `1024` |
| 后端启动 | `java -jar target/novel-3.5.1-SNAPSHOT.jar`（或 `mvnw spring-boot:run`），需本机 MySQL/Redis 就绪 |
| 前端启动 | `npm run serve`（yarn 已移除） |

## 2. 状态盘点

### 2.1 已实现（`[现有]`）

- 前台阅读：首页 / 搜索 / 目录 / 正文 / 排行榜 / 评论
- 用户体系：注册 / 登录 / 书架
- 作者后台：建书 / 逐章发布 / AI 润色
- 图片上传（封面/头像）
- 数据库搜索兜底（ES 关闭）

### 2.2 本次开发（`[新增]`）— 上传图书

| 功能 | 描述 | 依赖 |
|------|------|------|
| 前端上传页面 | 单页：文件选择 + 信息表单 + 提交/结果反馈 | 复用 `BookAdd.vue` 风格 |
| 后端上传接口 | `POST /api/front/resource/book/upload` | 前端页面 |
| 文件解析 | txt（编码识别 + 正则切章）、epub（zip + jsoup 提取正文切章） | — |
| 入库 | 建书 + 全量章节（单事务） | 现有 MP `BaseMapper` |
| 配置调整 | `max-file-size`/`max-request-size`→100MB；`file.upload.path`→Windows 路径 | — |

## 3. 待开发功能清单（按交付顺序）

### T-后端-001：上传配置与占位接口

- 调整 `application.yml`：`max-file-size`/`max-request-size`→100MB；`novel.file.upload.path`→Windows 路径
- 新增 `BookUploadReqDto`（元数据+文件）与 `BookUploadRespDto`
- 新增 `BookUploadService`/`BookUploadController`，接口 `POST /api/front/resource/book/upload`
- 新增 `ErrorCodeEnum`：`A0702`（过大）/`A0703`（格式）/`A0704`（解析失败）/`A0705`（重名）/`A0706`（空文件）

### T-后端-002：txt 解析 + 章节入库

- txt 编码识别（UTF-8 BOM / UTF-8 / GBK）
- 章节切分正则（`第[0-9一二三四五六七八九十百千]+[章节回]` 等），无章节标题整篇单章
- 单事务入库（建 book_info + 逐章 book_chapter/book_content + 更新 book_info 最新章节/字数）
- 复用现有 MP `BaseMapper` 与缓存清理

### T-后端-003：epub 解析 + 章节入库

- 引入 `jsoup` 依赖
- JDK 内置 zip 解压，按 spine 顺序提取正文
- 清洗 HTML → 纯文本 → 复用章节切分与入库逻辑

### T-前端-001：上传图书页面

- 路由 `/book_upload`（前台，免登录）
- 页面：文件选择（accept=.txt,.epub）+ 书名/作者/分类/方向/简介表单
- 提交 `POST /api/front/resource/book/upload`，展示解析进度与结果（成功/错误）
- 复用 `BookAdd.vue` 风格与 `el-upload`，支持大文件（100MB）

### T-集成-001：端到端验证

- 真实启动后端+前端，上传样例 txt/epub，验证入库、搜索命中、前台可读

## 3A. 增量开发清单：我的上传（2026-10-20 修整）

| 功能 | 描述 | 依赖 |
|------|------|------|
| 归属字段 | `book_info.uploader_id` + 索引；上传链路取登录态写入 | 现有 `UserHolder` |
| 管理员账号 | 启动幂等创建 `admin/admin`（`user_info`），沿用现有前台登录 | — |
| 管理接口 | `GET /api/front/upload/books`、`PUT /api/front/upload/book/{id}/status` | 归属字段 + 管理员判定 |
| 前端入口 | 导航栏「我的上传」（仅 admin 可见）、路由 `/my_upload` | 管理接口 |
| 管理页 | 分页列表 + 状态筛选 + 状态切换 | 前端入口 |

> 口径来源见 PRD 第 3A 节、api-contracts 第 1A 节。

## 4. 外部服务与测试权限清单（开发门禁用）

| 服务 | 用途 | 是否本次需要 | 配置状态 | Tester 联调权限 |
|------|------|-------------|----------|----------------|
| MySQL 8（本机） | 数据存储 | 是 | 已运行 | 有（本机 root） |
| Redis 5（本机） | 缓存 | 是 | 已运行 | 有（本机） |
| Elasticsearch | 全文搜索 | 否（关闭，DB 兜底） | 关闭 | 不需要 |
| Spring AI | 作者后台 AI 润色 | 否（本次不涉及上传链路） | 遗留真实 key | 不需要 |
| RabbitMQ / XXL-JOB / SBA | MQ/调度/监控 | 否 | 全部关闭 | 不需要 |

> 结论：**上传图书功能不引入新的外部服务依赖**，无 Key 需要向用户索取；Tester 用本机 MySQL/Redis 即可完成真实联调。

## 5. 增量开发清单：全局主题切换（2026-10-29 修整）

> 口径来源见 PRD 第 7 节。纯前端改动，后端零变更，不新增外部依赖。

**现状盘点（已实测）**：颜色硬编码约 1091 处 —— 全局 CSS 约 274 处（`base.css` / `main.css` / `book.css` / `about.css` / `user.css` / `read.css`），`.vue` 文件约 817 处（`BookContent.vue` 81、author 系列各 66、登录/注册/用户中心各约 60）。`easyui.css` 为第三方遗留样式，不在改造范围。

| 功能 | 描述 | 依赖 |
|------|------|------|
| 主题基础设施 | 新建主题变量文件（`:root` 浅色 / `html.dark` 深色）、主题 composable（读写 `localStorage` + 切换 `<html>.dark`）、引入 `element-plus/theme-chalk/dark/css-vars.css` | — |
| 全局 CSS 变量化 | 把 `base.css` / `main.css` / `book.css` / `about.css` / `user.css` / `read.css` 中的硬编码颜色替换为变量 | 主题基础设施 |
| 页面组件变量化（前台） | 首页 / 全部作品 / 排行榜 / 书籍详情 / 正文阅读 / 登录 / 注册 / 用户中心 / 上传 / 我的上传 / 书籍管理 / 反馈 / 新闻 | 全局 CSS 变量化 |
| 页面组件变量化（作者后台） | author 系列 5 个页面 + `author/Header.vue` + `user/Menu.vue` | 全局 CSS 变量化 |
| 切换入口 | `Top.vue` 导航栏右上角图标；点击切换 + 图标同步 | 主题基础设施 |
| 深色适配走查 | 逐页核对深色下无「深底深字 / 浅底浅字」，Element Plus 组件同步 | 以上全部 |

## 6. 明确不做（边界）

- 不做 `.mobi`/`.azw3`/`.pdf` 解析
- 不做从互联网抓取书源（多书源阅读站，另一需求方向）
- 不启用 ShardingSphere 分表（保持关闭）
- 不含作者账号绑定 / 审核流 / 收益
- 主题切换不做配色方案模式（暖橙/蓝调等）、不做跟随系统、不做后端持久化

## 7. 里程碑

| 阶段 | 产物 | 门禁 |
|------|------|------|
| 文档补齐 | PRD / api-contracts / Plan | 用户确认口径 |
| 开发 | tasks.json 任务拆分 → Planner → Developer → Tester | 每功能闭环 |
| 验收 | E2E：上传 txt/epub → 入库 → 搜索/阅读 | 用户验收 |

## 8. 来源说明

- 现有能力与端口：由代码运行 + 配置反向梳理。
- 上传图书功能设计：为本次新增需求，标注 `[新增]`。
- 主题切换功能设计：2026-10-29 修整新增，口径见 PRD 第 7 节。