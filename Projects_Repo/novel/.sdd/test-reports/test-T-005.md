# 测试报告：T-005 上传归属字段与管理员账号基础设施（uploader_id + admin 初始化 + 上传链路取登录态）

**测试时间**：2026-10-20 17:00 ~ 17:35
**Tester Agent ID**：claude-code/tester（SDD V7.1）

## 结果：PASS

所有验收标准与技术检查均独立复现通过。后端 8888（重启后 PID 2228，测试结束后已停止）、前端 1024（重启后 PID 22900，测试结束后已停止）均为本次验证期间由 Tester 自己启动的进程。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | book_info 新增 uploader_id 列（bigint unsigned NOT NULL DEFAULT 0）+ idx_uploader_id 索引，后端启动不报错 | PASS | `SHOW CREATE TABLE book_info` 实测：`` `uploader_id` bigint unsigned NOT NULL DEFAULT '0' COMMENT '上传者用户ID;0-匿名' ``、`KEY idx_uploader_id (uploader_id)`。`mvnw.cmd compile` 通过（exit 0）；`mvnw.cmd spring-boot:run` 启动成功（Started NovelApplication in 6.367s，Tomcat 8888）。实体 `BookInfo.uploaderId`（Long，手写 getter/setter，BookInfo.java:61/186-190）与列名映射一致；`DatabaseConsts.BookTable.COLUMN_UPLOADER_ID = "uploader_id"`（DatabaseConsts.java:95） |
| 2 | user_info 始终存在且仅一条 username='admin'，重复启动不多插 | PASS | 重启后端两次（含本次杀掉旧 PID 18400 后的启动），`SELECT COUNT(*) FROM user_info WHERE username='admin'` 恒为 1。启动日志：`AdminUserInitializer: 管理员账号 admin 已存在，跳过初始化`。admin id=1，salt='0'，status=0 |
| 3 | admin/admin 登录成功，admin=true；普通账号 admin=false | PASS | 实测 `POST /api/front/user/login`：admin → code=00000，data.admin=true，token 非空；插入的临时普通用户 t005testuser → code=00000，data.admin=false（测试后已删除）。错误密码返回 A0210 用户密码错误。绕过测试：`Admin`（大小写）可登录且 admin=true——MySQL utf8mb4_0900_ai_ci 排序规则下 `WHERE username='Admin'` 命中同一条 admin 记录（id=1），`isAdmin` 用 DB 规范用户名比对，密码校验仍生效，非权限绕过；注册侧查重同样大小写不敏感，无法注册冲突账号；带空格用户名（`admin `/` admin`）返回 A0201 不存在。详见「超出范围发现」#1 |
| 4 | 管理员登录态上传 → uploader_id=admin 的用户 id；匿名上传 → 0 | PASS | 双通道验证：(a) Python urllib 手工 multipart 直连 8888：admin token → bookId ...7802 uploader_id=1；无 Authorization → ...7804 uploader_id=0；普通用户 token → ...7803 uploader_id=3；Authorization: "null" 字符串头 → ...7805 uploader_id=0（TokenParseInterceptor 解析失败落 null → 0，不抛异常）。(b) Playwright 真实浏览器（Chrome headless，1024 前端）：admin 登录（localStorage isAdmin=true, uid=1）后从上传页面上传 → DB uploader_id=1；退出登录（isAdmin=null, Authorization=null）后匿名上传 → uploader_id=0 |
| 5 | 匿名上传保持可用，txt/epub 上传、100MB 限制、错误码行为无回归 | PASS | 匿名上传（无 token 与 "null" 头两种）均 code=00000；首页 `/api/front/home/books`、搜索 `/api/front/search/books`、详情 `/api/front/book/{id}`、阅读 `/api/front/book/content/{chapterId}` 全部 00000；100MB 限制：流式发送约 105MB body → 连接被服务端中止（WinError 10053，Tomcat multipart 超限拒绝），`COUNT(*) book_name='T005bigfile'`=0 无脏数据；超长章节名：上传「第一章 + 300 字」标题 → book_chapter.chapter_name 被截断为 CHAR_LENGTH=100（varchar(100) 上限），无 SQL 报错。epub 链路本次未重传（T-003/T-004 已 passed，归属逻辑对 txt/epub 是同一 doUploadBook 代码路径，uploaderId 赋值在解析之后入库之前，格式无关） |
| 6 | 管理员账号密码来自 novel.admin.*，代码与脚本无明文生产密钥 | PASS | `application.yml` 第 246-248 行：`novel.admin.username: admin` / `novel.admin.password: admin`（配置项默认值，生产需覆盖）。Java 代码 grep 无硬编码密码/username="admin"（AdminUserInitializer 只读 NovelProperties）；迁移脚本无 DROP/TRUNCATE/UPDATE/DELETE 等破坏性语句，仅 information_schema 查询 + 条件 DDL |

## 技术检查逐条验证

