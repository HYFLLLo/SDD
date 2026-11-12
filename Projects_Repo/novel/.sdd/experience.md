# 项目经验

> 当前项目长期有效的经验。  
> Developer / Tester / Bugfix 在任务完成后维护本文件。

---

## Harness 系统经验摘要

新项目开始时，Developer / Tester / Bugfix 需要同时参考：

- 当前项目经验：`.sdd/experience.md`
- 系统级经验：`<Harness 根目录>/memory/harness-experience.md`

---

## 项目经验

### T-001: 上传配置与接口骨架
- **陷阱**: `mvnw.cmd -Dmaven.repo.local=...` 会被 mangle 成 `-D.repo.local=D` 报错；本地 Maven 仓库必须通过 `MAVEN_OPTS` 环境变量传（`-Dmaven.repo.local=D:/tools/infra/m2-repo`）。
- **经验**: 构建必须用 `mvnw.cmd`（不是 mvnw），且 `JAVA_HOME` 需指向 `D:\tools\jdk21\jdk-21.0.12.1+1`（实际 java.exe 在该子目录下，`D:\tools\jdk21` 本身不是 JDK 根）。
- **经验**: multipart 上传表单 DTO 绑定用 `@ModelAttribute`（不是 `@RequestBody`），否则 MultipartFile 与表单字段无法正确反序列化；`@Valid` 校验自行生效。空 `file` 时由 `@NotNull` 校验兜底（全局 `BindException`→`A0400`），占位阶段暂不置 `A0706`。
- **经验**: `BookUploadReqDto` 只字段前以 `--` 分隔的注释（javadoc 风格应使用 `/** */`，与现有 DTO 中的 `/** */` 对齐）。
- **注意**: 本任务只做占位接口，不实现解析/入库（T-002/T-003）。`ErrorCodeEnum` 已注册 `A0702~A0706` 供后续解析/入库阶段返回，其中 `A0702`（文件过大）在 Spring DispatcherServlet 抛出 `MaxUploadSizeExceededException` 时由全局 `CommonExceptionHandler` 的 `@ExceptionHandler(Exception.class)` 兜底，实际会返回 `B0001` 而非 `A0702`，后续联调如需精确错误码需在 `CommonExceptionHandler` 增加对应绑定。
- **注意**: `docs/Plan.md` T-后端-001 提到新增 `BookUploadService/BookUploadController`，占位实现时保留 Service 分层（接口+impl 分开），T-002 真实解析逻辑落位到 impl。

**本功能已完成，等待 Orchestrator 调度 Tester 验证。**

### T-002: txt 解析与章节入库（含前端联调）
- **陷阱**: 上传接口位于 `/api/front/resource/**`（免登录），只存在 `@ModelAttribute` + `MultipartFile` 的 `BookUploadReqDto`；**不能调用**带作者权限校验的 `BookServiceImpl.saveBookChapter`，必须自实现「建书 + 逐章 book_chapter/book_content + 更新 book_info」的事务，author_id 固定 `0`。
- **陷阱**: `MaxUploadSizeExceededException` 此前被 `CommonExceptionHandler` 的 `@ExceptionHandler(Exception.class)` 兜成 `B0001`。T-002 已新增针对该异常的 handler 映射到 `A0702`，AC4（>100MB 明确提示「文件大小超过限制」）必须依赖该 handler。
- **陷阱**: `multipart/form-data` 表单 DTO 绑定必须用 `@ModelAttribute`（T-001 经验已踩），真实解析在 ServiceImpl 内使用 `file.getBytes()` 读取字节。
- **陷阱**: .txt 文件可能带 BOM。`new String(bytes, UTF_8)` 会把 BOM 解码为 `﻿` 混入首行标题。必须在读取时先探测 `EF BB BF` 三字节并从偏移 3 开始解码。
- **陷阱**: GBK 解码字节序列时，可能同时是「合法 UTF-8」范围。先 UTF-8 严格解码（REPORT 模式），失败才回退 GBK，能正确区分 GBK 与 UTF-8，避免中文被乱码。
- **经验**: 章节切分采用「逐行匹配标题正则 + 正文并入相邻标题」比「在位切分整段文本」更稳，天然处理了标题行前的前言/版权页；无标题时整篇作为单章。
- **经验**: 空文件/二进制伪装 txt 统一映射 `A0706`，解析后无有效章节映射 `A0704`，同名书校验放在 `author_id = 0` 下查 `book_name` 映射 `A0705`。
- **陷阱**: 缓存清理必须在事务内（`evictBookInfoCache` 等），否则提交前清除的是旧缓存；本任务在事务方法内直接调用，避免了 age-ahead 问题。
- **前端陷阱**: `frontend` 的 `utils/request.js` 默认 `axios.defaults.headers.post['Content-Type'] = 'application/json'`。上传 multipart 时若不复位，Spring 会因缺少 `boundary` 报 `MissingServletRequestPartException`。必须对上传请求显式传 `headers: { 'Content-Type': undefined }`（axios 0.27 在标准浏览器 FormData 下会删除 Content-Type 让浏览器加 boundary）；同时该全局默认值不影响 GET。
- **前端经验**: `el-upload` 使用 `:auto-upload="false"` + `:on-change` 捕获原始 File（`uploadFile.raw`），由自己组装 `FormData` 提交，可自由控制书名/分类等元数据字段与 axios。
- **前端路由**: `/book_upload` 是顶层前台路由（不是 author 嵌套路由）。导航入口放在 `components/common/Navbar.vue`（非 author Header）。
- **经验**: 前端 build 输出会验证 `dist` 中是否包含「上传图书」入口文案，可用作 smoke check。
- **注意**: 本任务仅实现 txt 解析；epub（T-003）仍返回 `A0704`，未引入 jsoup。

### Bugfix: book_info.pic_url NOT NULL 无默认值导致上传 B0001（2026-09-14）
- **触发**：上传合法 txt 返回 `{"code":"B0001","message":"系统执行出错"}`，无入库。
- **根因**：`BookUploadServiceImpl.doUploadBook()` 建 `BookInfo` 时未设 `picUrl`，而 `book_info.pic_url` 列 **NOT NULL 无默认值**（见 `doc/sql/novel_struc.sql`），INSERT 抛 `Field 'pic_url' doesn't have a default value`。
- **已有经验回查**：项目 T-002 经验未涵盖该列约束；系统级经验无相关条目。
- **修复**：`setPicUrl("/img/default-cover.gif")` + 新增后端 `resources/static/img/default-cover.gif`（复用前端 `default.gif`，随 jar 打包）。**不用 `/image/**`**——`FileInterceptor` 拦截 `/image/**` 且读磁盘 `D:/novel-upload`（当前磁盘无图），`/img/**` 走 Spring 静态映射零磁盘依赖。
- **避坑规则**：
  - 建 `BookInfo` 前对照 `novel_struc.sql` DDL，**NOT NULL 且无默认值的列必须全部赋值**：`pic_url`、`book_name`、`author_id`、`author_name`、`book_desc`。
  - 默认封面走 classpath `resources/static/img/` + `picUrl=/img/...`，可随 jar 部署，环境无关。
  - 上传/入库任务验收必须「真实 insert 落库成功」，不能只靠编译通过；覆盖 NOT NULL 列是必查项。
  - seed 107 本的 `/localPic/**` 封面是本地坏链（后端仅 `/image/**`），线上由 CDN 提供，非本缺陷，勿扩大范围。

### T-003: epub 解析与章节入库（含前端联调）
- **经验**: epub 解析链路（ZipFile → container.xml → OPF → spine → xhtml → jsoup 清洗）稳定可用，jsoup 纯文本化无 HTML 残留（`INSTR(content,'<')=0` 验证通过）。
- **经验**: 事务完整性验证通过——损坏 epub（缺 container.xml / 伪 zip）返回 A0704 且 DB 无任何脏数据（book_info/book_chapter/book_content 均无新增行）。
- **陷阱**: Windows Git-Bash 下 `curl -F` 中文会 mojibake，验收脚本改用 Python `urllib.request` 手动组装 multipart（UTF-8 boundary），彻底规避编码问题。
- **经验**: 同名书校验（A0705）放在解析成功后、insert 前，epub 分支复用 T-002 同一事务兜底，NOT NULL 列覆盖与 T-002 一致（pic_url/book_name/author_id/author_name/book_desc）。
- **观察**: book_desc 上传时未传则为空字符串（非 NULL），符合 NOT NULL 约束但内容为空——后续可考虑增加必填校验或默认值兜底（如"暂无简介"）。

