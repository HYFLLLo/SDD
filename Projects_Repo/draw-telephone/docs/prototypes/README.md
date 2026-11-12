# 画意接龙 · 原型设计交接说明

> 原型工具：Pencil MCP（.pen 文件）
> 设计方向：手账涂鸦本（温暖手作）
> 原型文件：`draw-telephone.pen`
> HTML 备份：`01-plaza.html` ~ `04-room.html`（Junior Pass + 前 4 页 HTML 版本，Pencil 接入前的产物）

## 页面清单（9 个 MVP 界面）

| Frame | 页面 | 类型 | 尺寸 | 坐标 |
|-------|------|------|------|------|
| P01-广场 | 首页/广场 | 列表页 | 1440×900 | (0,0) |
| P02-创建链 | 创建链页 | 表单页 | 1440×900 | (1680,0) |
| P03-加入链 | 加入链页 | 表单页 | 1440×900 | (3360,0) |
| P04-链大厅 | 链大厅（房间页）★签名锚点 | 仪表盘 | 1440×752 | (0,1140) |
| P05-接力作画 | 接力作画/描述页 | 创作页 | 1440×786 | (1680,1140) |
| P06-作品详情 | 作品详情页（只读） | 详情页 | 1440×1175 | (3360,1140) |
| P07-整链回放 | 整链回放页（含投票） | 详情页 | 1440×612 | (0,1900) |
| P08-个人主页 | 个人主页 | 列表页 | 1440×680 | (1680,1900) |
| P09-登录注册 | 登录/注册页 | 表单页 | 1440×900 | (3360,1900) |

> 网格排列：每行 3 个，水平间距 240，垂直间距 240。P04/P05/P06/P07/P08 高度按内容自适应。

## 关键组件清单

- **顶部导航**：Logo（文字+圆点 mark）+ 导航（广场/我的）+ 通知铃铛 + 头像
- **作品卡片**：手绘虚线边框 + 缩略图 + 标题 + meta（节点数/人数）
- **进度节点链**（★签名锚点）：6 节点 + 5 连线，已完成=实心陶土橙，当前=空心陶土橙，待接=空心虚线灰
- **画布**：偏直角(4px)，米白底，工具栏（笔/色板/粗细/橡皮/撤销）
- **AI 续标注**：冷灰蓝小标签"AI 续"，与人画署名区隔
- **投票维度卡**：三维度（最跑偏/最佳画/最佳描述），单选选项
- **表单**：圆角输入框 + 分段切换（seg）+ 陶土橙主按钮

## 交互状态

- 按钮：默认 / hover（微抬起+阴影）/ disabled（opacity .5）
- 进度节点：done / current（脉冲动画）/ pending
- 投票选项：默认 / selected（陶土橙边框+底色）
- 房间码输入：空 / 已填（陶土橙边框）
- Tab 切换：登录/注册

## Mock 数据结构

```
作品卡片：{ title, nodeCount, memberCount, likes, thumbSvg }
链：{ id, title, chainLength, visibility, roomCode, status, creator, nodes[] }
节点：{ id, seq, type(画/述), author, content, isAI }
投票：{ chainId, voter, dimension(最跑偏/最佳画/最佳描述), targetNodeId }
```

## 需要真实 API 的位置

| 页面 | API | 用途 |
|------|-----|------|
| P01 广场 | GET /api/works | 广场作品流 |
| P02 创建 | POST /api/chains | 创建链 + 生成房间码 |
| P02 创建 | POST /api/ai/prompt | AI 起手题（DeepSeek） |
| P03 加入 | GET /api/chains/{code} | 房间码校验 |
| P03 加入 | POST /api/chains/{id}/join | 加入链 |
| P04 大厅 | WS /ws/room/{id} | 实时围观笔迹推送 |
| P04 大厅 | GET /api/chains/{id} | 链状态/进度/成员 |
| P05 接力 | POST /api/nodes/{id}/submit | 提交节点 |
| P05 接力 | WS /ws/room/{id} | 推送作画笔迹 |
| P06 作品 | GET /api/works/{id} | 全链只读数据 |
| P07 回放 | POST /api/chains/{id}/votes | 提交投票 |
| P08 个人 | GET /api/users/me/works | 我的作品 |
| P09 登录 | POST /api/auth/register | 注册 |
| P09 登录 | POST /api/auth/login | 登录 |
| 后台 | 定时任务 | AI 补位（24h 超时扫描） |

## 哪些视觉效果必须生产实现

- **进度节点链脉冲动画**（P04 签名锚点）：current 节点的 box-shadow 脉冲，CSS @keyframes
- **逐节点渐显回放**（P07）：framer-motion 或 CSS transition，每节点 2s 间隔
- **画布涂鸦**（P05）：canvas 2D + pointer 事件 + 笔迹序列化
- **实时围观**（P04→P05）：WebSocket 笔迹事件广播 + canvas 重绘
- **手绘虚线边框**：CSS border-style:dashed 或 SVG stroke-dasharray
- **AI 续标签冷灰蓝区隔**：与暖色人画序列的视觉区隔

## 哪些只是原型展示效果

- 作品缩略图用 SVG 简笔画占位，生产用真实画作 PNG
- emoji（🔔🤖🐱）是原型占位，生产用 SVG 图标（反 AI slop 规范）
- 文字 Logo 的圆点 mark，生产可替换为真实 Logo
- 进度节点连线用 rectangle，生产可用 SVG path 画波浪线（设计意图）

## 设计 token（已写入 .pen 变量）

```
bg:#FAF6EF  paper:#FFFFFF  text:#2B2622  text2:#7A6F64  text3:#A89C8C
border:#D9CFC0  dash:#B8A890  accent:#C8643C  accentSoft:#F2E2D6
ai:#6B7A8F  aiSoft:#E8EDF2  canvas:#FFFBF3  white:#FFFFFF
```

## 技术栈（生产前端）

- React + TypeScript + Vite
- Ant Design（桌面 Web）
- canvas 2D（涂鸦画布）
- WebSocket（实时围观）
- framer-motion 或 CSS（回放动画）
