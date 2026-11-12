# 测试报告：T-007 历史书「仙逆」回填 + 全链路 E2E 回归

**结论：PASS**

测试时间：2026-10-21 10:01–10:26（Asia/Shanghai）  
验证方式：MySQL 实库查询、Maven 重打包 jar、前端开发服务真实启动、HTTP 接口实测、Chrome headless 真实浏览器 E2E、数据库单事务清理。  
运行 PID：后端 8888 = java PID 19964；前端 1024 = node PID 12820；均为本次构建/启动进程，测试后已停止，端口均释放。

## 验收项结果

| # | 验收项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 「仙逆」归属 admin 并出现在我的上传 | PASS | DB：`id=1431630596354977796`、`book_name=仙逆`、`author_id=0`、`author_name=匿名用户`、`uploader_id=1`；admin `user_info.id=1`。管理员列表返回 `code=00000,total=1`，首条 `bookName=仙逆, authorName=匿名用户, bookStatus=0, chapterCount=1960`。浏览器 `#/my_upload` 可见「仙逆」 |
| 2 | 归属持久化 / 刷新 / 重登 | PASS | 浏览器刷新 `/my_upload` 后仍可见「仙逆」；重新登录后再次进入仍可见；DB `uploader_id=1` 不变 |
| 3 | 管理员上传新书后列表首条 | PASS | Chrome 真实上传 txt `T007BrowserAdmin`：`POST /api/front/resource/book/upload` 返回 `bookId=1431630596354977828`；DB `uploader_id=1`；管理员列表按 `create_time desc` 首条为该书，`total` 从 1 增至 2 |
| 4 | 状态切换为已完结 | PASS | 浏览器点击「设为已完结」后，列表 `bookStatus=1`；`GET /api/front/book/1431630596354977828` 返回 `bookStatus="1"`；筛选 `bookStatus=1` 能查到该书。清理前已完成刷新/列表复验 |
| 5 | 匿名上传不进管理列表 | PASS | 清空登录态后浏览器上传 `T007BrowserAnon`，DB `uploader_id=0`；管理员列表 `total` 保持 3（不含匿名书）；搜索 `keyword=T007BrowserAnon` `total=1`；`GET /book/{id}`、`GET /book/content/{chapterId}` 均可阅读 |
| 6 | 现有功能回归 | PASS | `home/books`、`search/books`、`book/{id}`、`book/content/{chapterId}` 均 `code=00000`；浏览器从「仙逆」详情点击阅读进入 `#/book/1431630596354977796/1445988184596995316`，可见章节与正文；txt 与 epub 上传均成功 |
| 7 | 回填幂等且不影响其他书 | PASS | 脚本重复执行输出 `Rows matched: 0, Changed: 0, Warnings: 0`；基线时 `uploader_id<>0` 仅 1 行且为「仙逆」；测试清理后恢复为仅「仙逆」1 行 |

## 技术检查明细

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 回填落盘并实库执行 | PASS | `doc/sql/uploader_id_backfill_2026-10-20.sql` 存在；重复执行 `Query OK, 0 rows affected`；目标行 `uploader_id=1=admin.id` |
| 2 | 幂等与范围 | PASS | 测试前 `non_zero=1,xian_ni_non_zero=1`；清理后同为 `1/1`，无其他书被归属 admin |
| 3 | 端口属于本次构建 | PASS | Maven `package` BUILD SUCCESS；前端 `Compiled successfully`；`8888=PID 19964(java)`、`1024=PID 12820(node)`；验证后均停止且端口释放 |
| 4 | 管理员 E2E | PASS | 登录、我的上传、txt 上传、列表 total +1、首条新书、状态切换、详情 `bookStatus=1` 均通过 |
| 5 | 匿名 E2E | PASS | 无 token 上传 `uploader_id=0`；管理列表不包含；搜索与分章阅读通过 |
| 6 | 权限复测 | PASS | 无 token GET = `A0230`；普通用户 GET/PUT = `A0301` |
| 7 | 回归接口 | PASS | 四个既有接口均 `00000`；txt/epub 上传均成功 |
| 8 | 数据清理 | PASS | 基线 `book_info=109, book_chapter=19716, book_content=19716`；单事务按 `book_content → book_chapter → book_info` 删除全部 T007 测试书并删除普通用户；清理后三表回到基线 |
| 9 | 无 Mock 残留 / 真实 Network | PASS | `src` 与 `public` 搜索 `mock/Mock/MOCK` 无命中；`.env.development` 指向 `http://127.0.0.1:8888/api`；浏览器 Network 记录全部命中 `http://127.0.0.1:8888/api/**` |

## 真实证据摘录

- 登录：`{"code":"00000","data":{"uid":"1","nickName":"admin","admin":true}}`
- 浏览器步骤：`S1 login ok uid=1, isAdmin=true` → `S2 my_upload contains XianNi` → `S3 browser admin txt upload success` → `S5 my_upload contains newly uploaded book` → `S6 my_upload persists after reload` → `S7 anonymous browser upload success`
- 浏览器状态切换：`BROWSER_PUT_SUCCESS`；随后详情返回 `"bookStatus":"1"`
- 权限：无 token `A0230 用户登录已过期`；普通用户 `A0301 访问未授权`
- epub：`{"code":"00000","data":{"bookId":"1431630596354977830","chapterCount":"1","wordCount":"16"}}`
- 清理后残留搜索：`T007TxtE2E/T007BrowserTxt/T007BrowserAdmin/T007BrowserAnon/T007Epub/t007normal` 全部 `total=0`
- 数据清理后：`book_info=109`、`book_chapter=19716`、`book_content=19716`；`uploader_id<>0` 仅「仙逆」

## 观察项

- 前端 dev 环境只有 `localhost:1024` 在后端 CORS allow-list 中，`127.0.0.1:1024` 会被 CORS 拒绝。用户需使用 `http://localhost:1024` 访问；不影响本任务验收。
- 一次浏览器调试过程中出现 `Cannot read properties of null (reading 'setAttribute')`，隔离复测 `/my_upload` 页 `pageerror=[]`，判定为调试脚本交互时序/组件过渡期问题，非稳定页面错误。
- PowerShell `Set-Content -Encoding UTF8` 生成带 BOM 的 txt，上传解析会剥离 BOM；HTTP 直传响应仍正确解析 2 章。这是测试文件生成方式的影响，不是应用缺陷。
- E2E 截图：`.sdd/tmp/t007_browser.png`、`.sdd/tmp/t007_browser_put.png`、`.sdd/tmp/t007_read.png`（保留作为证据）。

## 环境处理

- MySQL / Redis 未由 Tester 启停，仅连接验证。
- Tester 启动的后端 PID 19964 与前端 PID 12820 已全部停止；`8888`、`1024` 均无监听。
- 未修改业务代码；仅更新 `.sdd` 验收记录。
