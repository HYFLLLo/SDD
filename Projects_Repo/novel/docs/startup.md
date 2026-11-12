# 启动文档 — novel 小说精品屋（上传图书功能）

> 本文件由 SDD Harness 在开发阶段全部功能自动验证通过后产出（见 `harness-core/protocols/development-rules.md`）。
> **安全约定：本文件不含任何真实密钥/密码值。** 所有敏感项仅给出配置字段名，真实值请从 `src/main/resources/application.yml` 或部署环境变量中获取。

---

## 1. 环境要求

| 组件 | 版本要求 | 本项目验证版本 | 说明 |
|---|---|---|---|
| JDK | 21+ | 21.0.12.1+1 | 必须指向 JDK 根目录（注意 `D:\tools\jdk21` 本身不是 JDK 根，实际在子目录） |
| Maven | 随 `mvnw.cmd` | wrapper | 使用项目自带 wrapper，**不要**用系统 `mvn` |
| MySQL | 8.0+ | 8.0.28 | 必需，后端强依赖 |
| Redis | 5+ | 5（Windows 版） | 必需，后端强依赖；**Redis 未启动会导致后端启动失败** |
| Node.js | 16+ | 24.14.0 | 仅前端需要 |
| npm | — | 11.9.0 | 仅前端需要 |

**关键依赖关系**：MySQL 与 Redis 是后端的硬依赖，任一未就绪后端都会启动失败。正确启动顺序为 **MySQL → Redis → 后端**。

---

## 2. 启动步骤

### 2.1 启动 MySQL

```bash
mysqld.exe --defaults-file=<MySQL 安装目录>/my.ini
```

默认监听 `3306`。数据库需已导入 `doc/sql` 下的初始化脚本（库名 `novel`）。

> 重要：`novel_data.sql` / `novel_struc.sql` 只在首次初始化时导入一次。日常关机后重新启动**不要**重新导入种子 SQL，否则已删除的书籍会被恢复。`start-novel.ps1` 不会导入这些文件，只会启动现有 MySQL 数据目录并做幂等迁移。

### 2.2 启动 Redis

```bash
redis-server.exe redis.windows.conf
```

默认监听 `6379`。

### 2.3 启动后端（端口 8888）

```bash
# Windows（Git-Bash / PowerShell）
set JAVA_HOME=<JDK 安装根目录>
set MAVEN_OPTS=-Dmaven.repo.local=<本地 Maven 仓库目录>
mvnw.cmd spring-boot:run
```

启动成功标志（日志）：

```
Tomcat started on port 8888 (http) with context path '/'
Started NovelApplication in ... seconds
```

验证：

```bash
curl http://127.0.0.1:8888/api/front/home/books
```

### 2.4 启动前端（端口 1024）

```bash
cd frontend
npm install        # 首次
npx vue-cli-service serve
```

启动成功标志：`App running at: - Local: http://localhost:1024/`

---

## 3. 默认配置说明

### 3.1 后端（`src/main/resources/application.yml`）

| 配置项 | 值 | 说明 |
|---|---|---|
| `server.port` | `8888` | 后端服务端口 |
| `spring.servlet.multipart.max-file-size` | `100MB` | 上传单文件上限 |
| `spring.servlet.multipart.max-request-size` | `100MB` | 上传请求上限 |
| `spring.datasource.url` | `jdbc:mysql://localhost:3306/novel?...` | 数据库连接 |
| `spring.datasource.username` / `.password` | — | **敏感，见配置文件** |
| `spring.data.redis.host` / `.port` | `127.0.0.1` / `6379` | Redis 连接 |
| `spring.data.redis.password` | — | **敏感，见配置文件** |
| `spring.elasticsearch.enabled` | `false` | 关闭 ES；搜索引擎走 DB 实现 |
| `spring.shardingsphere.enabled` | `false` | 关闭分库分表 |
| `novel.file.upload.path` | Windows 可用路径 | **仅供 `/image/**` 磁盘映射使用**，上传图书功能不依赖它 |
| `novel.cors.allow-origins` | `http://localhost:1024` 等 | 允许跨域的前端来源（端口变更需同步修改） |
| `novel.jwt.secret` | — | **敏感，见配置文件** |

### 3.2 前端（`frontend/.env.development`）

| 配置项 | 值 |
|---|---|
| `VUE_APP_BASE_API_URL` | `http://127.0.0.1:8888/api` |
| `VUE_APP_BASE_IMG_URL` | `http://127.0.0.1:8888` |

> 前端**直连后端**（无 Vite/webpack 代理）。封面地址 = `VUE_APP_BASE_IMG_URL` + `picUrl`。

---

## 4. 本功能（上传图书）使用说明

1. 打开 `http://localhost:1024`
2. 顶部导航栏点击「上传图书」
3. 选择 `.txt` 或 `.epub` 文件（≤ 100MB），填写书名、作者（选填）、作品方向、分类、简介（选填）
4. 点击「上传」→ 页面显示解析出的章节数与总字数
5. 该书可在首页推荐 / 搜索结果中找到，点击进入分章阅读

**接口**：`POST /api/front/resource/book/upload`（前台免登录，`multipart/form-data`）

**默认封面**：`/img/default-cover.gif`（随 jar 打包，走 Spring 静态资源映射；不使用 `/image/**`，该路径由 `FileInterceptor` 映射到磁盘上传目录）

### 支持的解析能力

| 格式 | 解析方式 | 章节划分 |
|---|---|---|
| `.txt` | 编码识别（UTF-8 / UTF-8 BOM / GBK） | 正则匹配中文章节标题（第 N 章/回/卷…、序章、楔子、Chapter N 等） |
| `.epub` | zip → `META-INF/container.xml` → OPF → spine | 按 spine 顺序，一个 xhtml 一章；jsoup 提取纯文本 |

### 错误码

| 码 | 含义 |
|---|---|
| `A0702` | 文件大小超过限制 |
| `A0703` | 不支持的文件格式 |
| `A0704` | 图书文件解析失败（解析后无有效章节，或文件损坏） |
| `A0705` | 同名图书已存在 |
| `A0706` | 上传文件为空 |

---

## 5. 常见问题

| 现象 | 原因与处理 |
|---|---|
| 后端启动失败，日志报 `Connection refused: 127.0.0.1:6379` | Redis 未启动，先启动 Redis |
| 后端启动失败，数据库连接异常 | MySQL 未启动或库 `novel` 未导入 |
| 上传返回 `B0001` 系统错误 | 检查后端日志的 SQL 异常；`book_info` 有 NOT NULL 无默认值列（`pic_url`/`book_name`/`author_id`/`author_name`/`book_desc`），入库前必须全部赋值 |
| 封面显示裂图 | 默认封面走 `/img/**` 静态映射；`/localPic/**`（部分种子数据）在本地不受后端服务，属既有行为 |
| `mvnw.cmd -Dmaven.repo.local=...` 报参数错误 | 本地仓库路径必须通过 `MAVEN_OPTS` 环境变量传入，不能直接作为命令行参数 |
| 前端 1024 跨域失败 | 确认 `novel.cors.allow-origins` 包含实际前端来源 |

---

## 6. 测试工具（可选）

项目 `.sdd/tools/` 下提供了开发期验证脚本（非运行时依赖）：

| 脚本 | 用途 |
|---|---|
| `make-epub-samples.py` | 生成合法 / 损坏 epub 测试样本 |
| `epub-smoke-test.py` | epub 上传与读取验证 |
| `e2e-smoke-test.py` | 端到端冒烟（txt + epub 全链路） |
| `browser-e2e.py` | 浏览器自动化 E2E（Playwright） |

