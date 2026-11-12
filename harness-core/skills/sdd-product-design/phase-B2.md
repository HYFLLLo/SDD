# 阶段 B2：原型设计

**严格按照 `.sdd/tmp/ui-design-spec.md` 设计原型。目标是尽快让用户看到可验证的前端原型，同时保留设计上下文、竞品视觉证据和后续生产前端交接信息。**

## 设计规范底座（必须加载）

进入 B2 时必须先加载：

```text
harness-core/skills/ui-design-standard/SKILL.md
```

该 Skill 定义原型阶段的底线：可读性、中文显示、组件状态、视口验证、竞品参考边界、原型与生产代码边界。

## 原型架构选择（先于工具选择）

进入 B2 后，不得直接问“用什么工具”。必须先根据 `ui-design-spec.md` 判断原型交付形态；如果 Design Spec 已经给出明确建议，直接采用，不再二次询问。

| 原型形态 | 适用场景 | 输出 |
|----------|----------|------|
| Overview 平铺 | 用户要看全部页面、比较布局、一眼 review | 多屏并排 HTML 或 Pencil Frame |
| 单机流程演示 | 用户要演示一条用户路径、点击走流程 | 单设备可点击 HTML 原型 |
| 桌面 Web 原型 | 后台 / SaaS / AI 工具控制台 | Browser frame 或 1440×900 页面 |
| 移动端 H5 原型 | 手机浏览器 / 微信内网页 / PWA | iOS/Android frame 或 390×844 页面 |
| 16:9 课件页 | 用于课程讲解、概念图、系统图 | 16:9 HTML / 图片 |

## 工具选择

默认使用 **HTML 原型**。只有用户明确指定，或项目环境更适合画布编辑时，才使用 Pencil / Stitch。

| 方式 | 输出格式 | 适用 |
|------|----------|------|
| HTML 原型（默认） | `.html` | 速度最快，可点击、可截图、可验证 |
| Pencil MCP | `.pen` | 需要可编辑画布时 |
| Stitch | HTML + TailwindCSS `.zip` | 用户明确要求使用 Stitch 时 |

## Junior Pass（快路径）

Junior Pass 的目标是低成本确认方向，不是增加流程负担。

### 必做场景

出现以下任一情况，必须先做 Junior Pass：

- Design Spec 中缺少竞品截图 / URL / design context
- 用户要求视觉质量高或多方案比较
- 原型超过 5 个界面
- 单机流程演示路径复杂
- Agent 对页面信息层级或视觉方向不确定

### 可跳过场景

如果 PRD、Design Spec、视觉证据、页面清单都很明确，可以跳过 Junior Pass，直接进入 Full Pass，但必须在输出里简短标注：

```text
已走快速路径：Design Spec 明确，直接生成高保真原型。
```

### Junior Pass 内容

- 原型形态：overview / flow demo / desktop / mobile H5 / 16:9
- 页面清单
- 每个页面的主要区域
- 关键用户路径
- assumptions
- placeholders
- 未确认问题
- 参考竞品截图 / URL 的使用位置

**技法**：把 assumptions、placeholder（灰块+文字标签）、reasoning 直接写在 HTML 开头并尽早 show 给用户。底层逻辑是「理解错了早改比晚改便宜 100 倍」——不要闷头画完高保真再给用户看。

确认文案：

```text
我已完成 Junior Pass：页面结构、主要路径、占位内容和设计假设已列出。
请确认方向是否正确。确认后我再进入 Full Pass 高保真原型绘制。
```

未经用户确认 Junior Pass，不得进入 Full Pass。

---

## Full Pass：按模式正式产出高保真原型

Junior Pass 确认方向后（或符合「可跳过场景」直接），进入 Full Pass：按下方选定的模式（A HTML / B Pencil / C Stitch）正式绘制高保真原型，填充 placeholder、补齐示例数据与交互状态。下方「模式 A / B / C」即 Full Pass 的三种执行路径。

---

## 模式 A：HTML 原型（默认）

### 适用

- 移动端 H5 原型
- 桌面 Web 原型
- 单机流程演示
- Overview 平铺
- 16:9 课件页

### 执行步骤

1. 读取 `.sdd/tmp/ui-design-spec.md`
2. 读取 `.sdd/tmp/visual-research.md`（如存在）
3. 根据原型形态选择布局：Browser / iOS / Android / 16:9 / 多屏平铺
4. 用 HTML/CSS/JS 绘制原型
5. 可点击 flow demo 必须包含最小状态机
6. 所有页面必须使用中文真实示例内容
7. 禁止把 Markdown 描述当原型
8. 原型代码仅用于设计验证，不作为生产前端源码

### 输出路径

推荐输出：

```text
docs/prototypes/index.html
```

多页面分拆时输出：

```text
docs/prototypes/
├── index.html
├── 01-login.html
├── 02-dashboard.html
└── assets/
```

### 生产前端交接说明（必须写入原型或同目录 README）

HTML 原型完成后，必须在 `docs/prototypes/README.md` 或 HTML 注释中标注：

- 页面清单
- 关键组件清单
- 交互状态
- Mock 数据结构
- 需要真实 API 的位置
- 哪些视觉效果必须生产实现
- 哪些只是原型展示效果

---