### T-004: 端到端回归验证（E2E 最终交付门禁）
- **经验**: E2E 回归验证采用「HTTP 冒烟 + Playwright 真实浏览器」双层验证。HTTP 层验证 API 契约与数据，浏览器层验证页面渲染、表单交互、路由跳转与加载态。仅做 HTTP 不能证明前端真实渲染；仅做静态代码也不能证明交互。
- **经验**: 浏览器驱动上传需处理 Element Plus 下拉：分类在 onMounted 调 listCategorys 后自动选中首项，无需再点开选择；点开下拉会留下 teleport 的 popper 拦截后续点击，需先按 Esc 关闭。
- **经验**: 小而快的上传（3KB txt）中间加载态肉眼/脚本难以捕捉；用 Playwright `page.route` 对 `/front/resource/book/upload` 注入 4s 延迟即可稳态验证 `is-loading=True` → 完成后 `False`。
- **经验**: 搜索/一类列表 DTO（BookInfoRespDto）返回字段名是 `id`、`categoryId`、`lastChapterName` 等（无 `bookId`）；上传响应 DTO（BookUploadRespDto）才用 `bookId/chapterCount/wordCount`。写断言脚本别混用。
- **经验**: `GET /api/front/book/{id}` 详情 DTO 的 `lastChapterName` 恒为 null（DB 字段存在但与读取详情路径无关），章节列表 DTO 的 `chapterNum/chapterWordCount` 也为 null——验收口径以 chapter/about 与 DB 为准，勿被 `null` 误判。
- **经验**: 测试数据清理必须在单事务内按 book_content → book_chapter → book_info 顺序删，删后恢复基线（107/11137/11137）；本库无外键，顺序仅按从属关系。清理后搜索残留关键词 total=0 可作清理完成的复核信号。
- **经验**: 后端日志为 GBK 控制台输出、前端为 webpack 进度；`PYTHONIOENCODING=utf-8` + `python -X utf8` 避免中文 mojibake，Playwright 长任务务必 `-u`（unbuffered）编写 stdout 到文件再 cat，否则 120s 后台化会丢输出。

### Bugfix: 章节名超长导致上传 B0001（2026-10-20）
- **触发**：用户上传图书时接口返回 `B0001 系统执行出错`。
- **根因**：`BookUploadServiceImpl` 未在入库前截断解析结果，`book_chapter.chapter_name varchar(100)` / `book_info.last_chapter_name varchar(50)` 收到超长标题后抛 `MysqlDataTruncation: Data too long for column 'chapter_name'`，被全局异常兜成 `B0001`。
- **已有经验回查**：无同因经验；此前 `book_info.pic_url` NOT NULL 缺默认值属于同一接口的另一变体。
- **为什么仍然犯错**：旧经验只覆盖 NOT NULL 缺默认值，未覆盖「入库字段必须与 DDL 长度对齐」这一通用规则。
- **修复**：在 `doUploadBook` 入库前对 `category_name(50)`、`book_name(50)`、`author_name(50)`、`book_desc(2000)`、`chapter_name(100)`、`last_chapter_name(50)` 统一按列长截断；新增按 code point 计数的 `truncate` 工具方法，避免切断 emoji 代理对。
- **避坑规则**：上传/解析类功能的所有写库字段必须先对照 `novel_struc.sql` DDL 长度；解析器产出的字段（尤其章节标题）必须在 insert 前截断到目标列上限，不能假设数据天然合法。验收必须包含「超长标题 txt/epub 上传成功且 CHAR_LENGTH 符合列长」。

### T-005: 上传归属字段与管理员账号基础设施（uploader_id + admin 初始化 + 上传链路取登录态）
- **陷阱**：`/api/front/resource/book/upload` 免登录、原不挂 `TokenParseInterceptor`，登录态上传拿不到 `UserHolder.getUserId()`。给该路径单独挂 `TokenParseInterceptor`（只解析不拦截，order 3），匿名上传继续可用。前端 axios 未登录时 `Authorization` 头为字符串 `"null"`，`TokenParseInterceptor` 里 `StringUtils.hasText("null")` 为真、`jwtUtils.parseToken("null")` 返回 null，`UserHolder.setUserId(null)` 后业务侧 `getUserId()==null` 必须落 0 而非抛异常。
- **陷阱**：`UserLoginReqDto.username` 原本带手机号 `@Pattern`，admin 登录直接 A0400。admin 账号名（如 `admin`）不是手机号，登录 DTO 的 username 只能 `@NotBlank`，手机号校验留在注册侧。这是 T-006 才会做的前端 Login 文案调整的前置后端前置——前端登录同样有 `^1[3-9][0-9]{9}` 校验但只弹错不 return，admin 仍能登录；后端 `@Pattern` 会直接 400，必须放宽。
- **陷阱**：`novel` 前缀下新增 `@ConfigurationProperties(prefix = "novel")` 的 record 会与既有 `CorsProperties`/`XssProperties` 的 `prefix = "novel.cors"`/`"novel.xss"` 并存不冲突；但必须用 `@EnableConfigurationProperties(NovelProperties.class)` 显式注册（项目无 `@ConfigurationPropertiesScan`，裸 `@ConfigurationProperties` 不会被扫描）。可在用到该属性的 `@Component`（`AdminUserInitializer`/`UserServiceImpl`）上各自 `@EnableConfigurationProperties`，或新建一个 `@Configuration` 统一注册。
- **陷阱**：后台运行的 Spring Boot jar 会锁住 `target/*.jar`，`mvnw.cmd package` 时 `repackage` 步骤报 `Unable to rename ... .jar to .jar.original`。打包前必须先 `taskkill //F //PID <pid>` 停掉旧进程再打包。
- **经验**：管理员账号初始化用 `CommandLineRunner` + 幂等查重（`selectCount` + 捕获 `DuplicateKeyException` 双保险），密码口径与 `UserServiceImpl.login` 一致（`DigestUtils.md5DigestAsHex`、`salt='0'`），重复启动恒 1 条。管理员判定直接 `username.equals(配置的 novel.admin.username)`，登录响应 `UserLoginRespDto.admin` 布尔向后兼容增列，供前端导航显隐，避免「普通用户每次进页面被 request.js 对非 00000 弹错」。
- **经验**：改表迁移脚本用 MySQL 预处理语句（`SET @x := (SELECT COUNT(*) FROM information_schema...); PREPARE/EXECUTE/DEALLOCATE`）实现幂等，重复执行输出 `already exists` 不报错；先 `SHOW COLUMNS` 确认列不存在再加列。
- **避坑规则**：新增 `uploader_id` NOT NULL DEFAULT 0 列不影响历史行 ALTER；建 `BookInfo` 时 `setUploaderId(UserHolder.getUserId() == null ? 0L : ...)`，同名校验仍按 `author_id=0` 查重不因归属字段改变口径；NOT NULL 无默认值列（pic_url/book_name/author_id/author_name/book_desc）仍须全部赋值。验收必须「真实 insert 落库」：admin 登录上传→uploader_id=admin 用户 id，匿名上传→0，`Authorization: null` 头→0。

