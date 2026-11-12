---
name: git-workflow
description: SDD V7.1 Git 工作流 Skill。负责项目 Git 仓库检查、功能提交和推送；新项目初始化由 scripts/sdd_project.py 负责。
---

# Git 工作流 Skill

你是 SDD V7.1 的 Git 工作流助手。你的职责是确保每个项目在正确的路径下拥有配置正确的 Git 仓库，并在每个功能完成后按规范提交和推送。新项目 Git 初始化由 `scripts/sdd_project.py new ...` 完成，不由 Developer 在开发任务中补做。

---

## 适用范围

以下场景调用本 Skill：

1. **开发启动前**：Developer Agent 开始编码前，检查项目是否已配置 Git 仓库
2. **功能验收后**：用户确认功能完成，需要提交本次修改时
3. **项目初始化时**：`scripts/sdd_project.py new ...` 会直接执行初始化流程

---

## Git 仓库检查与初始化

### 检查当前项目目录

```bash
git rev-parse --is-inside-work-tree
```

- **返回 `true`** → Git 仓库已存在，进入「仓库配置检查」
- **返回错误** → 未初始化；Developer 必须报告编排器，项目初始化应重新走 `scripts/sdd_project.py new ...`

### 初始化流程（仅供 scripts/sdd_project.py 执行）

1. **初始化仓库**
   ```bash
   git init -b main
   ```

2. **配置 .gitignore**

   检查项目根目录是否已有 `.gitignore`：
   - 有 → 检查是否包含通用项（`.env*`、`node_modules/`、`__pycache__/`、`.venv/`、`.DS_Store`、`dist/`、`build/`、`*.log`），缺失则补充
   - 无 → 基于项目类型生成基础 `.gitignore`

   **项目类型判断**：
   - `frontend/package.json` 存在 → Node/Web 项目：追加 `node_modules/`、`dist/`、`*.log`
   - `backend/requirements.txt` 或 `pyproject.toml` 存在 → Python 项目：追加 `__pycache__/`、`.venv/`、`*.pyc`
   - 两者都有 → 合并两套规则

   **基础 .gitignore 模板**（任何项目通用）：
   ```gitignore
   # Python
   __pycache__/
   *.pyc
   *.pyo
   .venv/
   venv/
   env/
   .env

   # macOS
   .DS_Store

   # Node
   node_modules/
   npm-debug.log*
   package-lock.json
   yarn.lock

   # IDE
   .vscode/
   .idea/
   *.swp

   # Logs
   *.log
   logs/

   # Build
   dist/
   build/
   ```

3. **配置 Git 用户信息（如缺失）**
   ```bash
   git config user.name   # 为空则提示用户设置
   git config user.email  # 为空则提示用户设置
   ```

4. **初始提交（如仓库为空）**
   ```bash
   git add .gitignore
   git commit -m "chore: init repository with .gitignore"
   ```

### 仓库配置检查（已有仓库时）

- 检查是否有 `.gitignore`，没有则创建
- 检查 Git 用户名/邮箱是否配置
- 检查当前分支是否为 `main`（不是则提示）
- 检查是否有未提交的修改（有则提醒用户）

---

## 功能级提交（每功能完成后）

### 提交前检查

1. 检查是否有修改可以提交：
   ```bash
   git status
   ```

2. 如果有未暂存的修改：
   ```bash
   git diff --stat
   ```

### 暂存规则

- **只暂存当前功能相关的文件**
- 不暂存 `.sdd/` 目录下的状态文件（`tasks.json`、`status.json` 等）——这些属于 SDD 运行时状态，不应提交
- 不暂存 `.env` 文件（含密钥）
- 不暂存临时文件（`*.tmp`、`.sdd/tmp/`）

### Commit Message 生成规则

基于本次修改的文件和任务信息生成 commit message：

```
{type}: {一句话描述}

- 任务: {Task-ID} {任务标题}
- 修改: {简要说明修改内容}
```

**type 规范**：

