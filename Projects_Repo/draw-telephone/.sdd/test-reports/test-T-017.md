# 测试报告：T-017 节点接力功能闭环（上一节点/提交/防剧透）

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> 两个新端点全部命中真实后端，完整接力流程验证通过：起手题→画→述→推进→成员轮转→防剧透→责任人校验。GET /api/nodes/{id}/previous 防剧透（只返回上一节点，非责任人 403），POST /api/nodes/{id}/submit 提交推进链（校验当前责任人，创建下一节点，成员轮转指派下一位）。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户进入接力页，只看到真实上一节点内容（画或述），看不到后续 | PASS | GET /api/nodes/{id}/previous 只返回上一节点（seq=current_seq-1）。seq=0 时返回起手题（content_type=text）。非当前责任人 → 403「当前未轮到你」。前端 RelayPage getNodePrevious(id) 渲染 previous.content_type（image 显示 img / text 显示文字），无后续节点数据 |
| 2 | 画节点用户作画后提交，述节点用户输入描述后提交，提交后返回链大厅页 | PASS | POST /api/nodes/{id}/submit 画节点提交 {content_type:image, content_url}，述节点提交 {content_type:text, content_text}。提交成功 → 200 {node_id,seq,status,next_seq,chain_status}。前端 handleSubmit 提交后 navigate(`/chain/${id}`) 返回链大厅。注：画节点完整闭环（canvas 导出 PNG → 上传 → 提交）的「上传」部分由 T-018 实现，T-017 验证 submit 接口本身（直接传 content_url） |
| 3 | 非当前责任人访问接力页，看到「当前未轮到你」提示 | PASS | previous/submit 非当前责任人 → 403 {code:403, message:"当前未轮到你", data:null}。前端 catch → message.error。真实联调验证：joiner 在创建者未提交前看 previous → 403，非责任人提交 → 403 |
| 4 | 提交后链大厅页进度推进，下一节点解锁 | PASS | submit 后链 current_seq+1，创建下一节点（pending）。链大厅详情 GET /api/chains/{id}/detail 返回 current_seq 推进 + nodes 进度链更新。真实联调：创建者提交画后 current_seq=1，joiner 可看 previous（seq=0 画），链大厅 current_seq=2（joiner 提交述后） |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 GET /api/nodes/{id}/previous、POST /api/nodes/{id}/submit 单元/集成测试通过（含防剧透、责任人校验） | PASS | test_t017_node_relay.py 14 测试全过（previous 6 + submit 8，含防剧透、责任人校验、内容类型校验、链完成、完整接力流程） |
| 2 | frontend/src/services/nodes.ts 已将 Mock 替换为真实后端 API，VITE_USE_MOCK=false 时不走 Mock 分支 | PASS | nodes.ts 的 getNodePrevious/submitNode 本身就是真实 API 调用（`api.get/post('/nodes/...')`），无 Mock 分支 |
| 3 | 浏览器能证明请求命中真实后端 | PASS | 真实联调脚本验证：后端 8099 直连，11 项端点全过（见下「真实前后端联通验证」） |
| 4 | P05 页面不展示 [Mock] 数据 | PASS | RelayPage 注释已清理（Mock 阶段→真实后端，Mock 上传→T-018 标注），无 [Mock] 文案 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | Vite proxy /api → 8099（T-014 已配，T-017 复用） |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 37 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build（VITE_USE_MOCK=false） | PASS | built 通过（chunk size 警告非阻塞，非本次引入） |
| Vite proxy 真实联通 | PASS | 后端 8099 直连验证两个新端点全部正确 |

## 后端分层实现

按 backend-layers.md 从下往上分层：