### T-006: 「我的上传」管理接口 + 前台入口与管理页（含真实联调）
- **陷阱**：`@RequestBody + @Valid` 参数校验抛的是 `MethodArgumentNotValidException`，不是表单绑定的 `BindException`；只补 `BindException` 会让 `bookStatus=2` 被兜底成 B0001。需在 `CommonExceptionHandler` 增加 `MethodArgumentNotValidException` → `A0400`。
- **陷阱**：本机 MySQL 8 的 root 用 `caching_sha2_password`，datasource URL 不加 `allowPublicKeyRetrieval=true` 时启动阶段连接池直接失败（Public Key Retrieval is not allowed）。已写入 `application.yml`，避免后续任务重复踩。
- **经验**：章节数统计用 `book_chapter` 的一次 `GROUP BY`，Mapper 方法返回自定义 `BookChapterCountDto`（`book_id as bookId, count(*) as chapterCount` + `<foreach>`），避免逐本 `selectCount` 的 N+1；分页主查询继续用 MyBatis-Plus `Page` + `QueryWrapper`，响应复用 `PageRespDto.of(...)`。
- **经验**：Jackson `write-numbers-as-strings` 下 `PageRespDto` 的 `pageNum/pageSize/total/pages` 也都是字符串，前端分页与比较要用 `Number()`；`localStorage` 中 admin 标记存的是字符串 `"true"`，Navbar 用 `String(getAdmin()).toLowerCase() === 'true'` 判定，不要直接布尔比较。
- **避坑规则**：T-005 已把 `setAdmin/getAdmin/removeAdmin` 放进 `utils/auth.js`，并在 `Top.vue` 退出时 `removeAdmin()`；T-006 前端只新增 `api/upload.js`、`MyUpload.vue`、`/my_upload` 路由和 Navbar 显隐，Login 移除手机号正则并把 placeholder 改为「用户名 / 手机号」，不要重复改 auth/Top。


### T-007: 历史书「仙逆」回填（第 1 部分）
- **经验**: 回填 UPDATE 用 `JOIN user_info u ON u.username = 'admin'`，且 WHERE 同时限定 `book_name = '仙逆' AND author_id = 0 AND uploader_id = 0`，本身天然幂等；第二次执行影响 0 行。
- **经验**: 执行前先用 `SELECT ... WHERE book_name='仙逆' AND author_id=0 AND uploader_id=0` 确认目标行唯一；本库另有大量匿名历史书（回填前 author_id=0 且 uploader_id=0 共 109 行），绝不能去掉 book_name 条件或扩大回填范围。
- **避坑**: PowerShell 调用 mysql 执行含中文 SQL 时，用 UTF-8 无 BOM 的脚本文件 + `--default-character-set=utf8mb4`，避免中文被命令行编码破坏；查询临时验证可用 `_utf8mb4 0xE4BB99E98086` 十六进制字面量避免传参乱码。
- **教训（2026-10-21）**: 回填前必须向用户确认「全部」历史上传书清单，不能只按任务描述里的单个示例书名回填。T-007 任务只写了「仙逆」，实际用户还上传过「丹道宗师」（同样 author_id=0 / uploader_id=0），首次回填遗漏，用户验收时才发现；已把脚本范围改为 `IN ('仙逆','丹道宗师')` 补回填。遇到「把历史上传书归属 admin」类需求，先列出所有候选书与用户核对再执行。

### 小修整: 作家专区导航不应新开标签页（2026-10-21）
- **现象**: 前台 Navbar 点「作家专区」用 `window.open(routeUrl.href, "_blank")` 打开独立标签页，与「首页 / 全部作品 / 排行榜」的当前页跳转不一致。
- **根因**: 原逻辑为了先查 `getAuthorStatus()` 再决定登录/注册/作者首页，最终用 `window.open` 打开作者首页。
- **修复**: `frontend/src/components/common/Navbar.vue` 的 `goAuthor` 保留登录/注册分支，最终跳转由 `window.open` 改为 `router.push({ name: "authorBookList" })`。
- **避坑规则**: SPA 内「需要先异步判断再跳转」的导航，仍应使用 `router.push`，不要用 `window.open(..., "_blank")`；只有明确要求新标签/外部页时才 `window.open`。
- **验证**: `npm run build` 通过（仅既有体积/旧浏览器告警）。

### 小修整: 用户阅读进度缺失（2026-10-21）
- **现象**: 登录用户阅读到某章节后，下次再打开同一本书仍从第一章开始。
- **根因**: 表 `user_read_history`、实体 `UserReadHistory` 和唯一键 `uk_userId_bookId` 都已存在，但后端没有任何读写接口，前端阅读页也没有保存进度、详情页也没有查询进度。属于未实现的存量功能。
- **修复**: 新增 `POST /api/front/user/read_history`（保存）与 `GET /api/front/user/read_history/{bookId}`（查询）；`pre_content_id` 存 `book_content.id`，查询时映射回 `book_content.chapter_id`。前端 `BookContent.vue` 在加载正文后保存，`Book.vue` 的「点击阅读」优先跳 `readChapterId`，无记录回退 `firstChapterId`。
- **避坑规则**: 遇到「表/实体已存在但功能不生效」，先全局搜索该实体的 mapper/service/controller 调用链，确认是逻辑断了还是完全没接线，不要只改前端表象。
- **验证**: 后端 `mvnw.cmd -DskipTests compile` 通过；前端 `npm run build` 通过（仅既有体积告警）。
- **后续坑（2026-10-21）**: 前端联调时点开书籍弹「网络异常」，根因是运行中的 `java -jar target/novel-3.5.1-SNAPSHOT.jar` 还是旧包，新接口返回 404；axios 的错误拦截器会把 404 显示成「网络异常」。**新增后端接口后必须重新 `mvnw.cmd -DskipTests package` 并重启 8888 进程**，不能只 compile 或只刷新前端。

### 新功能: 阅读历史列表（2026-10-21）
- **需求**: 登录用户可查看看过的书籍和上次阅读章节，点击进入正文。
- **实现**: 新增 `GET /api/front/user/read_history/list`，分页查询 `user_read_history` 后批量关联 `book_content` → `book_chapter` → `book_info`，返回 `bookName/picUrl/authorName/chapterId/chapterName/updateTime`。前端新增 `UserHistory.vue`、`/user/history` 路由、`UserMenu` 入口，点击跳 `/book/{bookId}/{chapterId}`。
- **避坑规则**: 列表接口要避免逐条 N+1；历史记录的 `pre_content_id` 是 `book_content.id`，展示章节名前必须先从 `book_content` 映射到 `book_chapter`。

### 新功能: 管理员全站书籍管理（2026-10-21）
- **需求**: 管理员账号可查看并修改全站书籍信息，可上传新 txt/epub 全量替换原内容、可修改封面、可删除书籍。
- **实现**: `UploadController` 新增 `GET /api/front/upload/books/admin`、`PUT /api/front/upload/book/{bookId}`、`PUT /api/front/upload/book/{bookId}/pic`、`POST /api/front/upload/book/{bookId}/content`、`DELETE /api/front/upload/book/{bookId}`；`UploadServiceImpl` 复用前台 JWT + `novel.admin.username` 做管理员校验，避免依赖空的 `AdminAuthStrategy`。
- **避坑规则**: `book_info` 的 `uk_bookName_authorName` 会在修改书名/作者时触发唯一键冲突，更新前必须排除自身 ID 查询重名；`book_name/book_desc/category_name` 等 NOT NULL 无默认值列更新时必须保持完整赋值并截断到 DDL 长度。
- **避坑规则**: 替换内容与删除书籍都要先查出旧 `book_chapter.id`，按章清理 `book_content` 与缓存；删除还要清理 `user_read_history`、`user_bookshelf`、`home_book`、评论及回复，避免首页推荐/书架出现已删除书籍残留。
- **验证**: 后端 `mvnw.cmd -DskipTests package` 通过；前端 `npm run build` 通过；用 `admin/admin` 登录后已实测全站列表、编辑信息、修改封面、临时书籍替换内容及删除均返回 `00000`。