| # | 检查 | 结果 | 证据 |
|---|------|------|------|
| 1 | mvnw.cmd compile 通过（JAVA_HOME=JDK21，MAVEN_OPTS 传本地仓库） | PASS | `JAVA_HOME=D:\tools\jdk21\jdk-21.0.12.1+1 MAVEN_OPTS=-Dmaven.repo.local=D:/tools/infra/m2-repo ./mvnw.cmd compile -q` exit=0 |
| 2 | 迁移脚本已真实执行，列与索引存在 | PASS | `SHOW COLUMNS FROM book_info LIKE 'uploader_id'` 有结果（bigint unsigned NO MUL 0）；`SHOW INDEX` 含 idx_uploader_id；**幂等复测**：对本地库重跑 `uploader_id_2026-10-20.sql` → 输出 `column uploader_id already exists` / `index idx_uploader_id already exists`，exit 0，无重复加列加索引（information_schema 索引计数仍为 1），脚本无破坏性语句 |
| 3 | 8888 端口 PID 属于本次构建 | PASS | 验证前 netstat 显示 8888=PID 18400（不可信旧进程），taskkill 后用 `mvnw.cmd spring-boot:run` 重启，新 PID 2228，启动日志 PID 一致（Tomcat started on port 8888，process 2228） |
| 4 | admin 登录 curl 返回 00000、admin=true、token 非空 | PASS | Python urllib 实测（等价 curl）：code=00000，admin=true，token=eyJzeXN0ZW... 非空 |
| 5 | 连续启动两次 COUNT 恒为 1 | PASS | 两次启动后各查一次均为 1 |
| 6 | 前端真实联调（非仅 curl） | PASS | Playwright + 系统 Chrome 驱动 1024（重启后的新 PID 22900）：`#/login` 填 admin/admin → 登录后 localStorage Authorization 非空、**isAdmin=true**、uid=1；跳转 `#/home`；`#/book_upload` 选文件填书名上传 → 页面显示「上传成功，共解析 2 章…48 字 立即阅读」，Network 命中 `http://127.0.0.1:8888/api/front/resource/book/upload`；DB 新行 `T005浏览器admin上传` uploader_id=1（=admin 的 user_info.id）；首页点「退出」后 isAdmin=null、Authorization=null |
| 7 | 匿名回归：清 Authorization 后上传，uploader_id=0，NOT NULL 列全有值 | PASS | 浏览器退出登录后匿名上传 `T005浏览器匿名上传` uploader_id=0；五本直连上传书 pic_url=/img/default-cover.gif、book_name/author_id(0)/author_name/book_desc 均非 NULL，全程无 B0001 |
| 8 | 匿名上传回归：word_count 与 book_chapter 行数正常，前台可打开 | PASS | word_count=48 与 2 章 chapter 行数/2 条 content 一致；`GET /api/front/book/{id}` 返回 bookName/wordCount 正常，`content/{chapterId}` 返回 chapterName「第一章 测试开始」 |
| 9 | 代码无硬编码密码 | PASS | 全源码 grep：Java 无 "admin" 字面量配置读取，md5 仅在 AdminUserInitializer 从 NovelProperties 取值后摘要 |

## 关键证据摘要

- 上传归属矩阵（Python urllib 直连，查库核对）：

| 登录态 | bookId 后缀 | uploader_id |
|--------|------------|-------------|
| admin token | ...7802 | 1（admin 的 user_info.id） |
| 普通用户 token（id=3） | ...7803 | 3 |
| 无 Authorization | ...7804 | 0 |
| Authorization: "null" 字符串 | ...7805 | 0 |

- 浏览器链路（Playwright，1024）：`S1 admin login: isAdmin=true uid=1` → 上传成功「共解析 2 章」 → `S5 after logout: isAdmin=null Authorization=null` → 匿名上传成功 → DB uploader_id 分别为 1 / 0。截图曾保存（pw_admin_upload.png 等，验证后已清理临时目录）。
- 前端 API 命中记录（Network 抓取）：login、news/latest_list、book/visit_rank、home/books、book/category/list、resource/book/upload 全部指向 `http://127.0.0.1:8888`，无 Mock。
- 前端改动核对：`utils/auth.js`（adminKey='isAdmin'，setAdmin/getAdmin/removeAdmin）、`Login.vue:141` setAdmin(data.admin)、`Top.vue:69` removeAdmin()。
- 后端改动核对：`WebConfig` 给 `API_FRONT_RESOURCE_URL_PREFIX + "/book/upload"` 挂 TokenParseInterceptor（order 3，只解析不拦截）；`BookUploadServiceImpl:151-152` `UserHolder.getUserId()==null?0L:...`；`UserServiceImpl:122` `.admin(isAdmin(username))`；`UserLoginReqDto` 已无手机号 @Pattern（仅 @NotBlank）。
- 控制台错误：仅静态图片资源 404（如封面占位图），与 T-002~T-004 期间一致，非本任务引入。

## 数据清理（恢复基线）

| 表 | 测试前 | 测试峰值 | 清理后 |
|----|--------|---------|--------|
| book_info | 109（含 Developer 验证期的「丹道宗师」1 本） | 119（本轮 Tester 新增 10 本） | **109** |
| book_chapter | — | 本轮新增 16 | 新增行全部删除（0 残留） |
| book_content | — | 本轮新增 16 | 新增行全部删除（0 残留） |
| user_info | 1（admin） | 2（+t005testuser） | **1（仅 admin）** |

清理方式：单事务按 book_content → book_chapter → book_info 顺序删除 id BETWEEN ...7802 AND ...7811；user_info 删 t005testuser。清理后复核：`search/books?keyword=T005` total=0，`home/books` 00000；本地 JWT token 文件与临时目录全部删除。注：基线 108 为 Developer 开工前口径，「丹道宗师」（id ...7797，uploader_id=0）与「仙逆」是 Developer 阶段产物，属 T-007 回填对象，本轮不处置，故恢复至 109。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 用户名大小写不敏感（MySQL ai_ci 排序规则）：`Admin` 可登录同一账号且 admin=true。判定为非真实风险（命中同一行、密码仍校验、无法注册冲突名），但 T-006 管理接口同样基于 username 比对，行为一致 | 后端/DB | 如需严格匹配可在查询加 `COLLATE utf8mb4_bin`，建议在 T-006/T-007 观察即可 |
| 2 | 前端页面存在静态图片 404（控制台报错），与既有版本一致 | novel-front-web | 既有问题，超出本任务范围 |

## 系统级经验

无。本任务未发现框架/规范/重复/对齐类跨项目问题。
