# Bug 修复报告：删除书籍后首页仍显示已删除书籍

## 用户原话

> 现在还有一个问题，就是我删除了一些书籍后，返回首页还是有之前没删除的书籍，点进去出现系统错误

## 经验回查

- 是否已有相关经验：是
- 相关经验：管理员全站书籍管理条目中已提到删除书籍需清理 `home_book`、`user_read_history`、`user_bookshelf`、评论及回复，避免首页推荐/书架出现残留
- 为什么仍然犯错：实现时删除了数据库关联数据，但遗漏了 `homeBookCache` 及排行榜等列表缓存的失效

## 问题分析

- 现象：删除书籍后首页仍展示已删除书籍；点击进入详情返回系统错误
- 影响范围：首页推荐、点击榜/新书榜/更新榜，以及书籍详情接口
- 直接原因：`UploadServiceImpl.deleteBook` 只调用 `bookInfoCacheManager.evictBookInfoCache(bookId)`，未清除 `homeBookCache`、排行榜缓存、`lastUpdateBookIdListCache`
- 根本原因：列表/详情缓存不同步；`BookInfoCacheManager.cachePutBookInfo` 对不存在的 bookId 未做 null 判断，导致 NPE

## 修复方案

- 修改文件：
  - `backend/src/main/java/io/github/xxyopen/novel/manager/cache/HomeBookCacheManager.java`
  - `backend/src/main/java/io/github/xxyopen/novel/manager/cache/BookRankCacheManager.java`
  - `backend/src/main/java/io/github/xxyopen/novel/manager/cache/BookInfoCacheManager.java`
  - `backend/src/main/java/io/github/xxyopen/novel/service/impl/UploadServiceImpl.java`
- 修改说明：删除书籍时同时失效首页推荐、三类排行榜、最近更新ID列表缓存；缓存详情方法对 null bookInfo 抛出 `BOOK_NOT_FOUND`；首页组装时过滤孤儿数据

## 验证方式

- 后端验证：`.\mvnw.cmd -DskipTests package` 成功
- 终端验证：`http://127.0.0.1:8888/api/front/home/books` 返回 200
- 前端验证：重新进入 `http://localhost:1024` 首页，删除书籍后刷新首页不再出现该书

## experience.md 更新

- 新增/更新：管理员全站书籍管理条目补充“删除书籍必须同时失效 `homeBookCache`、`bookNewestRankCache`、`bookUpdateRankCache`、`bookVisitRankCache`、`lastUpdateBookIdListCache`”