### Bugfix: 删除书籍后首页残留已删除书籍（2026-10-21）
- **触发**: 删除书籍后返回首页仍显示已删除书籍，点击进入出现系统错误
- **根因**: `UploadServiceImpl.deleteBook` 清理了数据库关联数据和 `bookInfoCache`，但未失效 `homeBookCache`、三类排行榜缓存和 `lastUpdateBookIdListCache`；同时 `BookInfoCacheManager.cachePutBookInfo` 对不存在的 bookId 未判空，导致 NPE
- **已有经验回查**: 有，管理员全站书籍管理条目已要求删除时清理 home_book 等关联数据，但未覆盖列表缓存失效
- **为什么仍然犯错**: 经验只强调 DB 关联表清理，未把“所有派生列表缓存必须同步失效”写成明确规则
- **修复**: 删除书籍时同步 `evictHomeBookCache`、`evictVisitRankBooks`、`evictNewestRankBooks`、`evictUpdateRankBooks`、`evictLastUpdateIdListCache`；`cachePutBookInfo` 对 null 抛 `BOOK_NOT_FOUND`；`HomeBookCacheManager` 过滤孤儿 bookId
- **避坑规则**: 任何影响 book_info 可见性/存在性的写操作（删除、替换内容、改状态），都必须同步失效所有可能缓存该书 ID 的列表缓存，不能只清详情缓存
### Bugfix: 删除书籍后再次登录又出现（2026-10-22）
- **触发**: 用户昨天删除大量书籍，今天重新登录后书籍又出现，怀疑删除不持久化
- **根因**: 当前删除接口会物理删除 `book_info` 及全部关联数据，并同步失效缓存；本次现象是删除后数据被全量种子数据恢复/重新导入，不是 delete 接口未持久化。证据：删除后工作日志曾记录只剩 9 本 `book_info`，当前却为 108 行（107 行种子 + 丹道宗师）
- **已有经验回查**: 有，`20261021-1620-delete-book-homepage-cache` 已覆盖“缓存残留”；本次为“数据被恢复”的新变体
- **避坑规则**: 业务验收期间禁止重新导入 `novel_data.sql` 等种子 SQL；启动脚本 `start-novel.ps1` 只执行幂等迁移，不导入业务数据。遇到“删除后又出现”，先查 `book_info` 行数与种子 SQL 是否被重新执行，再决定是否改 delete 代码

### T-008: 主题基础设施与切换机制
- **重大陷阱（仅 production）**: element-plus `sideEffects: "theme-chalk/*.css"` 用 globstar:false 匹配，不覆盖 `theme-chalk/dark/` 子目录，`import '...dark/css-vars.css'` 在 production 被当纯副作用剔除——dev 正常、dist 无 EP 深色变量、el-* 全变浅色。改 `require(...)` 解决。**校验要 grep 唯一深色值 `--el-color-primary-light-7:#213d5b`，只 grep `html.dark` 会因 theme.css 同名选择器误判通过**。
- **陷阱**: 首帧无闪烁必须在真实浏览器量时间：`addInitScript` 记录 class 变更时刻 + `first-paint`，实测 dark(105ms) 早于 first-paint(204ms)。只断言「DCL 有 dark」不够。
- **陷阱**: `page.goto(url+"#/x")` 纯 hash 不重载页面，预置 localStorage 后必须 `page.reload()`，否则误判「刷新后主题丢失」。
- **经验**: EP 2.2.0 深色选择器为 `html.dark`；同时设 `documentElement.style.colorScheme` 让原生控件跟随。25 个 `--nv-*` 在 `:root`/`html.dark` 严格同名同数，浅色照搬现状、深色用 EP 官方色阶（#141414/#1d1e1f/#E5EAF3/#4C4D4F）避免「两套深色」。
- **避坑**: `.bookShelf` 内元素均 `float:right`，后渲染者靠左；图标放 `.user_link` 之前 + `float:right` 才落在最右。实测 user_link 宽 125px、topMain 92px 未变。
- **避坑**: `utils/auth.js` 的 getNickName/getToken 无 try/catch，存储全禁用时会让 Top.vue setup 抛 SecurityError 中断渲染（既有缺陷，不在 T-008 范围；theme.js 自身已容错）。

### T-009: 全局 CSS 变量化
- **陷阱**: 文本模式写回把 CRLF 全转 LF，`sha256sum -c` 把未改的 read.css 判 FAILED；写后须还原 CRLF（read.css 逐字节回基线哈希 = 未改动铁证）。
- **陷阱**: `#ccc`→`#cccccc` 缩写归一使逐字符 diff 误报；须数值规范化（#abc→#aabbcc、.25→0.25）后比 file:line:prop:selector 四元组（257 处/74 色值 1:1 全对上）。
- **经验**: 浅色不变的机械证明：`var(--nv-*)` 按 `:root` 展开回字面量，与原件做「颜色+var() 全遮成同一占位符」的 skeleton diff，6 文件逐字节相同。
- **经验**: 历史色值强行合并会破坏 PRD 7.5 浅色基线，故新增 68 个扩展色板（一值一变量），`:root`/`html.dark` 各 93 个同名同数。
- **避坑**: 截图对比先排动态内容（轮播换 active、注册验证码、详情右侧推荐）；判据「同一 CSS 连拍两次也不一致」。
- **避坑**: `.mainNav .nav li a` 的 `border-bottom:2px solid #f80` 是与导航底色同值的隐形边框，映射 `--nv-brand` 会使深色冒橙线，须单开 `--nv-nav-link-line`。

### T-010: 前台浏览与阅读页变量化
- **陷阱**: 内联白蒙层实为 5 行不是 6（第 6 个在遗留 `.read_style_1`）。改写后 `grep 'background-color: rgba(255'` 仍命中遗留规则，TC 字面「无结果」不可达；改用 `style="background-color: rgba(255` 命中 0 证明内联清零。
- **陷阱**: 内联 style 优先级最高，搬进 `.textbox`/`.menu_left`/`.nextPageBox a` 是唯一零布局改法；但 `.textbox` 改前无 background 规则，换入基线的阳性对照须挑无内联竞争的 `.readBox`，否则扰动被内联盖住、对照恒 0 假通过。
- **陷阱**: 本仓 BookClass/BookRank 是 LF，Book/BookContent 是 CRLF。批量改写统一转 CRLF 会让 git 整文件全改；写前按文件实测 EOL，写后双向断言。
- **经验**: `page.goto(url+"#/x")` 只改 hash 不重载，上一用例注入的 `<style>` 会污染下一用例；每用例先 `goto('about:blank')`。