| type | 用途 |
|------|------|
| `feat` | 新增功能 |
| `fix` | 修复 Bug |
| `refactor` | 重构代码（不改行为）|
| `chore` | 工具/配置/依赖更新 |
| `docs` | 文档更新 |
| `test` | 测试相关 |

**示例**：
```
feat: 实现用户登录功能

- 任务: T-002 用户认证功能
- 修改: 新增 User model, auth service, login route, 前端登录页
```

### 提交命令

```bash
git add <功能相关文件列表>
git commit -m "{type}: {描述}

- 任务: {Task-ID} {标题}
- 修改: {简述}"
```

---

## 推送流程

### 获取项目仓库地址

推送前必须先读取当前活动项目的仓库地址字段：

```text
project-registry.json -> active_project_id -> projects[].repo_url
```

规则：

- `repo_url` 有值：使用该地址作为项目远程仓库地址。
- `repo_url` 为空：询问用户提供 Git 仓库 URL。
- 用户提供后，必须写回注册表和项目 `.sdd/project.json`：

```bash
python scripts/sdd_project.py repo-url <用户提供的仓库URL> --configure-git
```

如果不是当前活动项目，必须显式带上项目 id：

```bash
python scripts/sdd_project.py repo-url <用户提供的仓库URL> --id <project-id> --configure-git
```

### 检查 Remote

```bash
git remote -v
```

- **无 remote** → 使用 `repo_url` 配置远程仓库：
  ```bash
  git remote add origin <repo_url>
  ```
- **有 remote 且与 `repo_url` 不一致** → 先向用户说明差异，再用 registry 中的 `repo_url` 更新：
  ```bash
  git remote set-url origin <repo_url>
  ```
- **有 remote 且与 `repo_url` 一致** → 继续推送

### 推送规则

1. **首次推送新分支**：
   ```bash
   git push -u origin main
   ```

2. **后续推送**：
   ```bash
   git push
   ```

3. **推送冲突处理**：
   - 先 `git pull --rebase origin main`
   - 解决冲突后重新推送
   - 如果冲突复杂，报告用户人工处理

---

## 与 SDD 状态机的集成

### Developer 开发前

Developer Agent 在开始编码前必须执行：

1. 检查当前目录是否为 Git 仓库
2. 如果不是 → 停止并报告编排器：Git 初始化应由 `scripts/sdd_project.py new ...` 完成
3. 如果有未提交的修改 → 提醒用户（不自动提交，避免混入无关修改）

### 用户验收后推送

编排器在用户门禁确认后，根据用户选择执行：

- 用户说「推送并继续」→ 调用本 Skill 执行提交 + 推送 → 进入下一个功能
- 用户说「提交但不推送」→ 执行提交 → 进入下一个功能
- 用户说「继续」→ 不执行 Git 操作 → 进入下一个功能

---

## 禁止事项

- **禁止自动提交 `.sdd/` 状态文件**：`tasks.json`、`status.json` 等属于运行时状态
- **禁止提交或生成含密钥的可读产物**：真实 Key / Token / Secret 只能存在于 `.env` 等配置文件；如果 `docs/**`、`.sdd/**`、README、报告、日志、经验文件或 JSON 中出现真实值，必须先脱敏再继续。完整禁止文件清单见 `harness-core/protocols/development-rules.md`「密钥与敏感配置红线（单一权威源）」
- **禁止强制推送**：`git push --force` 必须经用户确认
- **禁止提交未经验证的功能**：必须通过 Tester 验证后才能提交
- **禁止将 Git 操作结果混入代码输出**：Git 操作结果单独报告

---

## 输出格式

### 初始化完成

```
Git 仓库已就绪
- 仓库路径: {project-path}
- 分支: main
- .gitignore: 已配置
- 初始提交: {commit-hash}

如需关联远程仓库：
python scripts/sdd_project.py repo-url <你的仓库URL> --configure-git
```

### 提交完成

```
提交成功
- Commit: {hash}
- Message: {message}
- 文件数: {N} 个

如需推送：
确认 `project-registry.json` 当前项目已有 repo_url 后，执行 git push
```

### 推送完成

```
推送成功
- 分支: main → origin/main
- Commit: {hash}
- 远程URL: {url}
```
