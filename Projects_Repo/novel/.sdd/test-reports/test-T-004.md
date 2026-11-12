# 测试报告：T-004 端到端回归验证

**测试时间**：2026-09-15
**Tester Agent ID**：tester (subagent，EB-DeepSeek-V4-Flash)

## 结果：PASS

---

## 测试环境

| 项 | 值 |
|----|----|
| 后端 PID 14548 | `java.exe ... io.github.xxyopen.novel.NovelApplication`（spring-boot:run，`novel-3.5.1-SNAPSHOT.jar` 属 Maven 插件正常形态）监听 8888 |
| 前端 PID 11820 | `node.exe ... vue-cli-service.js serve`（vue.config.js devServer port=1024）监听 1024 |
| MySQL 8 | 127.0.0.1:3306 db=novel，PID 14272 |
| Redis 5 | 127.0.0.1:6379，PID 14136 |
| 前端环境 | `.env.development`：`VUE_APP_BASE_API_URL=http://127.0.0.1:8888/api`、`VUE_APP_BASE_IMG_URL=http://127.0.0.1:8888`（直连，无 proxy），devServer port 1024 |
| DB 基线 | book_info=107，book_chapter=11137，book_content=11137（无历史测试书残留） |

**复用脚本**：`.sdd/tools/epub-smoke-test.py`；**新建脚本**：`.sdd/tools/e2e-smoke-test.py`（HTTP 冒烟）、`.sdd/tools/browser-e2e.py`（Playwright + 系统 Chrome 真实浏览器驱动）。

---

## 验收标准逐条验证

| # | 标准 | 结果 | 证明 |
|---|------|------|------|
| 1 | 上传 txt → 首页推荐或搜索可见 → 分章阅读内容正确 | **PASS** | HTTP 冒烟：上传 `valid-book.txt`（书 `T004端到端txt_09150906`）code=00000，chapterCount=3、wordCount=250；搜索 `GET /api/front/search/books?keyword=T004端到端txt_09150906` total=1 命中；详情/章节/正文 API 全 00000，3 章分别是「第一章 山雨欲来 / 第二章 剑鸣 / 第三章 旧事」，len=91/73/86，html_residual=False |
| 2 | 上传 epub → 可见 → 分章阅读，顺序与 spine 一致、正文纯文本 | **PASS** | 上传 `valid-book.epub`（书 `T004端到端epub_09150906`）code=00000，chapterCount=3、wordCount=148；章节「第一章 初入江湖 / 第二章 客栈奇遇 / 第三章 惊变」len=47/62/39，html_residual=False；DB `book_chapter.chapter_num` 0→1→2 递增与 spine 顺序一致（见 §DB 证据） |
| 3 | 搜索框输入书名关键词命中 | **PASS** | `GET /api/front/search/books?keyword=T004端到端` total=4（本批 4 本测试书全命中）；完整书名列 total=1。浏览器真实操作：`#/bookclass?key=<完整书名>` 页面命中书名与新章节名 |
| 4 | 现有 107 本 seed 回归（首页/搜索/阅读） | **PASS** | `/api/front/home/books` code=00000 31 条推荐；seed 书 `1334318182169681920` 详情/章节列表（49 章）/正文（第1章，len=5109）全 00000；搜索 API 全量 00000；前端 4 页面（首页/上传/搜索/详情/阅读）真实浏览器渲染 seed 数据 |
| 5 | 上传过程加载状态，完成/失败恢复 | **PASS** | 见 §AC5 专项（真实浏览器 + 请求延迟注入验证中间态） |
| TC #1 | 8888 监听 PID 对应本次构建 | **PASS** | netstat PID 14548，`Get-CimInstance` CommandLine = `java.exe -XX:TieredStopAtLevel=1 -cp @...argfile io.github.xxyopen.novel.NovelApplication`；日志 `bugfix-run.log` 为本次 spring-boot:run 完整启动(08:53) |
| TC #2 | 1024 监听 PID 对应本次前端构建 | **PASS** | netstat PID 11820，CommandLine = `node ...@vue/cli-service/bin/vue-cli-service.js serve`；`frontend-e2e.log`「Compiled successfully in 27638ms / App running at http://localhost:1024/」 |
| TC #3 | 前端 VUE_APP_BASE_API_URL 指向 8888 | **PASS** | `novel-front-web/.env.development`：`VUE_APP_BASE_API_URL = 'http://127.0.0.1:8888/api'`；`utils/request.js` 第 8 行 `axios.defaults.baseURL = process.env.VUE_APP_BASE_API_URL`；vue.config.js port=1024 |
| TC #4 | DB 三表数据完整，wordCount/lastChapter* 更新 | **PASS** | 见 §DB 证据（8 本测试书三表对账一致，last_chapter_* 全部更新） |
| TC #5/#6/#7 | 首页/搜索/阅读 API 回归 | **PASS** | `/api/front/home/books`、`/api/front/search/books`、`/api/front/book/{id}`、`/api/front/book/chapter/list?bookId=`、`/api/front/book/content/{chapterId}` 全部 code=00000；阅读链辅助 API（last_chapter/about、pre/next_chapter_id）也 00000 |
| frontendIntegration | mockExitCriteria：所有页面不再展示 Mock 数据；上传→入库→展示→阅读完整链路真实可用 | **PASS** | 真实浏览器逐页渲染确认（见 §浏览器级证据） |

