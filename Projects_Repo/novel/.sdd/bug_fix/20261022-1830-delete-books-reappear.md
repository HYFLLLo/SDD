# Bug 修复报告：删除书籍后再次登录又出现

## 用户原话

> 我记得昨天用的时候删除了好多书籍，但是今天重新登录的时候又出现了，相当于删除这个操作并不是持久化的行为

## 经验回查

- 是否已有相关经验：是
- 相关经验：
  - `20261021-1620-delete-book-homepage-cache.md`：删除后首页缓存未同步失效
  - `.sdd/experience.md`「新增后端接口后必须重新 package 并重启 8888 进程」
- 为什么仍然犯错：本次不是删除代码再次漏改缓存；现象是数据本身被恢复，需区分“缓存残留”和“数据被重新导入”

## 问题分析

- 现象：昨天删除大量书籍，今天重新登录后书籍又出现
- 影响范围：前台首页推荐、全站书籍管理列表
- 直接原因：当前数据库又回到了接近初始种子的状态
- 根本原因：不是 `DELETE /api/front/upload/book/{bookId}` 没有持久化，而是删除发生后数据被恢复/重新导入（历史 `novel_data.sql` 等初始化数据）。工作日志显示删除后曾只剩 9 本 `book_info`，而当前 `book_info` 有 108 行（107 行种子数据 + 丹道宗师），说明删除后的状态被后续数据恢复覆盖

## 修复方案

- 本次无需修改删除接口代码；当前代码已包含 2026-10-21 的缓存同步修复
- 已重启到当前 jar，删除逻辑已生效
- 规则：业务验收期间不得再次导入 `novel_data.sql` 等种子数据；`start-novel.ps1` 只做迁移检查，不导入业务数据

## 验证方式

- 终端验证：以 admin 登录后调用 `DELETE /api/front/upload/book/1431630596354977815`，返回 `00000`
- 数据库验证：删除后以下表均无残留：`book_info`、`book_chapter`、`book_content`、`user_read_history`、`user_bookshelf`、`home_book`、`book_comment`、`book_comment_copy1`、`book_comment_reply`
- 首页验证：删除后 `GET /api/front/home/books` 返回 `00000`

## experience.md 更新

- 新增条目：删除后书籍复现时，先查“是否重新导入种子 SQL”，不要直接判定 delete 接口不持久化
