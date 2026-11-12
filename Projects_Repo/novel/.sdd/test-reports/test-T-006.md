# 测试报告：T-006「我的上传」管理接口 + 前台入口与管理页（含真实联调）

**测试时间**：2026-10-21 09:24 ~ 10:00  
**Tester Agent ID**：codex/tester（SDD V7.1）  
## 结论：PASS

后端编译、前端构建、真实后端/前端联调、接口契约、权限/错误码、缓存同步、N+1 检查与浏览器真实操作均独立复现通过。测试数据已恢复基线。全仓 lint 仍存在既定 116 个历史错误；本次新增/改动文件单独 ESLint 为 19 个错误，但其中 17 个在任务前基线已存在，2 个为 `vue/multi-word-component-names` 因基线文件名导致且同文件基线已有同类规则错误；逐一对照后未见 T-006 新增 lint 错误。

## 验证环境与进程归属
- 后端：`mvnw.cmd spring-boot:run`，Java 21.0.12.1，8888 监听 PID 9944，本次启动后 `Started NovelApplication in 20.335 seconds`。
- 前端：`npm run serve`，1024 监听 PID 7796，本次启动后 `Compiled successfully in 18615 ms`。
- MySQL 8.0.36 / Redis 5 为 Orchestrator 已启动服务，Tester 未启停。
- 8888/1024 验证前均无监听，验证期间 PID 均属于本次构建；验证结束后由 Tester 停止。

## 技术检查
| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 后端编译 | PASS | `mvnw.cmd compile` exit 0，`BUILD SUCCESS` |
| 2 | 前端构建 / lint | PASS（历史 lint 观察项） | `npm run build` exit 0；`npm run lint` 复现 116 个历史错误；新增/改动文件单独 `npx eslint` 19 errors，对照 HEAD 同文件基线 19 errors，delta=0 |
| 3 | 端口进程归属 | PASS | 8888=PID 9944、1024=PID 7796，均为本次启动 |
| 4 | 列表契约 | PASS | admin token：`code=00000`，`pageNum/pageSize/total/pages/list` 齐全；默认 `pageSize=10`；`id/bookStatus/wordCount/chapterCount` 均为字符串；`createTime=yyyy-MM-dd HH:mm:ss`；create_time 倒序 |
| 5 | 筛选与分页 | PASS | 不传 status total=12；status=0 total=6；status=1 total=6；pageSize=5 时 page1/page2 均返回 5 条且 pages=3，第二页为第 6~10 条 |
| 6 | 状态切换与缓存 | PASS | `PUT bookStatus=1` → `00000`；DB `book_info.book_status=1`；随后 `GET /api/front/book/{id}` 返回 `bookStatus=1`，证明 Caffeine 已清理；重复同状态请求 `00000` |
| 7 | 权限与错误码 | PASS | 无 token `A0230`；普通用户 `A0301`（列表与更新均验证）；不存在/非本人 `A2002`；`bookStatus=2` `A0400` |
| 8 | 浏览器真实操作 | PASS | Chrome headless 实测：admin 登录后出现「我的上传」，进入 `/my_upload` 展示测试书；筛选、状态切换、刷新可用；Network 请求均命中 `http://127.0.0.1:8888`，无 Mock |
| 9 | chapterCount 无 N+1 | PASS | 分页 10 条 SQL：用户校验 1 + count 1 + 主分页 1 + 章节 `GROUP BY` 1，共常数 4 条；章节统计为单条 `select ... where book_id in (?,...10) group by book_id` |
| 10 | 控制台与普通用户直访 | PASS | `pageerror` 为空；控制台仅既有静态图片 404；普通用户直访 `/my_upload` 不白屏，显示「访问未授权」，表格 0 行，未展示 admin 书目 |

## Acceptance Criteria 逐条结论
| # | 标准 | 结果 | 说明 |
|---|---|---|---|
| 1 | 未登录/普通用户导航不显示入口 | PASS | 未登录与普通用户 localStorage 场景均实测入口不存在 |
| 2 | admin 登录入口与列表 | PASS | admin/admin 登录 `data.admin=true`；页面出现入口并展示 admin 名下书目 |
| 3 | 倒序、分页、字段展示 | PASS | 每页 10 条、create_time 倒序、翻页正确；书名/作者/分类/字数/章节数/上传时间/状态均渲染 |
| 4 | 状态筛选 | PASS | 已完结、连载中、全部行为均通过浏览器真实点击验证 |
| 5 | 设为已完结 | PASS | DB、列表、刷新后前台详情均同步为已完结 |
| 6 | 切回连载中 | PASS | 浏览器点击后接口、列表与详情均同步为连载中 |
| 7 | 普通用户/未登录直访 | PASS | 未登录跳转登录；普通用户返回 A0301 并显示错误提示，无书目、无修改能力 |
| 8 | 加载/空态/失败 | PASS | 页面有 loading、空态文案和 error alert；A0301 场景显示明确错误且不白屏 |
| 9 | admin 登录无手机号错误 | PASS | placeholder 为「用户名 / 手机号」，admin 登录无「手机号格式不正确」弹错 |

## 关键接口证据
- `admin/admin`：`code=00000`，`data.admin=true`；普通用户 `t006testuser`：`code=00000`，`data.admin=false`。
- 列表第一页响应：`pageNum="1"`、`pageSize="10"`、`total="12"`、`pages="2"`，`id/bookStatus/wordCount/chapterCount` 均为字符串。
- 状态筛选：不传 total=12；`bookStatus=0` total=6；`bookStatus=1` total=6。
- 分页：`pageSize=5` 时 page1/page2 各 5 条、`pages="3"`；第二页 ID 连续衔接第一页。
- 状态切换：bookId `1431630596354977815` 切换 1 后 DB 与详情均为 1；同状态重复请求仍 `00000`。
- 错误码：`A0230/A0301/A2002/A0400` 全部按契约返回。
- 浏览器网络命中：`http://127.0.0.1:8888/api/front/upload/books?...` 与 `http://127.0.0.1:8888/api/front/upload/book/.../status`，无 Mock。

## 浏览器证据
- 截图：`.sdd/tmp/t006_admin_final.png`（admin 列表）、`.sdd/tmp/t006_normal_real.png`（普通用户无权限）。
- admin 操作：登录 → 导航入口 → `/my_upload` → 列表/筛选/切换状态；`pageerror=[]`。
- 普通用户操作：带普通用户 token 直接访问 `/my_upload`，返回 `A0301`，页面显示「访问未授权」，表格 0 行。
- 未登录访问 `/my_upload`：跳转登录页，不白屏，不展示上传书。

## 数据清理（恢复基线）
测试前基线：`book_info=109`、`book_chapter=19716`、`book_content=19716`、`user_info` 仅 admin 1 条。  
测试后按单事务顺序删除 `book_content → book_chapter → book_info`，并删除临时普通用户。复核：`book_info=109`、`book_chapter=19716`、`book_content=19716`、`user_info=1`、`book_name LIKE 'T006 %'` 为 0。

## 观察项（不影响 T-006 判定）
1. 全仓 lint 仍为 116 个历史错误，与 work-log 记录一致；本次新增/改动文件对照 HEAD 的 lint 错误数 delta 为 0。
2. 首页/页面存在既有静态资源 404（`/localPic/**`、`/images/default.gif` 等），与历史报告一致；`pageerror` 为空，非本任务引入。
3. MySQL `utf8mb4_0900_ai_ci` 用户名大小写不敏感仍是 T-005 遗留观察项，与 T-006 行为一致，未见新增风险。