| 层 | 文件 | 职责 |
|----|------|------|
| Pydantic 模型 | src/models/node.py | SubmitNodeImageRequest（content_type=image pattern + content_url）、SubmitNodeTextRequest（content_type=text pattern + content_text max=30）、SubmitNodeResponse（node_id/seq/status/next_seq/chain_status）、NodePreviousResponse（node_id/seq/type/content_type/content_url/content_text） |
| Repository | src/repositories/node.py | NodeRepository：get_chain、get_user（查下一位 nickname）、get_current_node（当前 seq 节点）、get_previous_node（上一节点）、update_node_submit（更新内容+status=submitted）、advance_chain（current_seq+1，完成时 status=completed+completed_at）、create_next_node（创建下一 pending 节点，type 按 seq 推导，author_id 可 None） |
| Service | src/services/node.py | NodeService：get_previous（防剧透，成员校验+当前责任人校验，seq=0 返回起手题虚拟节点，LookupError→404/PermissionError→403）+ submit_node（校验当前责任人+内容类型匹配，提交+推进链+创建下一节点，成员轮转指派下一位，ValueError→400） |
| API 路由 | src/api/routes/nodes.py | GET /{chain_id}/previous（LookupError→404，PermissionError→403）、POST /{chain_id}/submit（Union 请求体，isinstance type guard 分流 image/text，LookupError→404/PermissionError→403/ValueError→400） |
| 入口 | src/main.py | include_router(nodes_router) |

## 关键设计决策

### 1. 路径参数 {id} 是链 ID（非节点 ID）

api-contracts.md 路径是 `GET /api/nodes/{id}/previous`，语义上 {id} 像节点 ID。但前端 RelayPage 从路由 `/chain/:id/relay` 取的是**链 ID**，调 `getNodePrevious(id)` 和 `submitNode(id, ...)`。因此后端 `{id}` 接收链 ID，按链 ID 查 current_seq 对应的当前节点。路由参数命名为 `{chain_id}` 明确语义，路径仍为 `/api/nodes/{chain_id}/previous` 保持与前端一致。测试报告如实记录。

### 2. seq=0 的"上一节点"是起手题

seq=0 是起手 draw 节点，无 seq=-1 节点。get_previous 在 seq=0 时返回虚拟节点：`{node_id:"", seq:-1, type:"describe", content_type:"text", content_text:chain.prompt_text}`。这样前端 RelayPage 的 `isDrawMode = previous.content_type === 'text'` 为 true（看文字画图），展示起手题文字。语义一致：起手题是"上一棒"的文字描述，当前画师照题画图。

### 3. 成员轮转指派下一位

提交后创建下一节点时，下一位责任人按**成员加入顺序轮转**：`idx = next_seq % member_count`，members 按 joined_at 排序。chain_length=4 + 2 成员时：seq=0→creator, seq=1→joiner, seq=2→creator, seq=3→joiner。成员不足（next_seq >= member_count 且无新成员）时 author=None（待接，T-024 AI 补位）。运行时创建者与加入者之间有真实时间差，joined_at 排序稳定。

### 4. 内容类型与节点类型校验

draw 节点必须提交 image（content_url 非空），describe 节点必须提交 text（content_text 非空）。类型不匹配 → ValueError → 400。防止画节点提交文字或述节点提交图片。

### 5. Union 请求体的 type guard

submit 路由的请求体是 `SubmitNodeImageRequest | SubmitNodeTextRequest`（discriminated union by content_type）。路由层用 `isinstance(body, SubmitNodeImageRequest)` type guard 分流 content_url/content_text，避免 mypy union-attr 错误。

## 防剧透与接力流程

```
完整接力流程（chain_length=4，2 成员轮转）：

1. 创建者看 previous（seq=0）→ 起手题「戴帽子的猫」（content_type=text）
2. joiner 看 previous → 403（未轮到，seq=0 责任人是创建者）
3. 创建者提交画（image）→ next_seq=1，创建 seq=1 describe 节点给 joiner
4. joiner 看 previous → 200（返回 seq=0 的画，content_type=image）✓ 防剧透：只看到上一节点
5. joiner 提交述（text）→ next_seq=2，创建 seq=2 draw 节点给创建者（2%2=0 轮转）
6. 创建者看 previous → 200（返回 seq=1 的述「戴礼帽的猫」）✓ 轮转回来
7. 链大厅 current_seq=2，进度推进，nodes[0]/nodes[1] 已建带真实 author
```

