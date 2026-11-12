# SDD V7.1 WorkBuddy Adapter

本目录是 WorkBuddy 适配层，只做入口和子智能体编排协议引用，不维护核心规则。

## 入口

- 根入口：`AGENTS.md`（平台中立入口，WorkBuddy 会作为项目级指令自动注入）
- WorkBuddy 原生 Skill 入口：`.workbuddy/skills/sdd-harness/SKILL.md`（**需同步到用户级才生效**）
- 子智能体配置：`.workbuddy/agents/{planner,developer,tester}.md`（需同步到用户级生效）
- 子智能体协议：`harness-core/protocols/workbuddy-subagents.md`
- 手动命令：`.codebuddy/commands/sdd-bugfix.md`（WorkBuddy 的项目级命令目录名是 `.codebuddy`）

## 为什么 Skill 也要装到用户级

WorkBuddy 的技能发现根**只有以下四个**，全部位于用户配置目录或内置插件目录，**不含当前工作区**：

```text
<configDir>                        # ~/.workbuddy
<configDir>/skills
<builtin plugins>/skills
<configDir>/skills-marketplace
```

实测证据：`.skill-list-cache.json` 的 `scopeKey` 完整列出上述四个根，其中没有任何工作区路径；`sdd-harness` 在 `.skill-list-cache.json` 与 `logs/main.log` 中出现次数均为 0，尽管 `.workbuddy/skills/sdd-harness/SKILL.md` 一直在磁盘上。

所以只把 Skill 放在仓库内的 `.workbuddy/skills/` 下，**永远不会被注册**。采用与子智能体相同的双路径：

```text
仓库内（版本化源）  .workbuddy/skills/sdd-harness/SKILL.md
        │  python scripts/install_workbuddy_skill.py
        ▼
用户级（运行时生效） ~/.workbuddy/skills/sdd-harness/SKILL.md
```

```bash
python scripts/install_workbuddy_skill.py          # 安装 / 更新
python scripts/install_workbuddy_skill.py --check  # 只校验，不写入
python scripts/install_workbuddy_skill.py --remove # 卸载
```

### 全局可见性守卫

用户级 Skill 在**所有工作区**都可见。为防止它误接管普通项目，`SKILL.md` 的「阶段 0：工作区校验」要求先确认当前目录存在 `harness-core/router.md` 与 `AGENTS.md`，任一缺失即静默退出。

这条守卫是硬约束：`install_workbuddy_skill.py` 拒绝安装缺少守卫的副本，`scripts/check_harness_consistency.py` 也会对源文件做同样校验。

## 使用方式

在 WorkBuddy 中打开 Harness 根目录后：

1. `AGENTS.md` 被自动注入，指向唯一入口 `harness-core/router.md`
2. 用户说出新建项目、需求对齐、开始开发、已有项目修整、导入已有项目、删除项目时，由 `harness-core/router.md` 根据自然语言意图分发
3. 需要显式唤起时，用户可直接要求"用 sdd-harness"或提到 SDD 相关关键词，触发已生成到用户级的 `sdd-harness` Skill
4. 只有用户明确要求修 Bug 时，才使用 `/sdd-bugfix` 或读取 `harness-core/commands/sdd-bugfix.md`

## 生效时机：三条链路各不相同

适配层的改动**不是**统一“改完重开会话就好”，三条链路的行为实测下来并不一样：

| 链路 | 仓库位置 | 运行时位置 | 生效方式 |
|------|----------|------------|----------|
| 根入口 `AGENTS.md` | `AGENTS.md` | 工作区根，直接读 | **会话启动时快照**，改后需新会话 |
| 子智能体 | `.workbuddy/agents/*.md` | `~/.workbuddy/agents/` | **即时生效**，装好即可调度 |
| 入口 Skill | `.workbuddy/skills/sdd-harness/SKILL.md` | `~/.workbuddy/skills/sdd-harness/` | **新会话 / 手动刷新** |
| 斜杠命令 | `.codebuddy/commands/*.md` | 工作区根，直接读 | 新会话 |

实测依据：

- **子智能体即时生效**：新建一个全新名字的探针子智能体，不加任何重启动作，当前会话立刻就能调度成功（`PROBE_LIVE=YES`）。同理，临时移走 `planner.md` 后仍能调度，是因为该角色已在会话启动时载入内存。
- **Skill 不热加载**：修改用户级 `SKILL.md` 的 description 并逐秒轮询技能缓存，20 秒内缓存无变化。但缓存确实会在会话中途被重写（`savedAt` 与安装时间不同步即为证据），触发点是客户端的技能刷新动作，不是文件变更本身。
- **`AGENTS.md` 内容快照**：文件被正常加载（日志有 file-watch `ready` 事件），但注入内容停留在会话启动那一刻。

