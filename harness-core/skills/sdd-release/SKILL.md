---
name: sdd-release
description: SDD V7.1 发布交付 Skill。用于项目功能开发完成、需要交给用户实际使用时的交付收口，产出发布前检查单、startup.md 定稿、最终用户验收走查清单、Git tag 与 release note、回滚方案。不替代 git-workflow 的提交规范，只在其上补齐 tag / release / 回滚与交付门槛。
---

# SDD 发布交付 Skill V7.1

你是 SDD V7.1 的发布交付负责者。开发通过验收，不等于可以交付：**验收证明"功能对了"，交付要证明"别人能把它跑起来、出了问题能退回去"**。

本 Skill 补的是流程最后一段的空白——原本 `development-rules.md` 只有一句「全部功能自动验证通过后，输出 `docs/startup.md`」。

---

## 定位与边界

| 对象 | 负责什么 | 边界 |
| ---- | -------- | ---- |
| Tester | 功能是否符合 `acceptanceCriteria` | 不管部署与交付 |
| Code Review | 写法是否守规范契约 | 不管部署与交付 |
| **sdd-release（本 Skill）** | 能否交付、怎么交付、如何回滚 | 不改功能代码、不重跑验收 |
| `git-workflow` | 仓库检查、功能级提交、推送 | 止于 `push`；tag / release 由本 Skill 负责 |

本 Skill **不做**：

1. 不修改业务功能代码（发现功能问题 → 转 `sdd-bugfix`）。
2. 不重跑 Tester 的 `acceptanceCriteria`。
3. 不重写 `git-workflow` 的提交规范、`.gitignore` 模板、`repo_url` 读取逻辑——这些全部引用既有定义。
4. 不擅自执行部署（部署属"需要用户确认"的动作，本 Skill 产出方案与指令，执行前必须确认）。

核心原则：**Reproducible or it did not happen.** 交付物的判断标准不是"我这儿能跑"，而是"换一个人、换一台机器、按文档照做能跑起来"。

---

## 触发时机

### 必须执行

1. **用户表达交付意图**：「发布 / 上线 / 部署 / 打包 / 交付 / 给客户 / 交付给团队 / 交付验收」。
2. **项目进入交付状态**：`.sdd/tasks.json` 中所有 `user_gate=true` 的任务均为 `passed`，且 `Code Review` 无未关闭 Blocker，用户确认要交付。
3. **里程碑交付**：阶段性版本（V1、MVP）要交给用户实际使用，即使后续还有迭代。

### 不执行

- 开发过程中的功能验收（那走 Tester + 用户门禁）。
- 只是本地看效果、还没到交付节点时。
- 项目处于重构中途（`sdd-refactor` 未收口时不得发布——行为等价性未验证完）。

---

## 输入

开始前必须具备：

1. `.sdd/tasks.json`：全量任务状态（用于判断是否齐备、生成 release note）。
2. `.sdd/test-reports/**`：最新一轮验收结论。
3. `.sdd/reviews/**`：代码审查结论，确认无未关闭 Blocker。
4. `docs/startup.md`：已存在的启动说明（可能不完整，需定稿）。
5. `docs/Plan.md`：「外部服务与测试权限清单」一节。
6. `.env.example` 或等价配置模板。
7. `project-registry.json` 中该项目的 `repo_url`。
8. `.sdd/work-log.md`：已知问题、超出范围发现、技术债登记。

缺 1 或 3 时不得开始：不知道任务是否齐备、不知道有没有未关闭的 Blocker，发布结论不可信。

---

## 交付五步

### Step 1：发布前检查单（门禁）

逐项核对，任何一项不通过即**不得发布**：