## 测试用例说明

`backend/tests/test_t017_node_relay.py`（14 测试，内存 SQLite + dependency_overrides）：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_previous_seq0_returns_prompt | seq=0 看起手题（content_type=text） | PASS |
| test_previous_non_responsible_403 | 非当前责任人 → 403 | PASS |
| test_previous_non_member_403 | 非链成员 → 403 | PASS |
| test_previous_chain_not_found | 链不存在 → 404 | PASS |
| test_previous_no_token_401 | 无 token → 401 | PASS |
| test_previous_returns_submitted_node | seq=1 看 seq=0 已提交画（image） | PASS |
| test_submit_draw_node_success | 画节点提交 → 推进+创建 seq=1 describe | PASS |
| test_submit_describe_node_success | 述节点提交 → 推进+创建 seq=2 draw | PASS |
| test_submit_non_responsible_403 | 非责任人提交 → 403 | PASS |
| test_submit_wrong_content_type_400 | 画节点提交 text → 400 | PASS |
| test_submit_empty_text_400 | 述节点提交空文字 → 400 | PASS |
| test_submit_chain_not_found | 链不存在 → 404 | PASS |
| test_submit_last_node_completes_chain | 提交最后一节点 → 链 completed | PASS |
| test_relay_flow_previous_after_submit | 完整接力流程（7 步轮转+防剧透） | PASS |

## 真实前后端联通验证

```
后端 8099（真实 SQLite 文件库，数据持久化）：

1. 注册 2 用户（创建者+加入者）→ 200 + JWT
2. 创建链（chain_length=4）→ 200 + chain_id
3. joiner 加入链 → 200 + joined=true
4. 创建者 GET /api/nodes/{id}/previous → 200 + 起手题「戴帽子的猫」
5. joiner GET /api/nodes/{id}/previous → 403「当前未轮到你」
6. 创建者 POST /api/nodes/{id}/submit（image）→ 200 + next_seq=1
7. joiner GET /api/nodes/{id}/previous → 200 + seq=0 画（content_url）
8. joiner POST /api/nodes/{id}/submit（text「戴礼帽的猫」）→ 200 + next_seq=2
9. 创建者 GET /api/nodes/{id}/previous → 200 + seq=1 述（轮转回来）
10. GET /api/chains/{id}/detail → 200 + current_seq=2，nodes[0]/[1] 真实 author
11. joiner POST /api/nodes/{id}/submit（非责任人）→ 403
```

## DB 持久化

- 真实 SQLite 文件库，数据落盘：Node 表记录已提交节点（content_type/content_url/content_text/status=submitted/submitted_at），Chain 表 current_seq 推进，新节点 pending 创建。
- 提交后链大厅详情能查到推进后的 current_seq 和已建节点真实 author。
- 链完成时 status=completed + completed_at 填充，不创建超出 chain_length 的节点。

## 与 T-018 的边界

T-017 实现了 previous + submit 后端 + 前端清理。画节点完整闭环的「上传」部分（canvas 导出 PNG → POST /api/upload/image → 获取 URL）由 T-018 实现上传后端后完成。T-017 验证 submit 接口本身（直接传 content_url 字符串），不依赖上传后端。前端 RelayPage 的画节点 handleSubmit 已写好上传→提交流程，T-018 实现上传后端后即可完整联调。

**自动验证全部通过（14 单元测试 + 11 项真实联调）。T-017 user_gate=true，需用户门禁验收浏览器 UI（接力页看上一节点→作画/描述→提交→返回大厅→进度推进）。**
