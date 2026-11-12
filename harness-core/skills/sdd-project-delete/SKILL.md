---
name: sdd-project-delete
description: SDD 删除项目流程。明确删除意图、展示删除范围、检查 Git 与未提交改动、要求明确确认后，调用 scripts/sdd_project.py delete 删除项目目录并更新注册表（含 active 指针清理）。
---

# SDD 删除项目 Skill V7.1

## 目标

当用户要删除一个已有 SDD 项目时，使用本 Skill。

删除是破坏性操作。这个分支必须明确、可确认、范围清晰。

## 何时使用

只有明确删除项目意图时，才进入此分支：

- “删除项目”
- “删掉这个项目”
- “这个项目不要了”
- “移除这个项目”
- “清理 Projects_Repo 里的某个项目”

不要把以下情况路由到删除项目：

- 删除单个文件
- 移除一个功能
- 重置一个页面
- 清理生成产物

这些都属于已有项目修整。

## 必要步骤

### 1. 确认目标项目

从以下信息定位目标：

1. 用户给出的明确路径
2. 用户给出的项目名
3. `project-registry.json`
4. `Projects_Repo/`

如果目标不清楚，询问项目名或路径。

### 2. 展示删除范围

删除前必须展示：

```text
将删除项目：
项目名：
项目路径：
Registry 记录：
是否为当前 active 项目：是 / 否
Git 状态：
远程仓库：仅本地删除，不会动远程仓库
```

如果目标项目是当前 `active_project_id`，必须提示用户：删除后活动项目会被清空，需要重新 `use` 选择其他项目。

### 3. 检查 Git 状态

如果项目目录有 Git：

1. 运行 `git status --short`
2. 汇报未提交改动
3. 如果存在未提交改动，必须让用户看到后再次明确确认，才能删除

如果项目目录没有 Git，直接说明。

### 4. 要求明确确认

删除前必须要求用户输入明确确认句：

```text
确认删除 <project-name>
```

不能把“可以”“继续”这类模糊表达当作删除确认。

### 5. 删除并更新注册表

用户明确确认后，统一通过脚本删除，不手动 `rm -rf` 或手改 registry（脚本会原子地移除目录、移除注册记录、并在必要时清空 active 指针）：

```text
python scripts/sdd_project.py delete <project_id> --yes
```

如果只想从注册表移除、保留磁盘文件（例如先备份）：

```text
python scripts/sdd_project.py delete <project_id> --yes --keep-files
```

脚本会自动完成：

1. 删除 `Projects_Repo/<project>`（`--keep-files` 时跳过）
2. 从 `project-registry.json` 移除该项目记录，保留其它无关记录
3. 如果被删项目是当前 `active_project_id`，将其清空为 `null`
4. 拒绝删除 `Projects_Repo/` 之外的路径

删除后汇报：已删除路径、registry 更新结果、active 指针状态（是否被清空）。如果 active 被清空，提示用户后续需 `python scripts/sdd_project.py use <id>` 重新选择活动项目。`<project_id>` 的 `--yes` 由 Agent 在第 4 步获得用户明确确认后再传入，脚本本身不替代用户确认。

## 约束

- 不能从模糊意图触发删除。
- 除非用户逐一列出目标，否则不能删除多个项目。
- 不能删除 `Projects_Repo/`、`harness-core/`、`.codex/`、`.cursor/`、`.claude/` 等父级目录。
- 不能使用宽泛破坏性清理命令。
- 不能移除无关 registry 记录。
