# SDD V7.1 Student Framework

这是从 `SDD_V7` 继续优化出的学生版框架，重点补齐 Codex 适配层。

## 已清理内容

- 已移除示例业务项目 `Projects_Repo/customer_service/`
- 已重置 `project-registry.json`，当前没有 active project
- 已移除 `.env`、`.env.*`、数据库、缓存、虚拟环境、构建产物和本机 MCP 配置
- 已保留 `harness-core/`、`.cursor/`、`.claude/`、`.codex/`、`.workbuddy/`、`.codebuddy/`、`pycore/`、`templates/`、`scripts/`
- 已补齐 `.codex/commands/`、`.codex/README.md` 和 `harness-core/protocols/codex-subagents.md`
- 已补齐 `.workbuddy/README.md`、`.workbuddy/skills/sdd-harness/SKILL.md` 和 `harness-core/protocols/workbuddy-subagents.md`（WorkBuddy 第四端适配）
- 已补齐 `.codebuddy/commands/sdd-bugfix.md`（WorkBuddy 项目级命令目录名为 `.codebuddy`，非 `.workbuddy`）

## WorkBuddy 使用前必做的同步

WorkBuddy 只从用户级目录发现技能与子智能体，项目内配置不会自动加载。首次使用或拉取更新后需执行：

```bash
python scripts/install_workbuddy_agents.py   # 同步 planner / developer / tester
python scripts/install_workbuddy_skill.py    # 同步 sdd-harness 入口 Skill
```

两者都支持 `--check`（只校验）与 `--remove`（卸载），并且都是幂等的。校验是否已同步：

```bash
python scripts/install_workbuddy_agents.py --check
python scripts/install_workbuddy_skill.py --check
python scripts/check_workbuddy_adapter.py      # 逐层确认是否真正生效
python scripts/check_harness_consistency.py
```

> **生效时机按链路区分**：子智能体装完**即时生效**；入口 Skill 与斜杠命令需**新开会话**；`AGENTS.md` 内容在会话启动时快照。不要一律以"重开会话"判断故障。

## 学生使用方式

### 方式一：创建新项目

```bash
python3 scripts/sdd_project.py new <project-id> --name "<项目名>" --type web
```

示例：

```bash
python3 scripts/sdd_project.py new customer-service --name "智能客服系统" --type web
```

### 方式二：查看当前项目

```bash
python3 scripts/sdd_project.py current
```

### 方式三：切换项目

```bash
python3 scripts/sdd_project.py list
python3 scripts/sdd_project.py use <project-id>
```

## 安全规则

真实 API Key、Token、Secret、密码只能写入 `.env` / `.env.local` / 用户指定 secret 配置文件；不得写入 `docs/**`、`.sdd/**`、报告、日志、README、JSON 或任何 Markdown 可读产物。