---

## DB 证据（technicalCheck #4）

### book_info（测试书 8 本，全部一致）
```
id 1431630596354977807 T004端到端txt_09150906  word_count=250 last_chapter_id=1445988184596992041 last_chapter_name=第三章 旧事 last_chapter_update_time=2026-09-15 09:06:13
id 1431630596354977808 T004端到端epub_09150906 word_count=148 last_chapter_id=1445988184596992044 last_chapter_name=第三章 惊变 last_chapter_update_time=2026-09-15 09:06:13
pic_url=/img/default-cover.gif  author_id=0  author_name=T004回归测试  category_id=3  category_name=武侠  book_status=0
```
（其余 6 本测试书模式一致：txt 均 word_count=250/最后一章目录；epub 均 148/第三章 惊变。）

### book_chapter ↔ book_content 对账（8 本全为 3 章 3 正文）
| book_id | chapter_num | chapter_name | word_count | content_len |
|---|---|---|---|---|
| ...807 (txt) | 0 | 第一章 山雨欲来 | 91 | 265 |
| ...807 | 1 | 第二章 剑鸣 | 73 | 209 |
| ...807 | 2 | 第三章 旧事 | 86 | 244 |
| ...808 (epub) | 0 | 第一章 初入江湖 | 47 | 135 |
| ...808 | 1 | 第二章 客栈奇遇 | 62 | 178 |
| ...808 | 2 | 第三章 惊变 | 39 | 111 |

- **spine 顺序一致**：book_chapter.chapter_num 0→2 递增，对应 epub OPF spine idref 顺序。
- **纯文本无 HTML 残留**：content 不含 `<p>/<div>/<span>/class=/style=`.（HTTP 层 html_residual=False 双重确认。）
- **wordCount/lastChapter\* 更新**：wordCount=Σ章节字数（91+73+86=250），lastChapterId/Name/UpdateTime 指向最后一章。
- **损坏样本**：`corrupt-nocontainer.epub`/`corrupt-notzip.epub` 上传返回 A0704「图书文件解析失败」，DB 无脏数据（`corrupted_rows=0`）。

---

## ACTUAL 浏览器级证据（真实浏览器驱动，非 HTTP 代替）

工具：Playwright + 系统 Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`，headless）驱动 `http://localhost:1024/#/...`。

### 真实 UI 上传 → 结果 → 恢复（browser-e2e.py）
```
[1] 分类已自动选中: 玄幻奇幻(男频默认)
[2a] 上传前按钮 loading(expect False): False
[4] 上传结果区: 上传成功，共解析 3 章//共解析 3 章 / 250 字/立即阅读
[5] 命中的上传请求: ['http://127.0.0.1:8888/api/front/resource/book/upload']
[6] 上传完成按钮 loading(expect False): False
[6b] 出现「立即阅读」按钮: True
[7] 搜索页(#/bookclass?key=)... 命中书名: True | 出现'第三章 旧事': True
[8] 详情页 url: #/book/<bookId>  ⭐可见于搜索结果点击书名进入
[9] 详情页含 作者/总字数/点击阅读: True
[10] 阅读页 url: #/book/<bookId>/<chapterId>
[11] 阅读页正文渲染(第一章内容/翻页): True   → 山雨欲来/沈砚/下一章/目录
[12] 阅读页「下一章」跳转后含'第二章 剑鸣': True
[13] 页面 JS 错误: None
```