| # | 检查项 | 通过标准 | 不通过怎么办 |
| - | ------ | -------- | ------------ |
| 1 | 任务齐备 | `user_gate=true` 的任务全部 `passed`，无 `blocked` / `fixing` | 转对应流程补齐 |
| 2 | 审查清零 | `.sdd/reviews/` 中 Blocker 全部关闭 | 转 Developer 修 |
| 3 | 真实联调 | `frontendIntegration.required=true` 的任务已完成真实后端联调 | 补齐联调或转 BLOCKED 并告知用户 |
| 4 | 密钥未入库 | 按 `harness-core/protocols/development-rules.md`「密钥与敏感配置红线」全量清单扫描，无真实值 | 脱敏 + 提示用户轮换 |
| 5 | `.gitignore` 覆盖 | 至少覆盖 `.env*`、`node_modules/`、`__pycache__/`、`dist/`、`*.log` | 补齐后重新提交 |
| 6 | 构建可复现 | 干净环境执行构建命令成功，产物路径明确 | 修构建问题 |
| 7 | 外部服务状态明确 | 每个外部依赖处于「已配置 / Mock 降级 / 未接入」之一，且已告知用户 | 补齐状态说明 |
| 8 | 无临时残留 | 无 `*.patch` / `*.bak` / `*.orig` / `[Mock]` 文本 / 未清理的 `.sdd/tmp/` | 清理或登记为已知问题 |
| 9 | 已知限制已记录 | 未实现功能、已知缺陷、环境要求写进 `startup.md`「已知限制」 | 补写 |

检查单落盘：

```text
.sdd/release/release-checklist-YYYYMMDD.md
```

**第 8 项与第 4 项可用脚本自动检查**：`scripts/check_project_state.py` 覆盖编码合规、残留检测、`.env` 误提交等机械项。先跑脚本，再做人工判断项，避免把机械检查也做成"凭印象"。

### Step 2：`docs/startup.md` 定稿

必备六节，缺任一节视为未定稿：

```markdown
# 启动说明

## 1. 环境要求
- 运行时版本（Node / Python 具体版本，注明验证过的版本）
- 是否需要数据库、是否需要外部服务
- 操作系统限制（如有）

## 2. 安装
- 从零开始的完整命令，含目录切换
- 常见安装失败与处理（网络慢、权限、代理）

## 3. 启动
- 本地开发启动命令与端口
- 生产/构建启动方式
- 如何停止

## 4. 默认配置
- 关键环境变量字段名（**只写字段名与用途，不写真实值**）
- 默认行为（如 Mock 开关默认值）
- 配置文件位置

## 5. 端口约定
- 引用 `harness-core/protocols/development-rules.md`「端口约定」，不另抄一份

## 6. 已知限制
- 未实现的功能
- 已知缺陷与影响范围
- 环境依赖的降级说明（如外部服务未接入时的表现）
```

写作要求：

- 面向**没看过这个项目的人**。所有命令可直接复制执行，不需要"你应该知道"的前置知识。
- 每条命令注明**在哪个目录执行**——这是最高频的踩坑点。
- 端口数值引用权威表，不另写一份（防止端口调整后 `startup.md` 与现实不符）。

### Step 3：最终用户验收走查清单（原 F9 归属）

产物：

```text
docs/manual-checklist.md
```

定位：**给最终用户逐项点选的操作清单**，与 `startup.md` 互补——`startup.md` 教怎么启动，走查清单验证启动后功能是否真的可用。

结构要求：

```markdown
# 最终用户验收走查清单

> 使用浏览器打开 http://<前端地址> 后逐项勾选。建议按顺序执行。

## 启动与页面
- [ ] 页面正常打开，能看到 <产品名/主标题>
- [ ] 首页无报错弹窗、空白页、明显排版错乱
- [ ] 无 `[Mock]`、调试文字、临时占位提示残留

## <按功能模块分组>
- [ ] <可观察的操作步骤>
- [ ] <可观察的预期结果>

## 数据持久化（如适用）
- [ ] 刷新后数据仍在

## 已知限制
- <明确写出「以下行为是已知限制，不是缺陷」>
```

写作要求：

- 每条都是**用户能自己判断真假**的观察项，不写「接口返回 200」这类内部标准。
- 覆盖主流程 + 关键边界（空数据、错误输入、空状态）。
- 已知限制单独成节，避免用户把预期行为当缺陷报上来。
- 依据 `docs/PRD.md` 的功能清单与 `docs/Plan.md` 的页面清单生成，不凭印象补。

> 这一产物此前是自发行为（`creator-topic-library` 产出了但无归属）。现在正式归属本 Skill，交付时必须产出。

### Step 4：Git tag 与 release note

前置：`git-workflow` 的提交与推送已完成（本 Skill 不重复其规范）。

```bash
# tag 命名与 version 对齐，如 v1.0.0 / v0.3.0
git tag -a v<version> -m "<一句话版本说明>"
git push origin v<version>
```

release note 落盘：

```text
.sdd/release/release-note-v<version>.md
```

结构：