因此：**改子智能体 → 装完即可用；改 Skill 或命令 → 需新会话。**

## 一条命令确认全部链路

与其逐个猜测，直接跑自查脚本：

```bash
python scripts/check_workbuddy_adapter.py          # 人读报告
python scripts/check_workbuddy_adapter.py --quiet  # 只看退出码，适合 CI
python scripts/check_workbuddy_adapter.py --json   # 机读
```

它逐层报告 `AGENTS.md`、子智能体（含仓库与用户级 MD5 一致性）、入口 Skill（含是否已进入技能列表）、斜杠命令（含误建 `.workbuddy/commands` 检测）和角色模型有效性，并在失败时给出该等新会话还是该重装。

退出码：`0` 全部生效，`1` 有环节需要处理。

> 角色模型名必须存在于 `~/.workbuddy/models.json`，否则运行时会静默回退。目前四个可用模型为 `EB-GLM-Pro`、`EB-DeepSeek-Flash`、`EB-DeepSeek-Pro`、`EB-GLM-Flash`，三个角色所用的三个模型均在其中。

## 命令适配：`.codebuddy/commands/`

WorkBuddy 的**项目级**斜杠命令目录在客户端内被硬编码为 `.codebuddy/commands`（历史遗留名，已实测确认），**不是** `.workbuddy/commands`。这一点很容易搞错，因此一致性检查会主动拦截误建的 `.workbuddy/commands/`。

沿用 SDD 的「只保留一个手动命令适配」原则，WorkBuddy 端只有一个命令：

```text
.codebuddy/commands/sdd-bugfix.md
```

其余入口全部由 Router 自然语言分发：

```text
新建项目、需求对齐、开始开发、已有项目修整、导入已有项目、删除项目
  -> 全部由 harness-core/router.md 自然语言分发
```

**为什么用项目级而不是用户级**：用户级命令目录 `<configDir>/commands` 会让 `/sdd-bugfix` 出现在**所有**无关项目的斜杠菜单里。项目级只在本仓库可见，更干净。

该命令文件同样是薄适配器：只做工作区校验、指向 `harness-core/commands/sdd-bugfix.md` 与对应 Skill、声明约束，不复制修复流程正文。

## 子智能体

WorkBuddy 支持静态子智能体声明，但**只从用户级配置目录发现**，不加载项目内的 `.workbuddy/agents/`（已实测确认）。因此采用双路径：

```text
仓库内（版本化源）  .workbuddy/agents/{planner,developer,tester}.md
        │  python scripts/install_workbuddy_agents.py
        ▼
用户级（运行时生效） ~/.workbuddy/agents/{planner,developer,tester}.md
```

安装与校验：

```bash
python scripts/install_workbuddy_agents.py          # 安装 / 更新
python scripts/install_workbuddy_agents.py --check  # 只校验，不写入
python scripts/install_workbuddy_agents.py --remove # 卸载
```

三个角色按 `harness-core/protocols/workbuddy-subagents.md` 编排：

- `planner` → `harness-core/agents/planner.md`（默认模型 `EB-DeepSeek-Flash`）
- `developer` → `harness-core/agents/developer.md`（默认模型 `EB-DeepSeek-Pro`）
- `tester` → `harness-core/agents/tester.md`（默认模型 `EB-GLM-Pro`）

角色配置文件只声明 `name` / `description` / `model` / `category` / `version` / `tags` 与指向 `harness-core/agents/*.md` 的引用，不复制核心规则。模型须存在于 `~/.workbuddy/models.json`。

## 记忆边界

WorkBuddy 的 `.workbuddy/memory/`（工作日志、长期备忘）与 SDD 的两级经验体系是**两套独立机制**，不得互相替代：

| 体系 | 路径 | 用途 |
|------|------|------|
| WorkBuddy 记忆 | `.workbuddy/memory/YYYY-MM-DD.md`、`.workbuddy/memory/MEMORY.md` | 宿主平台会话记忆 |
| SDD 项目经验 | `Projects_Repo/<id>/.sdd/experience.md` | 项目级踩坑与避坑规则 |
| SDD 系统经验 | `memory/harness-experience.md` | 跨项目可复用的 Harness 本体教训 |

## 核心规则只维护在

```text
harness-core/
```

`.workbuddy/` 内不得出现路由、Agent 规则、开发规范、Skill 流程的副本。