### AC5 加载态专项（请求人为延迟 4s 观察中间态）
- **成功路径**：点击上传后 MID-FLIGHT `is-loading=True`；成功后 `is-loading=False`，结果区「上传成功，共解析 3 章 / 250 字」。
- **失败路径**（corrupt-nocontainer.epub 经真实 UI）：中间态 `is-loading=True`，失败后恢复 `False`，结果区「图书文件解析失败/未写入任何数据，请重试」。**无脏数据（DB corrupted_rows=0）。**
- 代码位点：`BookUpload.vue:71` `:loading="submitting"`；`:180` `state.submitting = true`；`:197-199` `.finally(() => { state.submitting = false })`。

### 静态 DOM 渲染抽查（每个页面均真实渲染后端数据，非 Mock）
| 页面 | 证据 |
|---|---|
| `#/home` | 渲染 seed 推荐书名「我给战神王爷寄刀片」「名侦探修炼手册」等（真实后端数据） |
| `#/book_upload` | 「上传图书」「选择文件」「支持 .txt / .epub 文件，大小不超过 100MB」、`el-upload` 组件 |
| `#/bookclass?key=T004端到端` | 命中「T004端到端...」「第三章 旧事」「第三章 惊变」 |
| `#/book/<id>` | 书名/作者「T004回归测试」「点击阅读」「3章」「最新章节」 |
| `#/book/<id>/<chapterId>` | 章节标题「第一章 山雨欲来」「沈砚」「readBox」「下一章」「目录」 |

**Mock 残留检查**：各页面无 `[Mock]`/Mock 文案；请求命中真实后端 8888。

---

## technicalChecks 汇总（与 AC 叠合的复用上表）

| # | 检查 | 结果 |
|---|------|------|
| TC1 | 8888 PID 14548 对应本次构建 | PASS |
| TC2 | 1024 PID 11820 对应本次构建 | PASS |
| TC3 | VUE_APP_BASE_API_URL=http://127.0.0.1:8888/api | PASS |
| TC4 | DB 三表完整 + wordCount/lastChapter* 更新 | PASS |
| TC5 | 首页 `/api/front/home/books` code=00000 | PASS |
| TC6 | 搜索 `/api/front/search/books` code=00000 | PASS |
| TC7 | 阅读 `/api/front/book/{id}` + `/api/front/book/content/{chapterId}` code=00000 | PASS |

---

## 测试数据清理

- 验证完成后用 **单事务** 清理 8 本测试书（book_content → book_chapter → book_info）：`deleted_content=24`、`deleted_chapter=24`、`deleted_book=8`，已 `COMMIT`。
- 清理后恢复基线：book_info=**107**、book_chapter=11137、book_content=11137；搜索 T004 返回 total=0。
- 上传文件未落盘 `D:/novel-upload`（txt/epub 内存解析），目录仅存先前遗留 `.tmp-reverify.txt`（非本次产物），未触碰。

---

## 遗留问题 / 观察项（不影响当前任务判定）

无阻塞性问题。观察项：
1. **「详情 API 不返回 lastChapterName」**：`GET /api/front/book/{id}` 的 `data` 里 `lastChapterName` 为 null；DB 与 chapter/about API 都有该字段。首页/搜索页显示最新章节名用的是 last_chapter/about 与搜索 DTO，阅读链不受影响——属于详情页字段服务端未填充，与 T-003 报告观察一致的平台既有行为，**不在 T-004 acceptanceCriteria 范围**。
2. **「上传按钮 loading 只对上传请求生效」**：因本地上传耗时极短（3KB），中间态瞬时，手动不易观察；已用请求延迟注入法确认逻辑正确。
3. **书 chap 列表 API 不返回 chapterNum / wordCount**（均为 null），但 chapter/about 与 DB 有值——阅读链正常，观察项。

---

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | `BookContent.vue` 静态模板中仍有旧站残留 JS（`enterNextIndexPage('1334332601092112384')` 硬编码 chapterId、`searchByK('最终马甲')`、`BookDetail.SetBackUpColor` 等引用了 `BookDetail` 全局对象），但 Vue 绑定动态按钮正常、页面无 JS 错误 | 前端 BookContent.vue | 非上传图书功能链路缺陷，建议后续整修任务清理静态残留文案/死代码 |

---

## 验收结论

**PASS**。T-004 五条 acceptanceCriteria 全部通过；7 条 technicalChecks 全部通过；浏览器级真实交互（UI 上传 → 结果展示 → 状态恢复 → 搜索 → 详情 → 阅读 → 下一章）全链路通过，无页面 JS 错误，无 Mock 数据残留。测试数据已清理恢复 107 基线。