```markdown
# v<version> 发布说明

## 交付内容
- <按 tasks.json 中 passed 的任务归并成功能条目，不逐条罗列任务 ID>

## 相对上一版本的变化
- 新增：
- 调整：
- 修复：

## 已知限制
- <与 startup.md 一致>

## 验收依据
- Tester 报告：`.sdd/test-reports/`（最新一轮日期）
- 代码审查：`.sdd/reviews/`（Blocker 已清零）
- 用户走查：`docs/manual-checklist.md`
```

要求：

- 按**功能**归并，不按任务 ID 罗列——用户关心能做什么，不关心内部拆了几个任务。
- 「已知限制」必须与 `startup.md` 保持一致，两处口径不同会让用户不知道该信哪个。

### Step 5：回滚方案

产物写入 release note 的「回滚方案」一节：

```markdown
## 回滚方案

### 版本回退
- 代码回退：`git checkout <上一个 tag>` / `git revert <commit>`
- 依赖回退：<是否需要重装依赖、恢复到哪个 lock 文件>
- 构建产物：<是否保留上一版本 dist，路径在哪>

### 数据回滚边界
- 本版本是否包含数据结构变更：是 / 否
- 如有：变更内容、是否可逆、不可逆时的处理方式
- 数据备份位置与恢复命令

### 回滚验证
- 回退后如何确认已回到正常状态（具体命令或页面检查项）
```

**数据回滚是最高风险项**：代码可以 `revert`，数据变更往往不可逆。若本版本包含数据结构变更，必须写明备份方式；未做备份的破坏性变更不得发布。

---

## 部署执行规则

本 Skill 产出部署方案与指令，**但不擅自执行**。原因：`development-rules.md` 已将「部署发布」列入必须用户确认的动作。

正确链路：

```text
本 Skill 产出部署指令与回滚方案
  -> 向用户说明将执行什么、影响范围、回滚方式
  -> 用户确认
  -> 执行
  -> 执行后验证（按回滚方案中的「回滚验证」同样方式正向验证）
```

若用户选择自己部署，交付物是：`startup.md` + 部署指令清单 + 回滚方案。不要求用户回传执行结果，但要在交付说明中写明「部署由用户执行，部署后的生产环境验证未由 Agent 完成」。

---

## 与既有 Skill 的协作关系

| 对象 | 关系 |
| ---- | ---- |
| `git-workflow` | 上游。复用其提交规范、`.gitignore` 模板、`repo_url` 读取；本 Skill 只加 tag / release note / 回滚 |
| `sdd-code-review` | 前置。Blocker 未清零不得发布 |
| `sdd-experience-governance` | 前置。交付前应已治理经验（触发条件之一就是"交付前复盘"） |
| `sdd-bugfix` | 下游。用户走查清单发现的问题转其处理，修完需重新走 Step 1 的相关检查项 |
| `sdd-refactor` | 互斥。重构未收口（行为等价性未验证）不得发布 |
| `sdd-product-design` | 上游。消费其「外部服务与测试权限清单」（`docs/Plan.md`） |
| `scripts/check_project_state.py` | 工具。Step 1 的机械检查项由该脚本先行 |

---

## 完成输出

```markdown
发布交付完成。

版本：v<version>
发布前检查单：9/9 通过（或列出未通过项）
任务状态：<passed 数>/<总数>

交付物：
- docs/startup.md（六节齐备）
- docs/manual-checklist.md（<n> 项走查）
- .sdd/release/release-note-v<version>.md
- Git tag：v<version>（已推送 / 待用户确认）

已知限制：<n> 项
回滚方案：已写入 release note（含数据回滚边界）

待用户确认：<需确认的部署动作，如有>
```

---

## 禁止

- 禁止在发布前检查单有未通过项时宣布"可以交付"
- 禁止在 `.sdd/reviews/` 存在未关闭 Blocker 时发布
- 禁止擅自执行部署（必须先说明并获得用户确认）
- 禁止在 `startup.md` 或任何交付物中写入真实密钥（引用「密钥与敏感配置红线」）
- 禁止用"我这台机器能跑"替代干净环境的构建验证
- 禁止 `startup.md` 与 release note 的「已知限制」口径不一致
- 禁止把任务 ID 罗列当 release note（用户关心的是功能）
- 禁止在包含不可逆数据结构变更时跳过数据备份说明
- 禁止替代 Tester 重跑验收，或在功能有问题时代码层"顺手修一下"
