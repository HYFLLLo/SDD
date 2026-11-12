# Bug 修复报告：上传 txt 返回 B0001（book_info.pic_url 缺默认封面）

## 用户原话

> 继续修 novel 的 T-002 pic_url 缺陷（承接 memory 进度：T-002 判定 FAIL，任务状态 fixing）

## 经验回查

- 是否已有相关经验：是（部分）
- 相关经验：
  - 项目 `.sdd/experience.md`「T-002」已记：上传接口 `author_id` 固定 0、A0702~A0706 错误码、BOM/编码、缓存清理必须在事务内等。但**未提示** `book_info` 表 `pic_url` 列是 NOT NULL 无默认值，也未要求建 `BookInfo` 时必设 `picUrl`。
  - 系统级 `memory/harness-experience.md`「真实启动契约验证前必须先确认端口监听进程是当前代码」——本次验证严格遵守。
- 为什么仍然犯错：T-002 验收仅靠「编译通过 + curl」定位 INSPECT，缺「对照 DDL 逐个确认 NOT NULL 无默认值列都必须赋值」的验收点。经验没有沉淀成明确规则。

## 问题分析

- 现象：上传合法 UTF-8 三章 txt，接口返回 `{"code":"B0001","message":"系统执行出错"}`，无任何入库。
- 影响范围：AC1/AC2/AC3 全挂；上传功能整体不可用。
- 直接原因：`BookUploadServiceImpl.doUploadBook()` 建 `BookInfo` 时未调用 `setPicUrl()`。
- 根本原因：MySQL `book_info.pic_url` 列 NOT NULL 且无默认值，INSERT 缺少该列抛 `SQLException: Field 'pic_url' doesn't have a default value`，事务回滚成 B0001。
- 涉及文件：`src/main/java/io/github/xxyopen/novel/service/impl/BookUploadServiceImpl.java`
- 涉及契约：`.sdd/tasks.json` T-002 验收标准

## 修复方案

- 修改文件：
  1. `src/main/java/io/github/xxyopen/novel/service/impl/BookUploadServiceImpl.java`：`doUploadBook()` 在 `bookInfoMapper.insert(bookInfo)` 前补 `bookInfo.setPicUrl("/img/default-cover.gif")`。
  2. 新增 `src/main/resources/static/img/default-cover.gif`（复用前端 `novel-front-web/src/assets/images/default.gif`，420×560，随 jar 打包）。
- 修改说明：
  - 选 classpath 静态资源而非磁盘 `D:/novel-upload`，因为 `FileInterceptor` 独占 `/image/**` 且读磁盘（当前磁盘无图），而 `/img/**` 走 Spring 静态映射零依赖、随 jar 走、环境无关。
  - 不动 DB 结构、不动 seed 书（seed 的 `/localPic/**` 封面是官方仓库本地坏链，不在本次范围）。

## 验证方式

- 真实启动（`mvnw.cmd spring-boot:run`，JAVA_HOME=JDK21，MAVEN_OPTS 指向 D:/tools/infra/m2-repo），8888 = 本构建（PID 9836），MySQL 3306 + Redis 6379 已起。
- 封面：`GET /img/default-cover.gif` → 200 `image/gif`,10189 字节。
- 上传：合法三章 txt → `{"code":"00000",...,"chapterCount":"3","wordCount":"88"}`。
- DB：`book_info.pic_url = /img/default-cover.gif`；`book_chapter`×3、`book_content` 写入，正文 92 字节 UTF-8 无损（HEX 首字节 `E5A49CE9878C`=「夜里,那轮」）。
- 阅读：`GET /api/front/book/{id}`、`chapter/list`、`content/{chapterId}` 均 00000，`bookContent` 顶层字段返回正文。
- 搜索：`/api/front/search/books?keyword=书名` → total:1 命中（DbSearchServiceImpl，ES `enabled:false`）。
- 回归：首页 `code:00000`；seed 书详情正常，封面 `/localPic/...` 保持原样；`book_info` 107→109（+2 本验证书）。

## experience.md 更新

- 新增条目：`Bugfix: book_info.pic_url NOT NULL 无默认值导致上传 B0001`（见 experience.md）。
- 后续避坑规则：
  - 建 `BookInfo` 时对照 `novel_struc.sql` DDL，**NOT NULL 无默认值的列必须全部赋值**（pic_url/book_name/author_id/author_name/book_desc）。
  - 默认封面放后端 classpath `resources/static/img/` + `picUrl=/img/...`，别用 `/image/**`（被 FileInterceptor 拦截读磁盘）。
  - 上传/入库类改动必须对照 DDL 逐列核查，验收加「insert 能真实落库」而非仅编译通过。