## 模式 B：Pencil MCP

### 准备工作

1. 加载 UI Design Standard Skill
2. 阅读 `.sdd/tmp/ui-design-spec.md`
3. 阅读 `.sdd/tmp/visual-research.md`（如存在）
4. 调用 `get_guidelines("web-app")` 获取 Pencil 设计指南
5. 调用 `get_style_guide_tags` → `get_style_guide(tags)` 获取风格参考
6. 调用 `open_document("new")` 创建新画布

如果 Pencil MCP 连接失败，告诉用户：「可以自行前往 Pencil 绘制原型图，并将 `.pen` 文件保存到 `docs/prototypes/`。」同时提供可复制给 Pencil 的完整提示词，并保存到：

```text
docs/prototypes/pencil-prompt.md
```

### 批量绘制

允许一次性绘制全部界面，不需要每个界面单独门禁。

执行要求：

1. 阅读 `ui-design-spec.md` 中全部界面描述
2. 为每个界面创建 1 个独立 Frame，命名为 `NN-界面名`
3. 桌面 Web 默认尺寸 1440×900；移动端 H5 默认尺寸 390×844
4. 所有 Frame 必须在同一画布中有序排列，禁止重叠
5. 每个 Frame 严格按组件清单和示例数据绘制
6. 全部界面绘制完成后，再统一截图验证、保存、发起 B2 阶段门禁

### Pencil 画布布局硬规则

所有界面 Frame 必须在同一画布中横向排列或网格排列，不得重叠。

默认采用横向排列；界面超过 5 个时可改用网格排列：每行最多 3 个，水平间距 240，垂直间距 240。

禁止：

- 不指定 `x/y` 就插入新的界面 Frame
- 把多个界面放在同一个 Frame 内
- 把多个 Frame 放在同一坐标
- 为了节省空间缩小界面 Frame 尺寸

---

## 模式 C：Stitch

仅在用户明确选择 Stitch 时使用。

### 步骤 1：生成 Stitch 提示词

AI 阅读 `.sdd/tmp/ui-design-spec.md`，为每个界面生成英文提示词，必须包含：

1. 页面类型与用途
2. 视觉方向（来自 Design Spec，不得另起风格）
3. 配色、字体、圆角、间距、信息密度
4. 布局结构
5. 组件清单及细节
6. 示例数据（列表至少 3 条，对话至少 2-3 轮，表格至少 3-5 行）
7. 视口（桌面端 1440×900 或移动端 390×844）
8. 必须参考的竞品截图 / URL（如有）

将提示词在对话中呈现给用户，告知：「已生成 Stitch 提示词，请复制到 Stitch 中生成界面。」

### 步骤 2：用户在 Stitch 中生成并导出

用户操作（AI 给出指引）：

1. 打开 stitch.withgoogle.com
2. 粘贴提示词 → 生成界面
3. 点击 More → Download 下载 `.zip`
4. 解压到 `docs/prototypes/` 下对应目录

文件规范：

```text
docs/prototypes/
├── 01-登录页/
│   ├── index.html
│   └── style.css
├── 02-仪表盘/
│   └── ...
└── ...
```

### 步骤 3：AI 验证

每个界面导入后，AI 读取 HTML/CSS 文件：

- 对照 `ui-design-spec.md` 的组件清单逐项核对
- 检查示例数据完整性
- 检查布局结构是否与 spec 一致
- 检查是否真正参考 visual research 中的截图/URL
- 标注缺失或偏差

---

## 原型质量要求（所有模式通用）

- 每个界面必须生成可视化原型，禁止用 Markdown 文字描述充当原型
- 禁止不看 `.sdd/tmp/ui-design-spec.md` 直接画
- 如果 `.sdd/tmp/visual-research.md` 存在，禁止不看竞品视觉证据直接画
- 列表/卡片至少 2 条示例数据
- 对话界面至少 2 轮气泡消息
- 移动端 H5 必须检查 390×844 视口
- 桌面 Web 必须检查 1440×900 视口
- 可点击 flow demo 必须至少验证 3 个关键点击
- 不得把原型 HTML 当作生产前端源码

### 原型验证清单

- [ ] 原型能在浏览器打开
- [ ] 控制台无明显 JS 错误
- [ ] 页面无重叠、裁切、明显溢出
- [ ] 关键页面与 `ui-design-spec.md` 的组件清单一致
- [ ] 关键视觉规则来自 Design Context 或已确认的默认设计基底
- [ ] 竞品参考只借鉴结构/交互/视觉规律，不照搬品牌和内容
- [ ] 移动端/桌面目标视口截图正常
- [ ] 如为 flow demo，关键按钮可点击，路径可走通
- [ ] 所有显示文字为中文，禁止英文占位符

## 完成收尾

1. 原型输出到 `docs/prototypes/`
2. 删除临时文件 `.sdd/tmp/ui-design-spec.md`
3. 如存在 `.sdd/tmp/visual-research.md`，**保留到阶段 C 完成后删除**（权威口径见 SKILL.md「产出物映射表」），确保 API 契约和 Plan 能参考原型上下文
4. 发起最终确认：「阶段 B2 原型已完成，请确认是否进入阶段 C。」

**未经用户明确确认“进入阶段 C”，不得执行阶段 C。**