### T-011: 账号中心与内容管理页变量化
- **陷阱**: 第一版改写脚本在替换 `#hex` 时顺手给 `prop:value` 补了空格（`border:1px`→`border: 1px`），9 个文件因此多出 20 行非颜色 diff。正确做法是只做「HEX token 原位替换」：先 `text.find` 出 token 的起止，只把这段换成 `var(--nv-x)`，前后字符一律不动；再用「遮掉所有 hex 与 var() 后逐行比对」证明非颜色行 0 差异。
- **陷阱**: CSS 里颜色可能出现在没有 `prop:` 前缀的行（缩写/多行/`border:1px solid` 后换行续写），逐行取 `prop` 会拿到 None。要维护一个 carry：同一行无 prop 时沿用上一行的 prop，这样 `border-top:1px solid` 换行接 `#e0e0e0` 也能判成边框色而不是文字色。
- **陷阱**: 本仓 EOL 不统一：Login/Register/UserSetup/UserComment/user-Menu 是 CRLF，UserHistory/BookUpload/MyUpload/BookManage 是 LF。必须是「逐文件读二进制 → 记录该文件实际 EOL → 解码改写 → 按同一 EOL 编码写回」，写后断言 `\r\n` 数与 `\n` 数完全等于改前。
- **经验**: 浅色不变的三重证据比单一截图可靠：(a) 骨架 diff（hex 与 `var()` 全遮成同一占位符，9 文件 0 行非颜色差异）；(b) 变量按 `:root` 反向展开回字面量，与基线逐字节相同；(c) 真实浏览器改前/改后像素 diff，7/8 页 0 像素差异，注册页 3164 个差异像素 100% 落在验证码图片框内（动态内容）。
- **经验**: 新增 9 个变量是因为它们在现有色板里没有 1:1 对应：`--nv-text-label`(#aaa)、`--nv-text-time`(#bbb)、`--nv-text-icon`(#8c939d)、`--nv-btn-idle-bg`(#dfdfdf)、`--nv-border-panel`(#efefef)、`--nv-border-dotted`(#e3e3e3) 与三个第三方登录品牌色 `--nv-social-weibo/-qq/-wechat`。硬塞进相近的语义变量会改浅色观感（PRD 7.5 不允许）。
- **经验**: Element Plus 深色生效的判据不是「页面变黑」，而是取**计算样式**：`html.dark` 下 `.el-dialog` 背景 = `rgb(20,20,20)`、`.el-table th` = `rgb(20,20,20)`、上传文件名 = `rgb(207,211,220)`。只截图肉眼看深色很容易漏掉「组件仍是浅色、只是父容器变深」。
- **避坑（Element Plus 深色 + teleport）**: `.el-select` 下拉 `.el-popper`、`ElMessage`、`.el-dialog`、`.el-overlay` 都挂到 `body` 下，**不在页面组件的 DOM 子树里**。因此 (1) `<style scoped>` 里的选择器根本选不中它们；(2) 页面级 `background` 也覆盖不到它们；(3) 只能用 Element Plus 官方 `--el-*` 深色变量让它自己变深，不要写 `html.dark .el-popper { background:#xxx }` 之类覆写（本项目 TC 明令 `grep -rn 'html.dark .el-' frontend/src` 必须为空）。验证时必须显式打开下拉后在 body 下取 `.el-popper` 的计算样式。
- **避坑**: `.el-pagination.is-background .el-pager li.is-active` 这类官方组件内部状态，白字压品牌橙的对比度只有 2.78（浅色/深色都一样），属于 Element Plus 既有取值。本任务只变量化，不调官方组件设计，遇到时如实记录为「既有、超范围」，不要为了让对比度数字好看去改 `--nv-brand`。
- **避坑**: 本仓库**不是 Git 仓库**（`git rev-parse --is-inside-work-tree` 失败）。所有「改前基线」能力必须自己搭：改前把目标文件复制到 `.sdd/tmp/t011-baseline/` 并记 sha256，改后可随时比对/回滚到基线副本；绝不能依赖 `git checkout`。
- **避坑**: 改前/改后像素 diff 出现整条 footer 带差异（白 vs #f5f5f5）不是真差异，是「before」截图在 HMR 重建中途拍的。判据：把同一状态连拍三次，三次完全一致才可信；每页截图前先 `goto('about:blank')` 再整页 `goto`，不要只用 hash 跳转。

### T-012: 作者后台变量化（author 五页 + author/Register + author/Header）
- **陷阱**: 作者五个页面（BookAdd/BookList/ChapterAdd/ChapterList/ChapterUpdate）的 `<style scoped>` **是同一份全站共用样式表的拷贝**（约 10KB，含 `.userBox`/`.my_l`/`.updateTable`/`.comment_list`/`.pl_bar` 等大量本页根本用不到的历史规则）。`src/views/Register.vue` 已由 T-011 改造过同一份样式表，其映射就是**权威对照表**——对同一行做 `diff` 即可得到每个色值该用哪个 `--nv-*`，比自行推断快且不会出现同色异名。ChapterAdd 是唯一多出 `AI 工具栏` 段（`.ai-toolbar`/`.textarea`/`:deep(.el-dialog__body)`）的变体，但无颜色声明。
- **陷阱**: `color:` 的候选区分不能只看 HEX，要按**声明属性**分类：同一个 `#fff` 在 `color:` 上是 `--nv-text-inverse`，在 `background:` 上是 `--nv-bg-container`，在 `border-left:` 上是 `--nv-border-inverse`；同一个 `#eee` 在 `background:` 上是底色、在 `border-*:` 上是 `--nv-border-lighter`；同一个 `#eaeaea` 在 `background`（`.fast_tit .lines` 的 1px 分隔线）上语义是边框而不是底色。按值直接查表必然错。
- **陷阱**: CSS 里存在**跨行续写**（`border-top: 1px solid` 换行接 `#eee`）和**注释内色值**（`/*width: 998px; border: 1px solid #eaeaea;*/`、`/*color: #666666;*/`）。取值时要维护「同一块内 prop 向上回溯」，且要能剥离未闭合的 `/*` 前缀，否则会把注释里的 `#666666` 判成 `prop=None`。注释内色值同样要替换（T-011 对 `src/views/Register.vue` 就是这么做的），否则「色值清零」不达标。
- **陷阱**: `grep '#[0-9a-f]{3,8}'` 会命中 `&#8249;`（返回链接的 `‹` HTML 实体），它不是颜色。清零校验必须显式排除，否则永远清不干净，也不会误改——脚本里要先跳过这个 token，不能把它换成 `var()`。
- **陷阱**: 本仓 `git rev-parse --is-inside-work-tree` 在 `frontend/` 下**是 true**（T-011 记录的「不是 Git 仓库」指的是更外层目录）。但 `git diff` 对 Header.vue 会显示 46 行变化，其中 40 行是 T-011 之前就有的未提交改动（`back_link` 结构重写）。**判断本次 delta 必须对「自己开工前拍的基线副本」做 diff，不能用 `git diff`**，否则会把别人的未提交工作算进自己头上。
- **经验**: 「色值清零 + 浅色不变」用两段机械证明最可靠：(a) 把 HEX 与 `var(--nv-*)` 都遮成同一占位符做逐行 skeleton diff（7 文件全 0 差异）；(b) 把 `var(--nv-*)` 按 `:root` 展开回字面量、归一化 HEX 大小写与缩写（`#abc`→`#aabbcc`）后与基线**逐字节相同**（7 文件全 OK）。两段都过即等价于「浅色渲染不可能变化」，比单看截图强。
- **经验**: 真实浏览器 before/after 像素对比要做到 0 差异，关键是**用基线副本整体回滚文件**而不是靠 Git：先把改后版本存到 `.sdd/tmp/t012-final/`，把基线副本覆盖回工作区等 HMR 稳定，拍 before；再把 final 覆盖回去拍 after。6 个页面像素 diff 全为 **0**（含 1440x900 视口与 fullPage 高度）。
- **经验**: 作者后台**真的需要作者账号**：`author_info` 表初始为空，`admin` 登录后 `GET /api/author/books` 返回 `A0301 访问未授权`。可走真实链路自建临时作者：`POST /api/front/user/login` 拿 token → `POST /api/author/register` → `POST /api/author/book` → `POST /api/author/book/chapter/{bookId}`。注意作者接口前缀是 **`/api/author`**（`API_URL_PREFIX + "/author"`），不是 `/api/front/author`；`/api/front/author/**` 一律 404。
- **避坑**: Windows Git-Bash 里用 `curl -d '{"penName":"中文"}'` 传给 Spring 会因**控制台编码**把 UTF-8 弄成 GBK 字节，后端报 `JSON parse error: Invalid UTF-8 start byte 0xb2`。必须改用 Python `urllib` 显式 `encode('utf-8')` + `Content-Type: application/json; charset=utf-8`。
- **避坑**: 临时作者/书籍清理要按**精确主键**删，且顺序 `book_content → book_chapter → book_info → author_info`；清理后核对基线计数 `author_info=0 / book_info=108 / book_chapter=17756 / book_content=17756 / user_info=1`。**Redis 缓存也要清**：`Cache::Novel::authorInfoCache::1` 和 `Cache::Novel::bookContentCache::<章id>` 会自动写入，不删会让下次查询拿到已删数据的缓存。
- **避坑**: 深色下 `.s_input`（原生 `<select>`）的计算背景是 `rgb(59,59,59)`、`.textarea` 同值——这来自 Element Plus 的 `--el-fill-color-blank` 深色变量，**不是**页面 scoped 样式命中（原生控件不吃 `<style scoped>`）。不要误以为是变量化生效的证据；真正能证明本任务生效的是 `.userBox`/`.updateTable th`/`.mainNav` 这类页面自有选择器。
- **观察**: 浅色下 `.back_link` 白字压品牌橙导航条对比度 2.39、hover `#ffe8d1` 更降到 2.02；深色下同一链接是 16.70 / 12.58。浅色低对比属改造前既有取值（PRD 7.5 要求浅色不变），未调整，交由 T-013 统一走查决定是否另起需求。

### T-013: 主题体系收口（残余硬编码清扫 + Element Plus 全家桶 + 首帧 + 功能回归）

#### 一、最终变量白名单（新增页面 / 新代码可直接照抄）

全部变量只有一个来源：`frontend/src/assets/styles/theme.css`，`:root` 与 `html.dark` **两段同名同数**
（当前 134 个，顺序一致）。页面只消费 `var(--nv-*)`，不新建颜色常量。

> 下面按用途分组，同前缀的兄弟变量用「首项写全名、后续写 `-后缀`」的简写（如
> `--nv-text-primary` / `-regular` 表示 `--nv-text-regular`）。**唯一权威的完整枚举是 theme.css
> 本身**：`:root` 段与 `html.dark` 段各 134 个、同名同序，逐段比对 `diff` 应恒为 0。
> 想确认某个变量是否存在，直接 `grep -c -- '--nv-xxx:' frontend/src/assets/styles/theme.css`，
> 期望结果是 **2**（两段各一次）；结果是 1 说明只写了一段，深色下会取不到值。

- 背景：`--nv-bg-page`(页面底) / `--nv-bg-container`(卡片·白底) / `--nv-bg-overlay`(弹窗·下拉·消息) /
  `--nv-bg-subtle`(表头·悬浮行) / `--nv-bg-muted`~`-3`(中性填充四级) / `--nv-bg-hover`(灰按钮 hover) /
  `--nv-bg-raised` / `--nv-bg-warm`(顶栏) / `--nv-brand-tint`(品牌描边按钮 hover 底) / `--nv-bg-note`(提示条)
- 文字：`--nv-text-primary`(标题) / `-regular`(正文) / `-secondary` / `-weak`(辅助信息) / `-inverse`(反白) /
  `-strong` / `-body` / `-dim` / `-quiet` / `-note` / `-muted` / `-tertiary` / `-faint` / `-disabled` /
  `-ghost` / `-separator` / `-label`(字段标签) / `-time`(时间列) / `-icon`(图标) / `-field`(表单文字)
- 边框：`--nv-border`(表格·外框) / `-light` / `-lighter` / `-divider` / `-muted` / `-strong` / `-subtle` /
  `-medium` / `-soft` / `-shade` / `-faint` / `-hair` / `-hairline` / `-warm` / `-inverse`(白底隐形边框) /
  `-gray` / `-arrow`(小三角) / `-panel` / `-dotted` / `-field`(表单描边)
- 品牌 / 状态：`--nv-brand` `-brand-hover` `-brand-active` `-link`；`--nv-danger` `-danger-strong`
  `-danger-hover` `-danger-soft` `-danger-pure`；`--nv-success` `--nv-orange` `--nv-vip`；
  `--nv-accent-pink/blue/blue-alt/cyan/green/tab`
- 中性填充 / 装饰：`--nv-fill-muted`；`--nv-rank-1~3`、`--nv-level-1~11`（名次与等级徽标，**深色下刻意保持浅色值**，
  因为上面压白字）
- 表单：`--nv-input-bg`、`--nv-input-placeholder`；按钮：`--nv-btn-hover-text`、`--nv-btn-brand-tint`、
  `--nv-btn-idle-bg`、`--nv-btn-gray-bg`、`--nv-btn-danger-bg`
- 效果：`--nv-mask` `--nv-shadow` `--nv-shadow-strong` `--nv-shadow-medium` `--nv-shadow-grey`
  `--nv-shadow-inset` `--nv-shadow-warm` `--nv-scrim` `--nv-image-placeholder`
- 导航：`--nv-nav-bg`、`--nv-nav-link-line`、`--nv-nav-line`、`--nv-bg-nav-strong`、`-hover`、`--nv-nav-back-hover`
- 阅读页：`--nv-reader-panel-bg/-toolbar-bg/-toolbar-shadow/-line/-text/-title/-meta/-btn-shadow/-active/`
  `-on-brand/-order-border/-order-border-hover/-order-bg/-order-bg-hover/-chip-bg/-chip-bg-hover/-chip-active-bg`，
  色卡 `--nv-reader-theme-white/green/pink/yellow/gray/night`
- 第三方登录品牌色：`--nv-social-weibo/qq/wechat`

#### 二、新增页面如何接主题（照这个顺序做，不要自创）

1. **不要引入任何新色值**。先查上表，命中就直接用 `var(--nv-*)`。
2. 语义确实没有对应（极少数，例如新的第三方品牌色），**才**新增变量，并且必须：
   (a) `:root` 与 `html.dark` **两段同时定义、名字严格一致**（只写一段会让深色下取不到值、回退继承父级）；
   (b) 深色取值优先取 Element Plus 深色色阶（`#141414` / `#1d1e1f` / `#262727` / `#303132` / `#414243` /
   `#4c4d4f` / `#cfd3dc` / `#a3a6ad` / `#8d9095` / `#e5eaf3`），避免自定义区与 el-* 出现「两套深色」拼接感；
   (c) 到 theme.css 顶部「变量登记」表补一行。
3. 页面里只写 `color` / `background(-color)` / `border-*-color` / `box-shadow` / `outline-color`；
   **不写** `html.dark .xxx` 局部覆写，也**不写** `html.dark .el-*` 批量覆写（TC 门禁：该表达式计数必须为 0）。
4. Element Plus 组件一律交给官方 `theme-chalk/dark/css-vars.css`（`main.js` 已 require）。
   深色下 el-* 变深是「官方变量 + `html.dark` 根选择器」两个条件同时生效的结果，
   所以 **teleport 到 body 的组件（`.el-popper` / `.el-message` / `.el-dialog` / `.el-overlay` /
   `.el-message-box` / `.el-loading-mask`）也自动是深色的**，前提是 `html` 上有 `dark` 类——不是组件局部有。
5. 图片类资源（logo、图标）如果需要深浅两套，用 `computed` 按 `isDark()` 切 `src`，
   **不要**用 `filter: invert()`（会把品牌橙一起反色），也**不要**加 `html.dark .xx{background:url(...)}`。
6. 自测：`npm run lint`（本次文件 delta = 0）、`npm run build`、真实浏览器在 `http://localhost:1024` 里
   取 computed style 核对（见下条），不能只看截图。

#### 三、踩坑（本任务实测，后续直接复用结论）

- **陷阱（首帧取证）**: `page.add_init_script(OBSERVE)` 里如果传的是 `() => {...}` 这样的**箭头函数字面量**，
  Playwright 只会把它当一个表达式求值后丢弃，**不会执行**，于是 `window.__t013` 恒为空对象，
  所有字段都是 `null`——看起来像「观测到了空值」，其实是根本没装钩子。必须写 `"(" + OBSERVE + ")()"`。
  另外 init script 执行时 `document.documentElement` **可能还是 null**，取 class 前必须判空 + `setTimeout` 自旋。
- **经验（首帧实测结论）**: localStorage 预置 `novel-theme=dark` 后，`initTheme()` 在 `app.mount` **之前**执行。
  实测 4 个路由（home / bookclass / login / book_upload）顺序恒为「class 变更 → DOMContentLoaded → first-paint」，
  且 DCL 时刻 `classAtDCL="dark"`、`colorSchemeAtDCL="dark"`、`bgAtDCL=rgb(20,20,20)`，
  即 **class 先于首帧落地，无先浅后深闪烁**。绝对耗时随冷热缓存变化（home 首屏 1258 → 1259 → 1264ms，
  其余三个路由 990~1016ms），**只有顺序才是判据，不要拿绝对毫秒数当基线**。
  首个 rAF（t≈320~430ms）时 class 仍是空、body 背景还是 `rgba(0,0,0,0)`，说明此时还没绘制，属于正常。
- **经验（持久化语义）**: 清空 storage 时 `class` 恒空、`mutations=[]`（**根本没有发生 class 变更**）、
  `colorScheme` 被显式写成 `light`、body 为 `rgb(245,245,245)`；即使浏览器 `prefers-color-scheme=dark`
  也不会跟随——这就是 PRD 要求的「不跟随系统」。非法值（如 `purple`）同样回退浅色。
- **陷阱（v-loading 抓不到）**: `page.route(...)` 延迟接口**不足以**复现 `el-loading-mask`——axios promise
  一 resolve 遮罩就移除，来不及绘制。可靠做法是 CDP：
  `ctx.new_cdp_session(page)` → `Network.enable` → `Network.emulateNetworkConditions{latency:3000}`，
  再每 120ms 轮询 `.el-loading-mask`，实测第一次轮询就能抓到（深色 `rgba(0,0,0,0.8)`、浅色 `rgba(255,255,255,0.9)`，
  因为带 fade 所以 `opacity≈0.74`，是过渡中间值，不是缺陷）。
- **陷阱（el-message 触发不能写库）**: 想点亮 `.el-message` 不要点「保存」让它真提交。
  BookManage 的 `submitEdit()` 第一步就是 `if (!bookName || !authorName || !categoryId) ElMessage.error(...)`，
  清空书名再点保存即可命中校验分支并 `return`，**不会**发出 updateBook 请求。同理 `ElMessageBox` 的删除确认
  可以打开后点「取消」，实测库计数 108/17756/17756/0 前后一致。
- **陷阱（`.el-select-dropdown` 背景读不到）**: 直接对 `.el-select-dropdown` 取 computed `backgroundColor`
  会拿到 **`rgba(0, 0, 0, 0)`**，看起来像「下拉没变深」。原因：EP 2.2.0 把底色写在**外层 popper**上——
  `.el-select__popper.el-popper[role=tooltip] { background: var(--el-bg-color-overlay) }`，
  实测该 outer popper 深色下 = `rgb(29,30,31)`、bc `rgb(65,66,67)`。
  验收 TC 里写「读 `.el-select-dropdown` 的 backgroundColor 为深色」时，正确判据是
  **「dropdown 透明 + 它的 popper 祖先为深色」**，或者直接对 popper 取值；不要因为 dropdown 透明就判 FAIL。
  同理 `.el-select-dropdown__item` 的 bg 也是透明（fg `rgb(207,211,220)`），底色由 popper 提供。
- **陷阱（EP 2.2 固定列选择器）**: 2.2.0 **没有** `.el-table__fixed-right`（那是 3.x 的写法）。
  固定列是行内类 `td.el-table-fixed-column--right` / `th.el-table-fixed-column--right`，
  右侧阴影是 `::before` 的 `box-shadow: rgba(0,0,0,0.15) -10px 0 10px -10px inset`，
  未滚动时存在、`scrollLeft>0` 后变 `none`（深色浅色同值，属 EP 官方）。
- **经验（EP 全家桶深色实测值，可直接当回归基线）**: 深色下
  `.el-table th` bg `rgb(20,20,20)` fg `rgb(163,166,173)`；`.el-table td` fg `rgb(207,211,220)`；
  `.el-dialog` bg `rgb(20,20,20)`；`.el-overlay` `rgba(0,0,0,0.5)`；
  `.el-popper`（teleport，`#app` 内取不到 → `appRootAbsent=true`）bg `rgb(29,30,31)`、bc `rgb(65,66,67)`、
  `box-shadow rgba(0,0,0,0.72) 0 0 12px`；`.el-message`(error) bg `rgb(43,29,29)` 文字 `rgb(245,108,108)`；
  `.el-message-box` bg `rgb(20,20,20)` bc `rgb(54,54,55)`、主按钮 `rgb(51,117,185)`；
  `.el-tag--success` bg `rgb(28,37,24)` fg `rgb(103,194,58)`；
  `.el-table__empty-text` fg `rgb(163,166,173)`；`.el-loading-mask` `rgba(0,0,0,0.8)` 且 spinner `circle.path`
  stroke 仍是 `rgb(64,158,255)`（EP 主色，没有深色覆盖——EP 官方如此）。
- **陷阱（EP 主色不随品牌色）**: `.el-pagination.is-background .el-pager li.is-active`、`.el-button--primary`、
  `.el-loading-spinner` 全部用 EP 默认 `rgb(64,158,255)`（白字对比度 **2.78**），BookManage/BookUpload/MyUpload
  都没有覆写品牌色，而 BookClass/BookRank 有 `!important` 覆写成 `rgb(255,136,0)`。这是**改造前既有的不一致**
  （浅色深色都一样），本任务不动，仅记录。
- **观察（深色走查残余低对比，均属改造前既有装饰/品牌色，非本轮回归）**:
  `.num1/.num2/.num3` 名次徽标 2.75/2.28/1.89；`.btn_ora`/`.btn_ora_white` 与主导航白字压品牌橙 2.39；
  EP 主色按钮/分页 2.78；`.icon_qyzz` 2.65；footer 版权 `#999` **深色 6.47（达标）**。
  同一处 footer 在**浅色**下是 `#999` 压 `#f5f5f5` = **2.61**（排行榜等白底页是 2.85），
  这是改造前既有的浅色低对比，本轮不动（PRD 7.5 要求浅色 1:1 不变）。
  深色正文阅读区 **11.26**、标题 13.98、元信息 6.93，全部 ≥4.5；深色下走查的 13 个路由
  （10 个前台/账号页：home / bookclass / bookrank / book / bookcontent / login / register /
  user_setup / user_comment / user_history，加 3 个管理页：book_upload / my_upload / book_manage）的
  `lightBlocks`（浅色/半透明白块）实测**全为 0**。
- **陷阱（像素基线里的假 diff）**: 首页/详情页的「同类推荐」是**每次请求随机**的，
  所以 light before/after 出现 14997px 差异（bbox 落在右栏 `tj_bar`）不代表改坏了：同一状态连拍两次为 0，
  两次独立刷新复现同样的 bbox 但**内容不同**。注册页 3312px 差异落在验证码 bbox `(584,453)-(684,491)`，同理。
  判据固定为「同状态连拍为 0 + 差异区域是动态内容」。
- **经验（本任务唯一的真实视觉变化＝logo）**: 改造前/后整页像素对比（1440x900 fullPage）给出很干净的结论：
  浅色下 13 个页面里 **11 个 diff = 0**，只有 book 14997px（同类推荐区）与 register 3312px（验证码）不为零；
  深色下 **13 个页面全部**在同一个 bbox `(261,35)-(412,59)` 有 **1876px** 差异——这正是 Top.vue 把
  深色字 logo 换成白字版的位置（`bookshelf` 之前、`.logo` 内），属**本任务预期的唯一视觉改动**；
  book 另多 13666px、register 另多 3116px，与浅色那两处动态区域完全对应。
  也就是说：**除 logo 外，浅色与深色的渲染都没有发生任何变化**——这比逐页肉眼看截图强得多。
  logo 本身另有 canvas `getImageData` 取样为证：深色 `{white:4411, black:0}`、浅色 `{white:0, black:4411}`，
  两主题 `naturalWidth/Height` 均为 450x100、渲染矩形均为 216x48（尺寸未变，只换图）。
- **经验（布局未变，可机械证明）**: 对 13 个路由分别取 light/dark 下**每个元素的 boundingRect** 做逐项比对
  （`layout-equality.json`）。**除书籍详情页外**，12 个路由的元素数在两种主题下完全相等
  （home 726/726、bookrank 433/433、book_manage 436/436、bookcontent 166/166 …），
  几何差异各只有 **1 项**，就是主题图标 `path` 自身 17x17→18x18；详见下方「AC8 裁切实测值」。
  `document.scrollWidth - clientWidth` 两主题均为 **0**（无横向滚动条）。
  书籍详情页为什么不能这样比，见下方「详情页不能用跨主题几何比对当判据」。
- **陷阱（作者后台 route query 参数名）**: `ChapterList.vue:147`、`ChapterAdd.vue:199`、`ChapterUpdate.vue:134`
  读的都是 **`route.query.id`**，不是 `bookId` / `chapterId`。传错参数页面对后端发空 id，会弹
  「系统执行出错」红条（截图已存证），页面上只剩一个「章节发布」按钮。正确写法：
  `/#/author/chapter_list?id=<bookId>`、`/#/author/chapter_add?id=<bookId>`、`/#/author/chapter_update?id=<chapterId>`。
- **经验（残留 console 404 的来源）**: 走查中出现的 `Failed to load resource: 404` 全部是**封面图**
  `http://127.0.0.1:8888/localPic/**` 与 `http://127.0.0.1:8888/images/default.gif`（库里有记录、磁盘无文件，
  是历史数据问题，`onerror` 已兜底成 `default.gif`）。判定「无新增失败请求」要看 `requestfailed`
  计数（全程 0），不能只看 console error 条数。
- **陷阱（主题图标在 `path` 上）**: 深浅切换图标是 SVG，切主题时该 `path` 的 boundingRect 会从 17x17 变 18x18，
  做「两主题几何完全一致」比对时必须把它列为**预期白名单**，否则会误报布局变化。
- **陷阱（排行榜路由是 `/#/book_rank` 不是 `/#/bookrank`）**: 本仓路由表 `router/index.js` 里写的是
  `path: '/book_rank'`。用 `/#/bookrank` 访问**不会报错**，只会渲染一个空壳（实测 2 个元素、docH 900），
  于是「该页深浅几何一致、零裁切、零对比度问题」会全部**假通过**。
  同类易错路由：正文页 `/#/book/:id/:chapterId`、目录 `/#/chapter_list/:bookId`（注意不是 `book/`）。
  正确路径下排行榜实测 433 个元素、docH 2543、裁切 6/6（深浅一致）。
  防呆：每次走查脚本先断言 `document.querySelector('h3#rankName, .rankTable')` 存在，再取几何。
- **陷阱（详情页不能用「跨主题几何比对」当判据）**: 书籍详情右侧「同类推荐」每次请求随机抽 8 本书，
  换书会改变简介行数，从而改变**元素个数本身**（实测同一主题连开两次 174 vs 152 个元素、
  docH 在 1428/1438 之间抖动、30~35 项几何差异、推荐书名完全不同）。
  因此该页的判据只能是「**同一主题连开两次**也会产生同样量级差异」，不能拿 light/dark 的差值当回归。
  反之，其余 12 个路由元素数在 light/dark 下**完全相等**、几何差异仅 1 项（主题图标 `path`）。
- **经验（AC1 三态实测）**: 主题开关 `.theme_switch` 在 `.bookShelf.fr` 容器内、**位于**两个
  `v-if="!token"` / `v-if="token"` 分支**之前**，因此与登录态无关，三种身份都会渲染。
  实测匿名 / admin(`isAdmin=true`) / 普通用户(`isAdmin=false` + 任意 nickName) 三态、每种 9~12 条路由，
  `present=true`、`visible=true`、内含 `<svg>`、`rect=[1210,27,20,38]` 全部一致；
  点击一次后 `html.dark` 生效、body `rgb(245,245,245)`→`rgb(20,20,20)`、导航条→`rgb(29,30,31)`、
  `localStorage.novel-theme` 写为 `dark`，而 **`location.href` 全程不变**（无刷新即刻变色）；再点一次回到浅色。
  普通用户态无需建账号：`isAdmin` 与 `nickName` 都是前端读 localStorage 的展示字段，改标记即可复现同一 UI 分支。
- **经验（AC8 裁切实测值）**: 修正路由后 13 个页面在 light/dark 下「文字被裁切」逐条一致：
  home 5/5、bookrank 6/6、book 4/4、book_manage 3/3、bookclass 2/2，其余 8 个页
  （bookcontent / login / register / user_setup / user_comment / user_history / book_upload / my_upload）
  均为 **0/0**。全部是既有的
  `text-overflow: ellipsis` 书名列与 `.txt` 简介的 `overflow:hidden` 多行截断，主题切换不改变任何一条；
  13 个页面的 `scrollWidth - clientWidth` 两主题均为 **0**。

#### 四、禁止事项（新增样式/页面时硬约束）

- **禁止**修改 `theme.css` 里任何既有变量的**取值**；只允许按批次追加新变量（且两段同名同数）。
- **禁止**在业务文件里新建颜色常量、`filter: invert()` 调深色资源、JS 里写色值字符串。
- **禁止** `html.dark .el-*` 批量覆写；**禁止** `html.dark .xxx` 逐条覆写页面局部（变量段以外的覆写一律不允许）。
- **禁止**为了「对比度好看」去改品牌色、EP 官方主色或名次徽标色——这些是改造前既有取值，PRD 7.5 要求浅色 1:1 不变。
- **禁止**在样式任务里顺手改 `width/height/line-height/padding/margin/font-size/flex/grid`；
  发现裁切只记录并上报，另起 Bugfix。
- **禁止**改 `src/api/**`、`src/router/**`、业务逻辑、表单校验、`frontend/package.json`、
  `assets/styles/easyui.css`、`assets/styles/layer.css`。
- **禁止**在作者后台新增主题切换入口（PRD 非目标）。

#### 五、残留硬编码白名单（扫描后允许保留的全部项）

扫描命令（TC 口径）：`grep -rn -E '#[0-9a-fA-F]{3,8}\b|rgba?\(' --include=*.vue --include=*.css frontend/src`，
排除 `theme.css` / `easyui.css` / `layer.css` / `node_modules` 后，**全部**残留及结论：

1. `easyui.css`、`layer.css` —— 第三方遗留 / 未被引入，任务明令禁改，**保留**。
2. `theme.css` 自身 —— 变量定义处，本就是色的唯一来源，**保留（它就是白名单本体）**。
3. `BookContent.vue` 的 24 处色值 —— 全部位于 `.read_style_1~6` 遗留选择器内
   （`read_style` 在 template 与 script 中出现 **0** 次，运行时不挂类，死样式）；任务明令保留，**保留**。
4. `BookContent.vue` 另有 **5 行** IE `filter: progid:DXImageTransform.Microsoft.gradient(...)`
   （L397 / L403 / L1063 / L1074 / L1082；每行嵌 2 个 hex token，所以按「色值命中数」会数成 10，
   按「行」数只有 5 —— 两种口径都记下来，免得下次对不上账），外加 5 行 `filter: alpha(opacity=NN)`
   （L1006 / L1012 / L1016 / L1054 / L1144）—— 现代浏览器全部 inert，**保留**。
5. `author/Header.vue:5`、`author/Register.vue:3` 的 `&#8249;` —— HTML 实体（`‹`），不是颜色，**保留**。
6. **只存在于 CSS 注释里的色值 33 处** —— `base.css` 9、`main.css` 9、`book.css` 1、`BookContent.vue` 14。
   这是最容易漏掉的一类：不剥注释时全仓 raw 命中 **69** 处，剥掉 `/* */` 后 live 只剩 **36** 处
   （`BookContent.vue` 34 + 两个 `&#8249;`）。注释里的色值不参与渲染，**保留**。
   注意统计口径差异：T-011/T-012 的「色值清零」要求连注释内色值一起替换，本任务是「**live** 色值清零」，
   两者对注释处理不同，跨任务比对数字时不要混用。

除以上 6 类外，`frontend/src/**` 已无**参与渲染**的未说明色值；`html.dark .el-` 计数 = **0**。

[SYSTEM] 建议回传系统级经验：
- 大范围「样式变量化」必须分页分任务，且每步保留浅色基线（改前副本 + sha256 + 像素 diff），
  一次性全站替换无法定位「哪一页先坏」。
- 「深色是否生效」的判据必须取 **computed style**，不能看截图；「深色是否闪」的判据必须取
  `DOMContentLoaded` 时刻的 `document.documentElement.className`，不能靠肉眼录屏。
- 需要在浏览器里点亮 loading / message / dialog 这类瞬态或 teleport 组件时，优先用
  「CDP 延时 + 轮询选择器」和「命中校验分支但不写库」的方式，避免为了取证产生真实副作用数据。
- 回滚一律靠「开工前的文件副本」，不要依赖 `git checkout/reset/clean`——在有大量未提交工作的仓里等同于永久丢工作。
