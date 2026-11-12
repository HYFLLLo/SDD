# 工作日志

> 由 Orchestrator 维护。记录项目开发、测试、修复和 blocked 状态。

---

## 2026-09-04 — 项目纳管与产品设计（import 模式）

- 项目 `novel`（novel 小说精品屋）以 import 模式纳管：`Projects_Repo/novel`，repo `https://github.com/201206030/novel.git`。
- 反向补齐产品设计产物：`docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`docs/prototypes/`。
- 需求：新增「上传图书」功能 —— 前台**免登录**上传 txt/epub，自动解析章节入库，前台可浏览/搜索/阅读。
- 任务拆分（`.sdd/tasks.json`）：T-001 接口骨架 → T-002 txt → T-003 epub → T-004 端到端回归。

---

## 2026-09-04 — T-001 上传配置与接口骨架（passed）

- 调整 `application.yml`：multipart 上限 100MB；新增上传路径配置。
- 新增 `BookUploadReqDto` / `BookUploadRespDto` / `BookUploadController`（占位）；`ErrorCodeEnum` 注册 `A0702`~`A0706`。
- Tester 验证通过。

---

## 2026-09-04 ~ 09-14 — T-002 txt 解析与章节入库（含前端联调）

- 实现 `TxtBookParser`（BOM/UTF-8/GBK 编码识别 + 章节标题正则切分 + 正文清洗）、单事务入库（建 `book_info` + 逐章 `book_chapter`/`book_content` + 回写 wordCount/lastChapter*），`author_id` 固定 0。
- 前端 `BookUpload.vue` 接入真实 API，`api/book.js` 上传请求显式 `Content-Type: undefined`。

### Bugfix 记录（3 轮验收）

| 轮次 | 问题 | 修复 |
|---|---|---|
| 第 1 次验收 FAIL | 上传合法 txt 返回 `B0001`：`book_info.pic_url` 为 NOT NULL 无默认值，建书时未赋值 | `setPicUrl("/img/default-cover.gif")` + 新增后端 classpath 静态资源 `resources/static/img/default-cover.gif`（不走 `/image/**`，该路径被 `FileInterceptor` 映射到磁盘） |
| 第 2 次验收 FAIL | 简介留空时 `book_desc` 违反 NOT NULL（同类缺陷复发） | `setBookDesc(hasText ? trim : "")`；同时给 `book_name` 加兜底；穷尽核查全部 NOT NULL 无默认值列 |
| 第 3 次验收 | — | **PASS** |

- 缺陷报告：`.sdd/bug_fix/20260914-1510-book_info-pic_url-缺默认封面.md`、`.sdd/bug-logs/T-002.md`
- 教训已沉淀至 `.sdd/experience.md`。

---

## 2026-09-14 ~ 09-15 — T-003 epub 解析与章节入库（含前端联调）

- `pom.xml` 引入 jsoup 1.17.2。
- 实现 `EpubBookParser`：zip（JDK `ZipFile`）→ `META-INF/container.xml` → OPF（manifest + spine）→ 按 spine 顺序逐个读取 xhtml → jsoup 提取纯文本（保留段落换行、去标签/样式）。
- 复用 T-002 的单事务入库路径，NOT NULL 兜底完整覆盖。
- 损坏 epub（缺 container.xml / 非 zip 结构）统一 `A0704`，事务回滚无脏数据。
- 前端 `BookUpload.vue` accept 增加 `.epub`。
- **开发期坑**：验证脚本手写 multipart 时 boundary 行缺少起行 CRLF，导致 Spring 解析出 0 字段、全部返回 `A0400`；修正后正常。
- **验证前处置**：kill 陈旧后端进程（T-002 时代构建）→ `clean compile`（同时清掉 `target` 中残留的旧编译产物）→ 重启到当前构建。
- Tester 独立验收：合法 epub `00000`（3 章）、损坏 epub `A0704` 无脏数据、DB 三表与章节顺序正确、正文无 HTML 残留 → **PASS**。

---

## 2026-09-15 — T-004 端到端回归验证（passed）

- 真实启动后端（8888）+ 前端（1024）+ MySQL + Redis。
- Tester 独立验收（含 Playwright + 系统 Chrome 驱动的浏览器 E2E）：
  - txt / epub 上传全链路：`00000`、chapterCount=3、章节顺序与 spine 一致、正文纯文本。
  - 上传页 → 搜索结果 → 详情页 → 阅读页 → 下一章跳转，页面无 JS 错误、无 Mock 残留、请求命中 8888。
  - 加载态实测：上传中 `is-loading=True`，成功/失败后恢复；失败路径无脏数据。
  - 回归：首页推荐、seed 书详情/目录/正文、上下章接口全部正常。
  - **PASS**
- 测试数据清理：单事务删除测试书，DB 恢复基线 `book_info=107` / `book_chapter=11137` / `book_content=11137`。

---

## 当前状态

- **T-001 ~ T-004 全部 passed**，「上传图书」功能端到端闭环。
- 已产出启动文档 `docs/startup.md`（环境要求 / 启动命令 / 默认配置 / 常见问题）。
- 等待用户最终业务验收；如发现问题进入 `sdd-bugfix`。

### 已知观察项（非缺陷，不影响功能）

- `GET /api/front/book/{id}` 详情 DTO 的 `lastChapterName` 恒为 null；章节列表 DTO 无 `chapterNum`（前端用 `id` 定位章节）——平台既有行为。
- 部分种子数据的封面路径 `/localPic/**` 在本地后端不受服务（后端仅映射 `/image/**`），线上由 CDN 提供。
- `BookContent.vue` 存在旧站静态残留 JS，无运行时错误，超出本次功能范围。

---

## 2026-10-20｜「我的上传」需求：T-005 完成，T-006 暂停（干净中断点）

- 需求：前台导航「我的上传」页，仅管理员（admin/admin）可见，本期只做我的图书列表 + 切换状态（连载中/已完结）。文档增量已落盘：PRD 第 3A 节、api-contracts 第 1A 节、Plan 第 3A 节。
- Planner 拆分：T-005（基础设施）/ T-006（管理接口+前端页面，user_gate=true）/ T-007（仙逆回填+E2E 回归，user_gate=true）。
- ✅ **T-005 passed（Developer + Tester 双确认）**：`book_info.uploader_id` 列+索引（幂等迁移脚本 `doc/sql/uploader_id_2026-10-20.sql`）、admin 账号幂等初始化（`AdminUserInitializer` + `novel.admin.*` 配置）、登录返回 `admin` 标记（前端 localStorage isAdmin）、上传链路挂 TokenParseInterceptor 取登录态（匿名仍可传，落 0）、后端移除 UserLoginReqDto 手机号 @Pattern。测试报告 `.sdd/test-reports/test-T-005.md`。
- ⏸️ **T-006 在 Developer「读代码阶段」被用户要求暂停**：刚启动 5 分钟，只读了契约/mapper 等文件，**未写任何 T-006 代码**（已核实：无 UploadController/MyUpload.vue/api/upload.js 等产物，工作区改动均为 T-005 及更早内容）。中断点干净，无需回滚。
- **恢复方式**：直接重新调度 T-006 Developer（任务定义完整在 `.sdd/tasks.json` id=T-006，description 含全部实现细节与坑位提示），无需回滚或重建。
- 当前 DB 基线：book_info=109（107 种子 + 「仙逆」「丹道宗师」两本 uploader_id=0 待 T-007 回填）；user_info 仅 admin(id=1)。8888/1024 端口均已释放（服务已停）。
- 观察项：MySQL ai_ci 使「Admin」大小写变体可登录同一账号（密码仍校验，非风险）；`frontend` 既有 116 个 lint 历史错误；`jsconfig.json` 的 `target: es5` 弃用告警（历史遗留，非本次引入，待功能交付后统一处理）。

---

## 2026-10-21｜「我的上传」恢复开发：T-006、T-007 全部通过

- 用户继续「我的上传」优化。恢复方式按中断点约定：直接重新调度 T-006 Developer（任务定义完整，无需回滚）。
- 运行时确认：JDK21（`D:\tools\jdk21\jdk-21.0.12.1+1`）、Maven 仓库 `D:\tools\infra\m2-repo`、MySQL 8 / Redis 5 已拉起并监听 3306/6379。
- ✅ **T-006 passed**（管理接口 + 前台入口/管理页 + 真实联调）：`UploadController`/`UploadService(Impl)`、DTO、`ApiRouterConsts` 新增 `/upload` 前缀、`WebConfig` 拦截、`CommonExceptionHandler` 补 `MethodArgumentNotValidException→A0400`、`BookChapterMapper` 一次 `GROUP BY` 统计章节数；前端 `api/upload.js`、`MyUpload.vue`、`/my_upload` 路由、`Navbar` 管理员显隐、`Login.vue` 放开手机号校验。Developer 自我联调通过；Tester 独立验收 PASS（报告 `.sdd/test-reports/test-T-006.md`）。
- ✅ **T-007 passed**（仙逆回填 + 全链路 E2E）：回填脚本 `doc/sql/uploader_id_backfill_2026-10-20.sql` 幂等执行，将「仙逆」`uploader_id` 从 0 改为 admin id=1；Tester 真实浏览器 E2E 覆盖管理员上传/列表/状态切换/详情同步、匿名上传/搜索/阅读、权限与既有接口回归（报告 `.sdd/test-reports/test-T-007.md`）。
- 数据清理：每次测试后单事务按 `book_content→book_chapter→book_info` 删除新增数据，DB 恢复基线 `book_info=109 / book_chapter=19716 / book_content=19716`。
- 补充修正（2026-10-21，用户反馈）：用户指出「丹道宗师」也是上传书，应出现在「我的上传」。核实 `book_info.book_name='丹道宗师'`（id=1431630596354977797）确为 `author_id=0 / uploader_id=0` 的匿名上传书；已把回填脚本范围改为 `IN ('仙逆','丹道宗师')` 并重新幂等执行，丹道宗师 `uploader_id 0→1`。修正后 admin 的 `GET /api/front/upload/books` 返回 `total=2`，`uploader_id<>0` 为「仙逆」「丹道宗师」两行。
- 新增观察项：后端 CORS 只允许 `localhost:1024`，`127.0.0.1:1024` 会被拒，用户访问请用 `http://localhost:1024`；MySQL 8 root 需 `allowPublicKeyRetrieval=true`（已写入 datasource）；全仓 lint 116 个历史错误仍待功能交付后统一收敛。
- 下一步：等待用户从前端做最终业务验收（T-006/T-007 user_gate=true），如发现问题进入 `sdd-bugfix`。

- 小修整（2026-10-21，用户要求）：作家专区管理页共用页头 components/author/Header.vue 增加「返回上一页」按钮（有历史则 outer.back()，无历史回首页），覆盖 BookList/BookAdd/ChapterList/ChapterAdd/ChapterUpdate 五个页面。
  - 同时作家注册页 iews/author/Register.vue 也增加返回按钮，覆盖未注册进入路径。
### 数据回填: 首页推荐位空置回填（2026-10-21）
- **现状**: 删除大部分书籍后 `home_book` 仅剩 5 条，type 0 和 type 4 为空，首页推荐区空置
- **处理**: 用现有 9 本 `book_info` 按访问量/字数回填 `home_book`，type 0/1/2/3/4 分别 5/9/5/5/5 条
- **验证**: 重启后端后 `GET /api/front/home/books` 返回 200，各 type 计数为 5/9/5/5/5