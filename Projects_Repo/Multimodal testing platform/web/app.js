/* 多模态大模型能力测试平台 - 前端逻辑（无框架 SPA） */

// 全局状态（跨页面持久化）
const state = {};

// ---------------------------------------------------------------- 基础工具
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

async function api(path, opts) {
  opts = opts || {};
  if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
    opts.headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  }
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.json();
}
const get = (p) => api(p);
const post = (p, b) => api(p, { method: "POST", body: b || {} });
const put = (p, b) => api(p, { method: "PUT", body: b });
const del = (p) => api(p, { method: "DELETE" });

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function enc(p) { return encodeURI(p).replace(/#/g, "%23").replace(/\?/g, "%3F"); }
// 显示/隐藏统一走这里：.u-hide.u-hide 是为了压过组件规则而写成 (0,2,0)，
// 若只改 style.display，类名仍在、元素永远是 display:none。
function setShown(el, shown) {
  if (!el) return;
  el.classList.toggle("u-hide", !shown);
  el.style.display = shown ? "" : "none";
}
const encQ = encodeURIComponent;  // query 参数值专用（& = 等也必须转义）

function toast(msg, ok) {
  const d = document.createElement("div");
  d.className = "msg " + (ok === false ? "err" : "ok");
  d.setAttribute("role", ok === false ? "alert" : "status");
  d.setAttribute("aria-live", ok === false ? "assertive" : "polite");
  d.style.cssText = "position:fixed;top:60px;right:20px;z-index:300;box-shadow:0 2px 10px rgba(0,0,0,.15)";
  d.textContent = msg;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3000);
}

function jsonHtml(obj) {
  let s = esc(JSON.stringify(obj, null, 2));
  s = s.replace(/&quot;([^&]*?)&quot;(\s*:)?/g, (m, g1, g2) =>
    g2 ? `<span class="k">&quot;${g1}&quot;</span>:` : `<span class="s">&quot;${g1}&quot;</span>`);
  s = s.replace(/: (-?\d[\d.]*)/g, ': <span class="n">$1</span>');
  s = s.replace(/: (true|false|null)/g, ': <span class="b">$1</span>');
  return s;
}

// 可折叠 JSON 树（bejson 风格）：对象/数组可展开收起，值按类型着色
function jsonTreeHtml(obj) {
  const leaf = (v) => {
    if (v === null) return `<span class="b">null</span>`;
    if (typeof v === "number") return `<span class="n">${v}</span>`;
    if (typeof v === "boolean") return `<span class="b">${v}</span>`;
    return `<span class="s">"${esc(String(v))}"</span>`;
  };
  const render = (val, key, isIdx) => {
    const keyHtml = key !== null && key !== undefined
      ? `<span class="${isIdx ? "jt-idx" : "k"}">${isIdx ? esc(key) : "&quot;" + esc(key) + "&quot;"}</span>: ` : "";
    if (val === null || typeof val !== "object")
      return `<div class="jt-leaf">${keyHtml}${leaf(val)}</div>`;
    const isArr = Array.isArray(val);
    const entries = isArr ? val.map((v, i) => [String(i), v, true]) : Object.entries(val).map(([k, v]) => [k, v, false]);
    if (!entries.length)
      return `<div class="jt-leaf">${keyHtml}<span class="jt-type">${isArr ? "[]" : "{}"}</span></div>`;
    const kids = entries.map(([k, v, idx]) => render(v, k, idx)).join("");
    return `<details class="jt-node" open><summary>${keyHtml}<span class="jt-type">${isArr ? `Array[${entries.length}]` : `Object{${entries.length}}`}</span></summary><div class="jt-kids">${kids}</div></details>`;
  };
  return render(obj, null, false);
}

// ---------------------------------------------------------------- 结果渲染
// 解析结果的内部结构是「模型输出 + 诊断元数据」的混合体：
//   overall_status / summary / scene / objects  ← 业务结论
//   raw / source_json                           ← 与上面重复或更原始的文本
//   parse_ok / protocol_valid / protocol_errors ← 协议校验
//   _meta                                       ← 运行参数、耗时、token
// 直接把整个对象摊成树，用户要在十来行机器字段里翻找「到底判了什么」，
// 而 raw 里还有一坨带转义的原文占掉半屏。所以默认先给结论卡，
// 原始数据降级成可折叠的「技术细节」。

function resultStatusLabel(s) {
  const v = String(s == null ? "" : s).trim();
  if (!v) return "—";
  return v;
}

// 场景分析：键是模型按提示词自定义的（image_quality / 是否存在目标/事件 …），
// 这里不写死键名，统一按「键：值」两列渲染。
// 常见键给中文别名：同一行里「是否存在目标/事件」与「image_quality」并排很割裂。
const SCENE_KEY_CN = {
  image_quality: "图像质量", quality: "图像质量",
  "是否存在目标/事件": "是否有目标", has_target: "是否有目标", has_object: "是否有目标",
  scene: "场景", scene_type: "场景类型", environment: "环境",
};
function sceneKeyLabel(k) {
  return SCENE_KEY_CN[k] || SCENE_KEY_CN[String(k).toLowerCase()] || k;
}
function resultSceneHtml(scene) {
  if (!scene || typeof scene !== "object") return "";
  const entries = Object.entries(scene).filter(([, v]) => v !== "" && v !== null && v !== undefined);
  if (!entries.length) return "";
  return `<div class="rv-scene">${entries.map(([k, v]) =>
    `<div class="rv-scene-item"><span class="rv-k">${esc(sceneKeyLabel(k))}</span><span class="rv-v">${esc(typeof v === "object" ? JSON.stringify(v) : String(v))}</span></div>`
  ).join("")}</div>`;
}

function resultObjectsHtml(objects) {
  if (!Array.isArray(objects) || !objects.length) {
    return `<div class="rv-none">模型未检出目标 / 事件</div>`;
  }
  return `<div class="rv-objs">${objects.map((o, i) => {
    const name = o.name || o.labelName || `目标 ${i + 1}`;
    const val = o.label_value || o.labelValue || "";
    const conf = o.confidence != null && o.confidence !== "" ? Number(o.confidence) : null;
    const box = Array.isArray(o.bbox) ? o.bbox.map(n => Math.round(Number(n))).join(", ") : "";
    const evidence = o.evidence || o.description || "";
    const attrs = Object.entries(o.attributes || {}).filter(([, v]) => v !== "" && v != null);
    return `<div class="rv-obj">
      <div class="rv-obj-head">
        <span class="rv-obj-name">${esc(name)}</span>
        ${val ? `<span class="rv-obj-val">${esc(val)}</span>` : ""}
        ${conf != null && isFinite(conf) ? `<span class="rv-obj-conf" title="模型置信度">${(conf <= 1 ? conf * 100 : conf).toFixed(0)}%</span>` : ""}
      </div>
      ${evidence ? `<div class="rv-obj-ev">${esc(evidence)}</div>` : ""}
      ${box ? `<div class="rv-obj-meta"><span class="rv-k">bbox</span><code>${esc(box)}</code></div>` : ""}
      ${attrs.length ? `<div class="rv-obj-meta">${attrs.map(([k, v]) =>
        `<span class="rv-k">${esc(k)}</span><code>${esc(typeof v === "object" ? JSON.stringify(v) : String(v))}</code>`).join("")}</div>` : ""}
    </div>`;
  }).join("")}</div>`;
}

function resultMetaHtml(meta) {
  if (!meta || typeof meta !== "object") return "";
  const usage = meta.usage || {};
  const bits = [];
  if (meta.latency != null) bits.push(`<span><span class="rv-k">耗时</span>${Number(meta.latency).toFixed(2)}s</span>`);
  if (usage.total_tokens != null) bits.push(`<span><span class="rv-k">tokens</span>${usage.prompt_tokens || 0} + ${usage.completion_tokens || 0} = ${usage.total_tokens}</span>`);
  if (meta.timestamp) bits.push(`<span><span class="rv-k">时间</span>${esc(String(meta.timestamp).slice(5))}</span>`);
  return bits.length ? `<div class="rv-foot">${bits.join("")}</div>` : "";
}

// 结论摘要 + 协议校验 + 可折叠技术细节
function resultPanel(data, opts) {
  const o = opts || {};
  if (!data || typeof data !== "object") return `<div class="json-view">结果不存在</div>`;
  const status = data.overall_status;
  const summary = data.summary || "";
  const errs = Array.isArray(data.protocol_errors) ? data.protocol_errors : [];
  const problems = [];
  // 有上游错误时它就是根因，此时再说「未能解析为 JSON」是噪音
  const upstreamErr = data.error || (data._meta && data._meta.error) || "";
  if (upstreamErr) problems.push(String(upstreamErr));
  else if (data.parse_ok === false) problems.push("模型输出未能解析为 JSON");
  if (data.protocol_valid === false) problems.push("不符合最小协议");
  errs.forEach(e => problems.push(String(e)));
  const failed = !!upstreamErr && data.parse_ok === false && !summary;

  const custom = data.custom && typeof data.custom === "object" ? data.custom : null;

  return `<div class="result-panel">
    <div class="rv-top">
      <div class="rv-top-l">
        <span class="rv-status-dot ${statusDotClass(status)}" aria-hidden="true"></span>
        <span class="rv-status">${esc(resultStatusLabel(status))}</span>
        ${(data.parse_ok === false || failed) && summary === "" ? `<span class="rv-note">模型这次没有返回可用结论</span>` : ""}
        ${data.protocol_valid === false ? `<span class="tag orange">协议不合规</span>` : ""}
        ${data.parse_ok === false && !failed ? `<span class="tag red">解析失败</span>` : ""}
      </div>
      <span class="rv-detail-tog" data-rv="detail" role="button" tabindex="0">技术细节</span>
    </div>
    ${summary ? `<div class="rv-summary">${esc(summary)}</div>` : ""}
    ${problems.length ? `<div class="msg warn rv-problems">${problems.map(esc).join("<br>")}</div>` : ""}
    ${resultSceneHtml(data.scene)}
    ${(() => {
      // 解析失败时 objects 一定是空的，但那是「没读到」而不是「没检出」，
      // 再写一句「模型未检出目标」会把失败说成结论，必须整块隐去。
      if (o.noObjects || data.parse_ok === false || !("objects" in data)) return "";
      return `<div class="rv-sec-title">检出目标 <span class="rv-sec-n">${(data.objects || []).length}</span></div>` + resultObjectsHtml(data.objects);
    })()}
    ${custom ? `<details class="rv-custom"><summary class="rv-k">自定义字段</summary><div class="json-view">${jsonHtml(custom)}</div></details>` : ""}
    ${resultMetaHtml(data._meta)}
    <div class="rv-detail u-hide">
      <div class="json-panel-bar">
        <span class="jp-tog active" data-m="tree">完整结构</span><span class="jp-tog" data-m="raw">原始 JSON</span>
      </div>
      <div class="json-view jp-tree">${jsonTreeHtml(data)}</div>
      <div class="json-view jp-raw u-hide">${jsonHtml(data)}</div>
    </div>
  </div>`;
}

// 树形/原文双模式 JSON 面板（JSON 工具等「就是要看原始结构」的场景复用）
function jsonPanel(data) {
  return `<div class="json-panel">
    <div class="json-panel-bar">
      <span class="jp-tog active" data-m="tree">树形</span><span class="jp-tog" data-m="raw">原文</span>
    </div>
    <div class="json-view jp-tree">${jsonTreeHtml(data)}</div>
    <div class="json-view jp-raw u-hide">${jsonHtml(data)}</div>
  </div>`;
}

document.addEventListener("click", (e) => {
  const t = e.target.closest(".jp-tog");
  if (t) {
    // 结论卡里的「技术细节」用 .rv-detail 作容器，不是 .json-panel
    const panel = t.closest(".json-panel, .rv-detail");
    if (!panel) return;
    panel.querySelectorAll(".jp-tog").forEach(x => x.classList.toggle("active", x === t));
    setShown(panel.querySelector(".jp-tree"), t.dataset.m === "tree");
    setShown(panel.querySelector(".jp-raw"), t.dataset.m === "raw");
    return;
  }
  // 「技术细节」：默认收起，展开后才有树形/原文切换
  const dt = e.target.closest(".rv-detail-tog");
  if (!dt) return;
  const root = dt.closest(".result-panel");
  const box = root && root.querySelector(".rv-detail");
  if (!box) return;
  const open = !dt.classList.contains("active");
  dt.classList.toggle("active", open);
  dt.setAttribute("aria-expanded", open ? "true" : "false");
  setShown(box, open);
});

// 「技术细节」是 role=button，需要回车/空格也能展开
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const dt = e.target.closest && e.target.closest(".rv-detail-tog");
  if (!dt) return;
  e.preventDefault();
  dt.click();
});

// 带行列号定位的 JSON 解析（用于 JSON 工具的错误提示）
function parseJsonEx(text) {
  try { return { ok: true, data: JSON.parse(text) }; }
  catch (e) {
    const r = { ok: false, message: e.message };
    const m = /position (\d+)/i.exec(e.message);
    if (m) {
      r.pos = Number(m[1]);
      const before = text.slice(0, r.pos);
      r.line = before.split("\n").length;
      r.col = r.pos - before.lastIndexOf("\n");
    }
    return r;
  }
}

function zoom(src) {
  const m = document.createElement("div");
  m.className = "modal-mask";
  m.setAttribute("role", "dialog");
  m.setAttribute("aria-modal", "true");
  m.setAttribute("aria-label", "图片预览，点击关闭");
  // 用属性赋值而不是拼接 HTML：src 来自模型输出，避免注入
  const img = document.createElement("img");
  img.src = src;
  img.alt = "放大预览";
  m.appendChild(img);
  m.onclick = () => m.remove();
  document.body.appendChild(m);
}

// 推理图仅在模型检出目标时生成；未检出时回退显示原图并说明原因
// CSP 下不允许内联事件处理器：图片预览/推理图回退统一用事件委托
document.addEventListener("click", (e) => {
  const img = e.target.closest && e.target.closest('img[data-zoom]:not([data-zoom=""])');
  if (img) zoom(img.src);
});
// 站内链接统一用 #，阻止默认跳转以免污染路由 hash
document.addEventListener("click", (e) => {
  const a = e.target.closest && e.target.closest("a.link");
  if (a && a.getAttribute("href") === "#") e.preventDefault();
});
document.addEventListener("error", (e) => {
  const img = e.target;
  if (!img || img.tagName !== "IMG") return;
  const fallback = img.dataset && img.dataset.annFallback;
  if (fallback && !img.dataset.annFallbackUsed) {
    img.dataset.annFallbackUsed = "1";
    annOrOrig(img, fallback);
  } else if (img.dataset && img.dataset.hideOnError) {
    setShown(img.parentElement, false);
  }
}, true);

function annOrOrig(img, origUrl) {
  img.onerror = () => { setShown(img, false); };
  img.src = origUrl;
  const note = document.createElement("div");
  note.className = "muted";
  note.style.cssText = "font-size:var(--fs-xs);margin-bottom:4px";
  note.textContent = "模型未检出目标，显示原图";
  img.parentElement.insertBefore(note, img);
}

// 渲染优化建议详情：新旧模块对比 + 保存/验证按钮。生成完成页与历史记录查看共用。
// run 可为空（历史记录场景），此时按 rec.source_run 拉取运行信息用于"立即验证"。
async function renderOptRecord(container, rec, run, onClose) {
  let oldSections = {};
  try {
    const ver = await get(`/api/prompts/${encodeURIComponent(rec.prompt_name)}/versions/${rec.source_version}`);
    oldSections = ver.sections || {};
  } catch (e) {}
  const changed = rec.changed_modules || [];
  const rcCounts = Object.entries(rec.root_cause_counts || {});
  container.innerHTML = `
    <div class="msg ok u-mt-12">优化建议已生成（基于 ${rec.selected_evidence_count || 0} 条裁判证据） · ${esc(rec.created || "")}</div>
    ${rcCounts.length ? `<div class="judge-meta-line">根因分布：${rcCounts.map(([k, v]) => `<span class="tag blue">${esc(k)} × ${v}</span>`).join("")}</div>` : ""}
    <div class="fault-card u-bd-l-primary">
      <div class="fk">修改摘要</div><div class="fv">${esc(rec.change_summary || "（优化器未提供摘要）")}</div>
      <div class="fk">预期效果</div><div class="fv">${esc(rec.expected_effect || "-")}</div>
      <div class="fk">改动模块</div><div class="fv">${changed.length ? changed.map(m => `<span class="tag orange">${esc(m)}</span>`).join("") : '<span class="muted">无模块级改动</span>'}</div>
    </div>
    ${changed.map(m => {
      const title = (PROMPT_SECTIONS.find(([k]) => k === m) || [m, m])[1];
      return `<div class="u-mt-10"><div class="muted u-mb-4">${esc(title)}</div>
      <div class="opt-compare">
        <div class="oc-col"><div class="oc-head">当前 V${rec.source_version}</div><textarea class="oc-old" rows="8" readonly>${esc(oldSections[m] || "")}</textarea></div>
        <div class="oc-col"><div class="oc-head">优化后</div><textarea class="oc-new" rows="8" readonly>${esc((rec.sections || {})[m] || "")}</textarea></div>
      </div></div>`;
    }).join("")}
    <div class="dlg-actions">
      ${rec.saved_version ? `<span class="tag green u-as-c">已保存为 V${rec.saved_version}</span>` : `<button class="btn primary" id="op-save">确认修改，保存为新版本</button>`}
      <button class="btn" id="op-discard">关闭</button>
      <span class="muted u-as-c" id="op-save-status"></span>
    </div>`;
  container.querySelector("#op-discard").onclick = onClose;
  const saveBtn = container.querySelector("#op-save");
  if (saveBtn) saveBtn.onclick = async () => {
    const saveStatus = container.querySelector("#op-save-status");
    saveBtn.disabled = true;
    try {
      const note = (rec.change_summary || "裁判驱动优化").slice(0, 120);
      const r = await post(`/api/prompt-ai/optimizations/${encodeURIComponent(rec.id)}/save`, { note, branch: "main" });
      const newVer = r.version || r.saved_version || (r.info || {}).version;
      rec.saved_version = newVer;
      let runInfo = run;
      if (!runInfo && rec.source_run) {
        try { runInfo = await get(`/api/runs/${encodeURIComponent(rec.source_run)}`); } catch (e) {}
      }
      container.innerHTML = `
        <div class="msg ok u-mt-12">已保存为「${esc(rec.prompt_name)}」V${newVer}。建议立即跑一次验证，对比优化前后的效果。</div>
        <div class="dlg-actions">
          ${runInfo ? `<button class="btn primary" id="op-verify">立即运行验证</button>` : ""}
          <button class="btn" id="op-done">关闭</button>
        </div>`;
      container.querySelector("#op-done").onclick = onClose;
      const verifyBtn = container.querySelector("#op-verify");
      if (verifyBtn) verifyBtn.onclick = () => {
        state._runPreselect = { prompt_name: rec.prompt_name, prompt_version: Number(newVer), dataset: runInfo.dataset, split: runInfo.dataset_split || "" };
        onClose();
        location.hash = "#/runs";
      };
      if (state._optRecordsReload) state._optRecordsReload();
    } catch (e) { saveStatus.innerHTML = `<span class="tag red">保存失败</span> ${esc(e.message)}`; saveBtn.disabled = false; }
  };
}

// 将键盘焦点限制在当前弹窗内；返回卸载函数
function trapDlgFocus(mask) {
  const visible = (el) => el.getClientRects().length > 0;
  const onKey = (e) => {
    if (e.key !== "Tab") return;
    const nodes = Array.from(mask.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(visible);
    if (!nodes.length) return;
    const first = nodes[0], last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  mask.addEventListener("keydown", onKey);
  return () => mask.removeEventListener("keydown", onKey);
}

let dlgSeq = 0;

// 通用弹窗：返回 { mask, box, close }；Esc / 点遮罩关闭，关闭后归还焦点
function openDlg(html, opts) {
  opts = opts || {};
  const mask = document.createElement("div");
  mask.className = "dlg-mask";
  // 弹窗宽度按内容分档：默认是 440px 的窄确认框。原来 `.dlg` 写死 width:100%
  // + max-width:980px，一句「确定删除？」也被撑成 980px，正文挤在左边一小条。
  // 只有真正的宽内容（优化建议的左右对比、多字段表单）才声明 opts.wide。
  const sizeClass = opts.wide ? " dlg-wide" : "";
  mask.innerHTML = `<div class="dlg${sizeClass}" role="dialog" aria-modal="true">${html}</div>`;
  const box = mask.querySelector(".dlg");
  let headingId = opts.id || "";
  if (!headingId) {
    const heading = box.querySelector("h3, h4");
    if (heading) { headingId = "dlg-title-" + (++dlgSeq); heading.id = headingId; }
  }
  if (headingId) box.setAttribute("aria-labelledby", headingId);
  else box.setAttribute("aria-label", opts.title || "对话框");
  const previousFocus = document.activeElement;
  const untrap = trapDlgFocus(mask);
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    document.removeEventListener("keydown", onKey);
    untrap();
    mask.remove();
    if (previousFocus && previousFocus.isConnected && typeof previousFocus.focus === "function") previousFocus.focus();
    if (typeof opts.onClose === "function") opts.onClose();
  };
  const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); close(); } };
  mask.addEventListener("click", (e) => { if (e.target === mask) close(); });
  document.addEventListener("keydown", onKey);
  document.body.appendChild(mask);
  const autofocus = box.querySelector("[autofocus]") ||
    box.querySelector("input:not([type='hidden']):not([disabled]), textarea:not([disabled]), select:not([disabled])") ||
    box.querySelector("button:not([disabled])");
  if (autofocus) autofocus.focus();
  return { mask, box, close };
}

function dlgActions(okText, cancelText, danger) {
  return `<div class="dlg-actions">
    <button class="btn ${danger ? "danger" : "primary"}" id="dlg-ok">${esc(okText || "确定")}</button>
    ${cancelText === false ? "" : `<button class="btn" id="dlg-cancel">${esc(cancelText || "取消")}</button>`}
  </div>`;
}

// 站内确认框：Promise<boolean>；Esc / 点遮罩 / 取消均为 false
function confirmDlg(message, opts) {
  opts = opts || {};
  const allowCancel = opts.cancelText !== false;
  return new Promise((resolve) => {
    const id = "dlg-title-" + (++dlgSeq);
    const html = `<h3 id="${id}">${esc(opts.title || "请确认")}</h3>
      <div class="dlg-message">${esc(message).replace(/\n/g, "<br>")}</div>
      ${dlgActions(opts.okText || "确定", allowCancel ? (opts.cancelText || "取消") : false, opts.danger !== false)}`;
    let settled = false;
    let dlg;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      dlg.close();
      resolve(value);
    };
    dlg = openDlg(html, { id, onClose: () => finish(allowCancel ? false : true) });
    const okBtn = dlg.box.querySelector("#dlg-ok");
    okBtn.onclick = () => finish(true);
    const cancel = dlg.box.querySelector("#dlg-cancel");
    if (cancel) cancel.onclick = () => finish(false);
    dlg.box.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.isComposing && !e.target.matches("textarea")) { e.preventDefault(); finish(true); }
    });
    okBtn.focus();
  });
}

// 站内输入框：Promise<string|null>，取消返回 null
function promptDlg(title, value, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    const id = "dlg-title-" + (++dlgSeq);
    const html = `<h3 id="${id}">${esc(title)}</h3>
      <label class="f" for="dlg-input">${esc(opts.label || "输入内容")}</label>
      <input type="text" id="dlg-input" value="${esc(value == null ? "" : value)}" placeholder="${esc(opts.placeholder || "")}" autofocus>
      ${dlgActions(opts.okText || "确定", opts.cancelText || "取消", false)}`;
    let settled = false;
    let dlg;
    const finish = (val) => {
      if (settled) return;
      settled = true;
      dlg.close();
      resolve(val);
    };
    dlg = openDlg(html, { id, onClose: () => finish(null) });
    const input = dlg.box.querySelector("#dlg-input");
    dlg.box.querySelector("#dlg-ok").onclick = () => finish(input.value);
    dlg.box.querySelector("#dlg-cancel").onclick = () => finish(null);
    dlg.box.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); finish(input.value); }
    });
    input.focus();
    input.select();
  });
}

// ---------------------------------------------------------------- 可访问性
// 页面几乎全部由模板字符串动态渲染，控件命名不逐处硬编码：
// 渲染后统一把相邻的 <label class="f"> 建立 for/id 关联，并给仍无名的控件补 aria-label。
const A11Y_SKIP_TYPES = new Set(["hidden", "submit", "button", "reset", "image"]);
const A11Y_CTRL_SELECTOR = "input, select, textarea";
let a11ySeq = 0;

function a11yText(el) {
  return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
}

function a11yOwnLabel(el) {
  if (el.closest("label")) return true;
  if (el.getAttribute("aria-label") || el.getAttribute("aria-labelledby")) return true;
  if (!el.id) return false;
  return !!document.querySelector(`label[for="${el.id.replace(/"/g, '\\"')}"]`);
}

function a11ySiblingLabel(el) {
  const parent = el.parentElement;
  if (!parent) return null;
  for (const child of Array.from(parent.children)) {
    // 跳过包裹了其他控件的 label，否则会把复选框的说明文字错绑给旁边的输入框
    if (child === el || child.tagName !== "LABEL" || child.contains(el)) continue;
    if (child.querySelector(A11Y_CTRL_SELECTOR)) continue;
    if (a11yText(child)) return child;
  }
  return null;
}

function a11yHeading(el) {
  const card = el.closest(".card, .dlg, .panel");
  const h = card && card.querySelector("h2, h3, h4");
  return h ? a11yText(h) : "";
}

function enhanceA11y(root) {
  const scope = root || document;
  const nodes = scope.matches && scope.matches(A11Y_CTRL_SELECTOR)
    ? [scope] : Array.from(scope.querySelectorAll(A11Y_CTRL_SELECTOR));
  for (const el of nodes) {
    if (el.tagName === "INPUT" && A11Y_SKIP_TYPES.has((el.type || "").toLowerCase())) continue;
    if (a11yOwnLabel(el)) continue;
    const label = a11ySiblingLabel(el);
    if (label) {
      if (!el.id) el.id = "a11y-ctrl-" + (++a11ySeq);
      label.htmlFor = el.id;
      continue;
    }
    const fallback = el.getAttribute("placeholder") || el.getAttribute("title") ||
      (el.tagName === "SELECT" ? "选择项" : "输入项");
    const heading = a11yHeading(el);
    el.setAttribute("aria-label", heading ? heading + " - " + fallback : fallback);
    // 无可见标签的表单控件再补 title，鼠标用户也能看到用途
    if (!el.getAttribute("title") && el.tagName !== "SELECT") el.setAttribute("title", fallback);
  }
}

// 跳转链接只移动焦点，不改 hash（hash 被 SPA 路由占用）
document.addEventListener("click", (e) => {
  const skip = e.target.closest && e.target.closest(".skip-link");
  if (!skip) return;
  e.preventDefault();
  const main = document.getElementById("app");
  if (main) main.focus();
});

// ---------------------------------------------------------------- 自绘下拉
// 原生 <select> 的弹出层由系统绘制：方角、无阴影的灰白列表，与站内的卡片、
// 圆角和设计令牌完全脱节，这就是「下拉框很生硬」的来源。
// 保留原生 select 本身（键盘、表单、无障碍不变），只在它上面盖一层自绘触发器，
// 展开时用浮层列出同一份 option。写入一律回到原生控件，因此既有代码里对
// .value / .options / onchange 的依赖全部无需改动。
const SEL_MAX_ITEMS = 300;
let _selSeq = 0;
let _openSel = null;

function selEnhance(root) {
  const scope = root || document;
  const list = scope.matches && scope.matches("select") ? [scope]
    : Array.from(scope.querySelectorAll("select"));
  for (const el of list) {
    if (el.dataset.selUi) continue;
    if (!el.isConnected) continue;
    // 多选做「标签 + 勾选浮层」：原生 multiple 列表框要按住 Ctrl 才能多选，
    // 用户几乎每次都会把已选的项点掉。
    if (el.multiple) mselMount(el);
    else selMount(el);
  }
}

function selMount(el) {
  const host = document.createElement("div");
  host.className = "sel";
  if (el.id) host.dataset.for = el.id;
  const cssW = el.style.width, cssMax = el.style.maxWidth, cssMin = el.style.minWidth;
  host.style.width = cssW;
  if (cssMax) host.style.maxWidth = cssMax;
  if (cssMin) host.style.minWidth = cssMin;
  el.parentNode.insertBefore(host, el);
  host.appendChild(el);
  el.classList.add("sel-native");
  el.dataset.selUi = "1";
  el.tabIndex = -1;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "sel-trigger";
  btn.setAttribute("aria-haspopup", "listbox");
  btn.setAttribute("aria-expanded", "false");
  if (el.id) btn.id = "sel-btn-" + el.id;
  host.insertBefore(btn, el);
  selSync(el);
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    if (_openSel && _openSel.sel === el) selClose(true);
    else selOpen(el);
  });
  btn.addEventListener("keydown", (e) => { selKeyNav(el, e); });
  el.addEventListener("change", () => selSync(el));
  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(() => { selSync(el); }).observe(
      el, { childList: true, subtree: true, characterData: true });
  }
  el.addEventListener("focus", () => { const b = selTrigger(el); if (b) b.focus(); });
  // 既有代码大量直接写 $("#x").value = ... / selectedIndex = ...，这类赋值不会
  // 触发 change，触发器会停在旧值。在实例上挂一层写入钩子，让显示始终跟随真实值。
  const proto = Object.getPrototypeOf(el);
  for (const prop of ["value", "selectedIndex"]) {
    const desc = Object.getOwnPropertyDescriptor(proto, prop);
    if (!desc || !desc.set) continue;
    Object.defineProperty(el, prop, {
      configurable: true,
      enumerable: false,
      get() { return desc.get.call(el); },
      set(v) { desc.set.call(el, v); selSync(el); }
    });
  }
}

function selTrigger(el) {
  const prev = el.previousElementSibling;
  return prev && prev.classList.contains("sel-trigger") ? prev : null;
}

function selSync(el) {
  const btn = selTrigger(el);
  if (!btn) return;
  const opt = el.options[el.selectedIndex] || null;
  const text = opt ? opt.textContent.trim() : "";
  btn.innerHTML = `<span class="sel-value">${esc(text || "请选择")}</span>` +
    `<span class="sel-caret" aria-hidden="true">▾</span>`;
  btn.title = text;
  btn.classList.toggle("is-placeholder", !opt || opt.value === "");
  // 代码里常见的 el.disabled = true 要能反映到自绘触发器上
  btn.disabled = !!el.disabled;
  btn.closest(".sel").classList.toggle("is-disabled", !!el.disabled);
  const label = selLabelText(el);
  btn.setAttribute("aria-label", label ? `${label}：${text}` : text);
}

// 借用原生控件已经算好的可访问名称：label / aria-label / 旁边的文字
function selLabelText(el) {
  if (el.id) {
    const forLabel = document.querySelector(`label[for="${el.id.replace(/"/g, '\"')}"]`);
    if (forLabel && forLabel.textContent.trim()) return forLabel.textContent.trim();
  }
  const aria = el.getAttribute("aria-label");
  if (aria) return aria;
  const wrap = el.closest("label");
  if (wrap && wrap.textContent.trim()) return wrap.textContent.trim();
  const prev = el.previousElementSibling;
  if (prev && prev.tagName === "LABEL" && prev.textContent.trim()) return prev.textContent.trim();
  return "";
}

// 触发器上的方向键直接改原生选中项，和原生 select 的手感一致
function selKeyNav(el, e) {
  const keys = ["ArrowDown", "ArrowUp", "Home", "End"];
  if (!keys.includes(e.key)) return;
  e.preventDefault();
  const before = el.selectedIndex;
  if (e.key === "ArrowDown") el.selectedIndex = Math.min(el.options.length - 1, before + 1);
  else if (e.key === "ArrowUp") el.selectedIndex = Math.max(0, before - 1);
  else if (e.key === "Home") el.selectedIndex = 0;
  else el.selectedIndex = el.options.length - 1;
  if (el.selectedIndex !== before) {
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }
}

// ---------------------------------------------------------------- 多选标签
// 原生 <select multiple> 是需要按住 Ctrl 才能多选的列表框：点第二张图会把
// 第一张取消，用户几乎每次都会踩。这里改为「已选标签 + 勾选浮层」，原生控件
// 仍留在 DOM 里负责维护 selected 状态，既有 `option:checked` 取值代码不变。
let _openMulti = null;

function mselTrigger(el) {
  const prev = el.previousElementSibling;
  return prev && prev.classList.contains("msel-trigger") ? prev : null;
}

function mselMount(el) {
  const host = document.createElement("div");
  host.className = "msel";
  if (el.id) host.dataset.for = el.id;
  el.parentNode.insertBefore(host, el);
  host.appendChild(el);
  el.classList.add("sel-native");
  el.dataset.selUi = "1";
  // size 会在视觉隐藏后继续撑出高度，去掉后由自绘触发器决定高度
  el.removeAttribute("size");
  el.tabIndex = -1;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "msel-trigger";
  btn.setAttribute("aria-haspopup", "listbox");
  btn.setAttribute("aria-expanded", "false");
  if (el.id) btn.id = "msel-btn-" + el.id;
  host.insertBefore(btn, el);
  mselSync(el);
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    if (_openMulti && _openMulti.sel === el) mselClose(true);
    else mselOpen(el);
  });
  btn.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      mselOpen(el);
    }
  });
  el.addEventListener("change", () => mselSync(el));
  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(() => mselSync(el)).observe(
      el, { childList: true, subtree: true, characterData: true,
            attributes: true, attributeFilter: ["selected", "disabled"] });
  }
  el.addEventListener("focus", () => { const b = mselTrigger(el); if (b) b.focus(); });
}

function mselPicked(el) {
  return Array.from(el.options).filter((o) => o.selected && !o.disabled);
}

function mselSync(el) {
  const btn = mselTrigger(el);
  if (!btn) return;
  const picked = mselPicked(el);
  // 只显示前 3 个标签，其余收成 +N：长文件名会把整行撑爆
  const head = picked.slice(0, 3).map((o) => {
    const text = o.textContent.trim();
    return `<span class="msel-chip" title="${esc(text)}">${esc(text)}</span>`;
  }).join("");
  const rest = picked.length > 3 ? `<span class="msel-chip more">+${picked.length - 3}</span>` : "";
  const body = head + rest || `<span class="msel-empty">未选择</span>`;
  btn.innerHTML = `<span class="msel-values">${body}</span>` +
    `<span class="msel-count">${picked.length || ""}</span>` +
    `<span class="sel-caret" aria-hidden="true">▾</span>`;
  btn.title = picked.map((o) => o.textContent.trim()).join("、");
  btn.disabled = !!el.disabled;
  btn.closest(".msel").classList.toggle("is-disabled", !!el.disabled);
  const label = selLabelText(el);
  btn.setAttribute("aria-label", label ? `${label}：已选 ${picked.length} 项` : `已选 ${picked.length} 项`);
}

function selItems(el) {
  return Array.from(el.options).map((o, i) => ({
    i, value: o.value, text: o.textContent.trim(), disabled: o.disabled,
    group: (o.parentElement && o.parentElement.tagName === "OPTGROUP") ? o.parentElement.label : ""
  }));
}

function selOpen(el) {
  const btn = selTrigger(el);
  if (!btn) return;
  selClose(false);
  const pop = document.createElement("div");
  pop.className = "sel-pop";
  pop.id = "sel-pop-" + (++_selSeq);
  pop.setAttribute("role", "listbox");
  pop.setAttribute("aria-label", selLabelText(el) || "选项");
  const all = selItems(el);
  // 选项数量来自全部提示词 / 模型站点时可能上百：只有真正需要才给搜索框，
  // 3 个选项还让人打字是负担。
  const needSearch = all.length > 8;
  const rows = all.slice(0, SEL_MAX_ITEMS);
  let html = "", lastGroup = null, active = Math.max(0, el.selectedIndex);
  for (const it of rows) {
    if (it.group && it.group !== lastGroup) {
      html += `<div class="sel-group">${esc(it.group)}</div>`;
      lastGroup = it.group;
    }
    const on = it.i === el.selectedIndex;
    html += `<div class="sel-opt${on ? " active" : ""}${it.disabled ? " disabled" : ""}"` +
      ` role="option" id="${pop.id}-o${it.i}" data-i="${it.i}" aria-selected="${on}"` +
      `${it.disabled ? ' aria-disabled="true"' : ""}>${esc(it.text || "（空）")}</div>`;
  }
  const rest = all.length - rows.length;
  pop.innerHTML =
    (needSearch ? `<input type="search" class="sel-search" aria-label="${esc(selLabelText(el) || "选项")}搜索"` +
      ` placeholder="搜索…" autocomplete="off" spellcheck="false">` : "") +
    `<div class="sel-list">${html || `<div class="sel-empty">没有可选项</div>`}` +
    `${rest > 0 ? `<div class="sel-more">还有 ${rest} 个，输入关键字筛选</div>` : ""}</div>`;
  btn.parentNode.appendChild(pop);
  btn.setAttribute("aria-expanded", "true");
  btn.setAttribute("aria-controls", pop.id);
  _openSel = { sel: el, pop, btn, active };
  selPopPosition(btn, pop);
  const search = pop.querySelector(".sel-search");
  if (search) {
    search.addEventListener("input", () => selFilter(search.value));
    search.addEventListener("keydown", selPopKey);
    search.focus();
  }
  pop.addEventListener("click", (e) => {
    const row = e.target.closest(".sel-opt");
    if (!row || row.classList.contains("disabled")) return;
    selPick(el, Number(row.dataset.i));
  });
  pop.addEventListener("mousemove", (e) => {
    const row = e.target.closest(".sel-opt");
    if (row && !row.classList.contains("disabled")) selMarkActive(Number(row.dataset.i));
  });
  document.addEventListener("mousedown", selOutside, true);
  window.addEventListener("resize", selReposition);
  // 页面滚动时跟随触发器重新定位。用 passive 监听，避免拖动主滚动条时卡顿。
  window.addEventListener("scroll", selReposition, { capture: true, passive: true });
  const act = pop.querySelector(".sel-opt.active");
  if (act && act.scrollIntoView) act.scrollIntoView({ block: "nearest" });
}

function selReposition() {
  // 单选与多选共用一个定位函数：只认 _openSel 会让多选浮层在滚动后卡在原地。
  const open = _openSel || _openMulti;
  if (open) selPopPosition(open.btn, open.pop);
}

function mselOpen(el) {
  const btn = mselTrigger(el);
  if (!btn) return;
  mselClose(false);
  const pop = document.createElement("div");
  pop.className = "sel-pop msel-pop";
  pop.id = "msel-pop-" + (++_selSeq);
  pop.setAttribute("role", "listbox");
  pop.setAttribute("aria-multiselectable", "true");
  pop.setAttribute("aria-label", selLabelText(el) || "选项");
  pop.innerHTML =
    `<div class="msel-head"><span class="msel-head-text">可多选</span>` +
    `<button type="button" class="msel-link" data-act="all">全选</button>` +
    `<button type="button" class="msel-link" data-act="none">清空</button></div>` +
    `<div class="sel-list msel-list"></div>` +
    `<div class="msel-foot"><button type="button" class="btn small primary" data-act="done">完成</button></div>`;
  btn.parentNode.appendChild(pop);
  btn.setAttribute("aria-expanded", "true");
  btn.setAttribute("aria-controls", pop.id);
  // 默认焦点放在浮层上，方向键可直接在列表里移动
  pop.tabIndex = -1;
  // 记录打开时的选择快照：关闭时只有真的变了才广播 change，
  // 否则点开又点掉会把下游的「已选 N 张」重复刷新一遍。
  _openMulti = { sel: el, pop, btn, sig: mselSig(el) };
  mselRenderList(el);
  selPopPosition(btn, pop);
  pop.addEventListener("click", (e) => {
    const act = e.target.closest("[data-act]");
    if (act) {
      const kind = act.dataset.act;
      if (kind === "all") mselSetAll(el, true);
      else if (kind === "none") mselSetAll(el, false);
      else mselDone(el);
      return;
    }
    const row = e.target.closest(".msel-opt");
    if (!row || row.classList.contains("disabled")) return;
    mselToggle(el, Number(row.dataset.i));
  });
  pop.addEventListener("keydown", mselPopKey);
  document.addEventListener("mousedown", mselOutside, true);
  window.addEventListener("resize", selReposition);
  window.addEventListener("scroll", selReposition, { capture: true, passive: true });
  const search = pop.querySelector(".msel-search");
  (search || pop).focus();
}

// 图片集可能有上千张图：超过 10 项才给搜索框
function mselRenderList(el) {
  if (!_openMulti) return;
  const pop = _openMulti.pop;
  const list = pop.querySelector(".msel-list");
  const all = selItems(el);
  const picked = new Set(mselPicked(el).map((o) => o.value));
  if (all.length > 10 && !pop.querySelector(".msel-search")) {
    const input = document.createElement("input");
    input.type = "search";
    input.className = "sel-search msel-search";
    input.placeholder = "搜索…";
    input.setAttribute("aria-label", "搜索选项");
    input.autocomplete = "off";
    input.addEventListener("input", () => mselFilter(input.value));
    input.addEventListener("keydown", mselPopKey);
    pop.insertBefore(input, list);
  }
  list.innerHTML = all.slice(0, SEL_MAX_ITEMS).map((it) => {
    const on = picked.has(it.value);
    return `<div class="msel-opt${on ? " checked" : ""}${it.disabled ? " disabled" : ""}"` +
      ` role="option" aria-selected="${on}" data-i="${it.i}" data-text="${esc(it.text)}">` +
      `<span class="msel-box" aria-hidden="true">${on ? "✓" : ""}</span>` +
      `<span class="msel-text">${esc(it.text || "（空）")}</span></div>`;
  }).join("") || `<div class="sel-empty">没有可选项</div>`;
  const first = list.querySelector(".msel-opt");
  if (first) first.classList.add("active");
  if (pop.querySelector(".msel-search")) {
    pop.querySelector(".msel-search").focus();
  }
}

function mselFilter(q) {
  if (!_openMulti) return;
  q = (q || "").trim().toLowerCase();
  _openMulti.pop.querySelectorAll(".msel-opt").forEach((n) => {
    n.hidden = !!q && !n.dataset.text.toLowerCase().includes(q);
  });
}

function mselToggle(el, idx) {
  const opt = el.options[idx];
  if (!opt || opt.disabled) return;
  opt.selected = !opt.selected;
  // 只改这一行，不重建整个列表：重建会把正在点击的节点换掉，
  // 连续快速点选时后续点击会落在已卸载的 DOM 上而丢失。
  mselSync(el);
  if (_openMulti && _openMulti.sel === el) {
    const row = _openMulti.pop.querySelector(`.msel-opt[data-i="${idx}"]`);
    if (row) {
      const on = opt.selected;
      row.classList.toggle("checked", on);
      row.setAttribute("aria-selected", on ? "true" : "false");
      const box = row.querySelector(".msel-box");
      if (box) box.textContent = on ? "✓" : "";
    }
  }
}

function mselSetAll(el, on) {
  Array.from(el.options).forEach((o) => { if (!o.disabled) o.selected = on; });
  mselRefresh(el);
}

// 勾选即时写回原生控件；change 统一在关闭时按打开快照判重后广播一次，
// 避免「全选/清空」先报一次、点「完成」又报一次。
function mselRefresh(el) {
  mselSync(el);
  if (_openMulti && _openMulti.sel === el) {
    const box = _openMulti.pop.querySelector(".msel-search");
    const q = box ? box.value : "";
    mselRenderList(el);
    if (q) mselFilter(q);
  }
}

function mselPopKey(e) {
  if (!_openMulti) return;
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); mselDone(_openMulti.sel); return; }
  if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
  e.preventDefault();
  const rows = [..._openMulti.pop.querySelectorAll(".msel-opt")].filter((n) => !n.hidden);
  if (!rows.length) return;
  const cur = rows.findIndex((n) => n.classList.contains("active"));
  const next = e.key === "ArrowDown"
    ? Math.min(rows.length - 1, cur + 1)
    : Math.max(0, cur - 1);
  rows.forEach((n) => n.classList.remove("active"));
  rows[next].classList.add("active");
  rows[next].scrollIntoView({ block: "nearest" });
}

function mselDone(el) {
  mselClose(true);
}

function mselSig(el) {
  return Array.from(el.options).map((o) => (o.selected ? "1" : "0")).join("");
}

function mselClose(focusBack) {
  if (!_openMulti) return;
  const { pop, btn, sel, sig } = _openMulti;
  const changed = sig !== mselSig(sel);
  btn.setAttribute("aria-expanded", "false");
  pop.remove();
  document.removeEventListener("mousedown", mselOutside, true);
  window.removeEventListener("resize", selReposition);
  window.removeEventListener("scroll", selReposition, { capture: true, passive: true });
  _openMulti = null;
  if (focusBack) btn.focus();
  if (changed) sel.dispatchEvent(new Event("change", { bubbles: true }));
}

function mselOutside(e) {
  if (!_openMulti) return;
  if (_openMulti.pop.contains(e.target) || _openMulti.btn.contains(e.target)) return;
  mselClose(false);
}

// 默认向下展开；下方放不下且上方更宽松时翻到上方，避免浮层被视口裁掉
function selPopPosition(btn, pop) {
  const r = btn.getBoundingClientRect();
  // 触发器可能只有 160px，而选项是「示例项目 / 防溺水-水边人员检测」这种长文本。
  // 浮层按内容自然宽度展开（不低于触发器宽、不超过 420 与视口），避免全部被截断。
  pop.style.width = "max-content";
  const natural = pop.scrollWidth || r.width;
  pop.style.width = "";
  // 多选触发器常是整行宽（卡片里 width:100%），但浮层不需要跟着铺满：
  // 420px 足够放下「勾选框 + 文件名」，再宽只会变成一块空白的白板。
  const isMulti = pop.classList.contains("msel-pop");
  const cap = Math.min(420, window.innerWidth - 16);
  const base = isMulti ? Math.max(280, Math.min(Math.round(r.width), cap)) : Math.round(r.width);
  const want = isMulti ? base : Math.max(base, Math.min(natural, cap));
  pop.style.minWidth = base + "px";
  pop.style.width = Math.round(want) + "px";
  const popH = pop.offsetHeight || 240;
  const below = window.innerHeight - r.bottom - 12;
  const up = popH > below && (r.top - 12) > below;
  pop.classList.toggle("up", up);
  if (up) pop.style.bottom = Math.round(window.innerHeight - r.top + 6) + "px";
  else pop.style.top = Math.round(r.bottom + 6) + "px";
  const w = pop.offsetWidth || want;
  pop.style.left = Math.round(Math.max(8, Math.min(r.left, window.innerWidth - w - 8))) + "px";
}

function selMarkActive(idx) {
  if (!_openSel) return;
  _openSel.active = idx;
  _openSel.pop.querySelectorAll(".sel-opt").forEach((n) => {
    n.classList.toggle("active", Number(n.dataset.i) === idx);
  });
  const act = _openSel.pop.querySelector(".sel-opt.active");
  if (act && act.scrollIntoView) act.scrollIntoView({ block: "nearest" });
}

function selFilter(q) {
  if (!_openSel) return;
  q = (q || "").trim().toLowerCase();
  const pop = _openSel.pop;
  pop.querySelectorAll(".sel-opt").forEach((n) => {
    n.hidden = !!q && !n.textContent.toLowerCase().includes(q);
  });
  // 分组标题没有可见子项时一起隐藏，避免只剩一串空标题
  pop.querySelectorAll(".sel-group").forEach((g) => {
    let n = g.nextElementSibling, any = false;
    while (n && !n.classList.contains("sel-group")) {
      if (n.classList.contains("sel-opt") && !n.hidden) { any = true; break; }
      n = n.nextElementSibling;
    }
    g.hidden = !any;
  });
  const visible = [...pop.querySelectorAll(".sel-opt")].filter((n) => !n.hidden);
  if (visible.length) selMarkActive(Number(visible[0].dataset.i));
}

function selPopKey(e) {
  if (!_openSel) return;
  const pop = _openSel.pop;
  const visible = [...pop.querySelectorAll(".sel-opt")]
    .filter((n) => !n.hidden && !n.classList.contains("disabled"));
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); selClose(true); return; }
  if (!visible.length) return;
  if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
    e.preventDefault();
    const cur = visible.findIndex((n) => Number(n.dataset.i) === _openSel.active);
    let next = 0;
    if (e.key === "End") next = visible.length - 1;
    else if (e.key === "ArrowDown") next = cur < 0 ? 0 : Math.min(visible.length - 1, cur + 1);
    else if (e.key === "ArrowUp") next = cur < 0 ? visible.length - 1 : Math.max(0, cur - 1);
    selMarkActive(Number(visible[next].dataset.i));
    return;
  }
  if (e.key === "Enter") { e.preventDefault(); selPick(_openSel.sel, _openSel.active); }
}

function selPick(el, idx) {
  const opt = el.options[idx];
  if (!opt || opt.disabled) return;
  const before = el.value;
  el.selectedIndex = idx;
  selClose(true);
  // 与原生一致：值真的变了才派发 change，避免重复触发查询/新建
  if (el.value !== before) {
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }
  selSync(el);
}

function selClose(focusBack) {
  if (!_openSel) return;
  const { pop, btn } = _openSel;
  btn.setAttribute("aria-expanded", "false");
  pop.remove();
  document.removeEventListener("mousedown", selOutside, true);
  window.removeEventListener("resize", selReposition);
  window.removeEventListener("scroll", selReposition, { capture: true, passive: true });
  _openSel = null;
  if (focusBack) btn.focus();
}

function selOutside(e) {
  if (!_openSel) return;
  if (_openSel.pop.contains(e.target) || _openSel.btn.contains(e.target)) return;
  selClose(false);
}

// ---------------------------------------------------------------- 输入建议
// `<input list="...">` 的候选框由浏览器绘制：方角、无令牌、暗色下是黑块，
// 和站内自绘下拉完全不是一套视觉语言。这里改成「文本输入 + 自绘建议浮层」，
// 关键差别是「可自由输入」——分组允许新建，所以不能退化成只读的 select。
let _openSuggest = null;

function sugOptions(input) {
  try { return JSON.parse(input.dataset.suggest || "[]"); } catch (e) { return []; }
}

function sugFiltered(input) {
  const q = (input.value || "").trim().toLowerCase();
  return sugOptions(input).filter((v) => !q || v.toLowerCase().includes(q));
}

function sugOpen(input) {
  const opts = sugFiltered(input);
  if (!opts.length) { sugClose(); return; }
  sugClose();
  const pop = document.createElement("div");
  pop.className = "sel-pop sug-pop";
  pop.id = "sug-pop-" + (++_selSeq);
  pop.setAttribute("role", "listbox");
  pop.innerHTML = `<div class="sel-list">${opts.map((v, i) =>
    `<div class="sel-opt sug-opt" role="option" data-i="${i}" data-value="${esc(v)}">${esc(v)}</div>`).join("")}</div>`;
  document.body.appendChild(pop);
  input.setAttribute("aria-expanded", "true");
  input.setAttribute("aria-controls", pop.id);
  _openSuggest = { input, pop, active: 0, moved: false };
  sugMark(0);
  selPopPosition(input, pop);
  window.addEventListener("resize", sugReposition);
  window.addEventListener("scroll", sugReposition, { capture: true, passive: true });
  document.addEventListener("mousedown", sugOutside, true);
}

function sugReposition() {
  if (_openSuggest) selPopPosition(_openSuggest.input, _openSuggest.pop);
}

function sugMark(i) {
  if (!_openSuggest) return;
  const rows = [..._openSuggest.pop.querySelectorAll(".sug-opt")];
  if (!rows.length) return;
  const idx = Math.max(0, Math.min(i, rows.length - 1));
  _openSuggest.active = idx;
  rows.forEach((n, j) => n.classList.toggle("active", j === idx));
  if (arguments.length && i !== 0) _openSuggest.moved = true;
  rows[idx].scrollIntoView({ block: "nearest" });
}

function sugPick(input, value) {
  input.value = value;
  sugClose();
  input.focus();
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function sugClose() {
  if (!_openSuggest) return;
  const { pop, input } = _openSuggest;
  pop.remove();
  input.setAttribute("aria-expanded", "false");
  input.removeAttribute("aria-controls");
  window.removeEventListener("resize", sugReposition);
  window.removeEventListener("scroll", sugReposition, { capture: true, passive: true });
  document.removeEventListener("mousedown", sugOutside, true);
  _openSuggest = null;
}

function sugOutside(e) {
  if (!_openSuggest) return;
  if (_openSuggest.pop.contains(e.target) || _openSuggest.input.contains(e.target)) return;
  sugClose();
}

function sugEnhance(root) {
  const scope = root || document;
  const list = scope.matches && scope.matches("input[data-suggest]") ? [scope]
    : Array.from(scope.querySelectorAll("input[data-suggest]"));
  for (const input of list) {
    if (input.dataset.sugUi) continue;
    if (!input.isConnected) continue;
    input.dataset.sugUi = "1";
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.addEventListener("focus", () => sugOpen(input));
    input.addEventListener("input", () => sugOpen(input));
    input.addEventListener("keydown", (e) => {
      if (!_openSuggest || _openSuggest.input !== input) {
        if (e.key === "ArrowDown") { e.preventDefault(); sugOpen(input); }
        return;
      }
      const rows = [..._openSuggest.pop.querySelectorAll(".sug-opt")];
      if (e.key === "ArrowDown") { e.preventDefault(); sugMark(_openSuggest.active + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sugMark(_openSuggest.active - 1); }
      else if (e.key === "Enter") {
        // 只有用户主动在列表里移动过，回车才采纳建议；否则保留其输入的新分组
        if (_openSuggest.moved && rows[_openSuggest.active]) {
          e.preventDefault();
          sugPick(input, rows[_openSuggest.active].dataset.value);
        } else sugClose();
      } else if (e.key === "Escape") { e.preventDefault(); sugClose(); }
    });
    input.addEventListener("blur", () => setTimeout(() => {
      if (_openSuggest && _openSuggest.input === input) sugClose();
    }, 120));
  }
}

function setupSuggest() {
  document.addEventListener("click", (e) => {
    const row = e.target.closest && e.target.closest(".sug-opt");
    if (!row || !_openSuggest) return;
    sugPick(_openSuggest.input, row.dataset.value);
  });
}

// 初始挂载：脚本在 body 末尾执行，此时静态 DOM 已就绪
selEnhance(document);
sugEnhance(document);
setupSuggest();

// 只观察结构变化（不观察属性），避免补名称时自身触发循环
if (typeof MutationObserver !== "undefined") {
  let a11yTimer = null;
  new MutationObserver(() => {
    if (a11yTimer) return;
    // 原生 select 的升级与补无障碍名称同一批次执行：两者都是"结构变了再补",
    // 分两个定时器会让同一页重排两次。
    a11yTimer = setTimeout(() => {
      a11yTimer = null;
      enhanceA11y(document);
      selEnhance(document);
      sugEnhance(document);
    }, 0);
  }).observe(document.documentElement, { childList: true, subtree: true });
}

// 进度：processed 为已处理条数（含失败），显示「已处理/总数 · 百分比」并标出失败数
function progressBar(processed, total, failed, parseFailed) {
  processed = Number(processed) || 0; total = Number(total) || 0;
  failed = Number(failed) || 0; parseFailed = Number(parseFailed) || 0;
  const pct = total ? Math.min(100, Math.max(0, Math.round(processed / total * 100))) : 0;
  // 「调用失败」和「解析失败」是两个不同口径：前者接口没返回，后者接口返回了但 JSON 读不出来。
  // 混成一个数字会让用户看到「有图没结论，但失败数是 0」。
  return `<div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="进度 ${pct}%，已处理 ${processed}/${total}">
      <i style="width:${pct}%"></i></div>
    <span class="progress-text" aria-hidden="true">${processed}/${total} · ${pct}%</span>
    ${failed ? `<span class="tag red">调用失败 ${failed}</span>` : ""}
    ${parseFailed ? `<span class="tag orange">解析失败 ${parseFailed}</span>` : ""}`;
}
function statusTag(s) {
  const map = {
    pending: ["等待", ""], running: ["运行中", "blue"], done: ["完成", "green"],
    stopped: ["已停止", "orange"], interrupted: ["已中断", "orange"], failed: ["失败", "red"],
    paused: ["已暂停", "orange"], waiting_for_review: ["等待人工审核", "orange"], waiting_for_judge: ["等待裁判补齐", "orange"],
    stable: ["性能稳定", "green"], done_with_errors: ["完成（有失败项）", "orange"],
    "正确": ["正确", "green"], "误报": ["误报", "red"], "漏报": ["漏报", "red"],
    "部分正确": ["部分正确", "orange"], "无法判断": ["无法判断", "blue"],
    abnormal: ["abnormal", "red"], normal: ["normal", "green"], error: ["error", "red"],
  };
  const [t, c] = map[s] || [s || "未填写", "blue"];
  return `<span class="tag ${c}">${esc(t)}</span>`;
}

function statusDotClass(s) {
  const v = String(s == null ? "" : s).toLowerCase();
  if (["abnormal", "异常", "违规", "报警", "不合格", "是", "true", "1"].includes(v)) return "red";
  if (["normal", "正常", "合格", "否", "false", "0"].includes(v)) return "green";
  return "blue";
}

// ---------------------------------------------------------------- 站点/模型选择器
// 多站点配置下，所有模型下拉统一用「站点::模型」作为值，按站点分组显示
function smOptions(cfg, selectedSite, selectedModel) {
  const sites = (cfg.api && cfg.api.sites) || [];
  const selVal = selectedSite ? `${selectedSite}::${selectedModel}` : "";
  const defVal = `${cfg.defaults.site}::${cfg.defaults.model}`;
  return sites.map(s => `<optgroup label="${esc(s.name)}">${(s.models || []).map(m => {
    const v = `${s.name}::${m}`;
    const sel = selVal ? v === selVal : v === defVal;
    return `<option value="${esc(v)}" ${sel ? "selected" : ""}>${esc(m)}</option>`;
  }).join("")}</optgroup>`).join("");
}
function smParse(v) {
  const i = (v || "").indexOf("::");
  if (i < 0) return { site: "", model: v || "" };
  return { site: v.slice(0, i), model: v.slice(i + 2) };
}
function smValue(cfg) {
  return `${cfg.defaults.site}::${cfg.defaults.model}`;
}
function smOptionsFromValue(cfg, value) {
  const parsed = smParse(value);
  return smOptions(cfg, parsed.site, parsed.model);
}

const PAI_NEW_MODEL_KEY = "mmtest.pai.newModel";
const PAI_NEW_PROFILE_KEY = "mmtest.pai.newProfile";
const PAI_LAST_SESSION_KEY = "mmtest.pai.lastSession";

function smValidValue(cfg, value) {
  const parsed = smParse(value);
  const site = ((cfg.api && cfg.api.sites) || []).find(s => s.name === parsed.site);
  if (site && (site.models || []).includes(parsed.model)) return `${site.name}::${parsed.model}`;
  return smValue(cfg);
}
function storedSmValue(cfg, key) {
  try { return smValidValue(cfg, localStorage.getItem(key) || ""); }
  catch (e) { return smValue(cfg); }
}
function saveSmValue(key, value) {
  try { localStorage.setItem(key, value); } catch (e) {}
}
function storedPaiProfileName(profiles) {
  try {
    const name = localStorage.getItem(PAI_NEW_PROFILE_KEY) || "";
    return profiles.some(p => p.name === name) ? name : "";
  } catch (e) {
    return "";
  }
}
function paiChatModelKey(sessionId) {
  return `mmtest.pai.chatModel.${sessionId}`;
}
function paiChatModelValue(cfg, session, sessionId) {
  let stored = "";
  try { stored = localStorage.getItem(paiChatModelKey(sessionId)) || ""; } catch (e) {}
  if (stored) return smValidValue(cfg, stored);
  if (session && session.site && session.model) {
    const value = `${session.site}::${session.model}`;
    if (value === smValidValue(cfg, value)) return value;
  }
  return smValue(cfg);
}

const PROMPT_SECTIONS = [
  ["role", "ROLE / 角色人设"], ["task", "TASK / 任务目标"],
  ["definition", "DEFINITION / 判定定义"], ["workflow", "WORKFLOW / 视觉思维链"],
  ["output_format", "OUTPUT FORMAT / 输出格式约束"],
];

function composePromptSections(sections) {
  return PROMPT_SECTIONS.map(([key, title]) => `## ${title}\n${String(sections[key] || "").trim()}`).join("\n\n") + "\n";
}

// ---------------------------------------------------------------- 路由
const routes = {};
let pollTimer = null;
let pageTimers = [];

function route(path, fn) { routes[path] = fn; }

function schedulePagePoll(fn, delay) {
  const timer = setTimeout(() => {
    pageTimers = pageTimers.filter(t => t !== timer);
    fn();
  }, delay);
  pageTimers.push(timer);
  return timer;
}

function clearPageTimers() {
  if (pollTimer) {
    clearInterval(pollTimer);
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  pageTimers.forEach(t => clearTimeout(t));
  pageTimers = [];
}

// 页面级事件监听清理：路由切走后必须摘掉 window/document 上的监听，
// 否则旧页面（已从 DOM 移除）的回调会一直挂在 window 上。
let pageCleanups = [];
function onPageLeave(fn) { pageCleanups.push(fn); }
function runPageCleanups() {
  pageCleanups.forEach(fn => { try { fn(); } catch (e) {} });
  pageCleanups = [];
}

// ---------------------------------------------------------------- 主题与移动导航
const THEME_KEY = "mmtest.theme";
// 首次进入默认浅色。注意「默认值」不等于「已选择」：
// 只有用户点过开关才写 localStorage，否则 auto（跟随系统）会被永久顶掉。
const THEME_DEFAULT = "light";
const THEME_MEDIA = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function systemTheme() {
  return THEME_MEDIA && THEME_MEDIA.matches ? "dark" : "light";
}

// 存的是用户的显式选择：auto（跟随系统）/ light / dark；从未选择过则为空
function storedTheme() {
  try {
    const v = localStorage.getItem(THEME_KEY) || "";
    return v === "dark" || v === "light" || v === "auto" ? v : "";
  } catch (e) {
    return "";
  }
}

// 当前「用户选择」的模式：没有显式选择时落到默认浅色
function savedTheme() {
  return storedTheme() || THEME_DEFAULT;
}

// 当前「实际生效」的外观：auto 时跟随系统
function currentTheme() {
  const mode = savedTheme();
  return mode === "auto" ? systemTheme() : mode;
}

function syncThemeButton(mode) {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  const effective = mode === "auto" ? systemTheme() : mode;
  const toNext = effective === "dark" ? "亮色" : "暗色";
  const label = mode === "auto" ? `跟随系统（当前${effective === "dark" ? "暗色" : "亮色"}）`
    : (mode === "dark" ? "暗色" : "亮色");
  // 图标表示「点一下会变成什么」：暗色下显示太阳
  btn.textContent = effective === "dark" ? "☀" : "☾";
  btn.title = `主题：${label}（点击切换到${toNext}）`;
  btn.setAttribute("aria-label", `切换主题，当前${label}，点击切换到${toNext}`);
}

// persist 只由用户操作触发；首屏应用默认值时不落盘
function applyTheme(mode, persist) {
  const root = document.documentElement;
  if (mode === "dark" || mode === "light") {
    root.setAttribute("data-theme", mode);
    root.style.colorScheme = mode;
  } else {
    root.removeAttribute("data-theme");
    root.style.colorScheme = "";
  }
  if (persist !== false) {
    try { localStorage.setItem(THEME_KEY, mode); } catch (e) {}
  }
  syncThemeButton(mode);
}

// 点一下必定翻转外观：亮 <-> 暗。
// 旧实现是 auto -> 亮 -> 暗 -> auto 三态循环，系统本身是深色时，
// 「暗 -> auto」视觉上毫无变化，用户得连点两下才变亮，看起来像开关失灵。
function toggleTheme() {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
}

// auto 状态下系统主题变化时，同步按钮图标与提示
if (THEME_MEDIA) {
  const onSystemThemeChange = () => { if (savedTheme() === "auto") syncThemeButton("auto"); };
  if (THEME_MEDIA.addEventListener) THEME_MEDIA.addEventListener("change", onSystemThemeChange);
  else if (THEME_MEDIA.addListener) THEME_MEDIA.addListener(onSystemThemeChange);
}
applyTheme(savedTheme(), false);

// ---------------------------------------------------------------- 项目上下文
// 用户是按「一个项目里跑一条流程」工作的，但旧实现里 state.project 出现 0 次：
// 每换一页都要重新在一堆全部项目的数据里认一遍当前项目。
// 这里把「当前项目」提到全局单例，顶栏下方常驻一条上下文条，深链进入时自动回填。
const PROJECT_KEY = "mmtest.project";
const PROJECT_ALL = "";

// 这几类页面不挂在某个项目下，显示上下文条只会增加噪音
const CTX_HIDDEN_ROUTES = new Set(["config", "help", "jsontool", "profiles"]);

function savedProject() {
  try { return localStorage.getItem(PROJECT_KEY) || PROJECT_ALL; } catch (e) { return PROJECT_ALL; }
}

// 当前项目从上次会话恢复；没有记录时默认「全部项目」，不静默替用户选一个。
// 必须放在 PROJECT_ALL 声明之后：const 有暂存死区，提前读会抛 ReferenceError。
state.project = savedProject();

function currentProject() { return state.project || PROJECT_ALL; }

function setProject(name, opts) {
  opts = opts || {};
  const before = currentProject();
  state.project = name || PROJECT_ALL;
  try {
    if (state.project) localStorage.setItem(PROJECT_KEY, state.project);
    else localStorage.removeItem(PROJECT_KEY);
  } catch (e) {}
  if (before !== currentProject() && opts.rerender !== false) navigate();
}

// 深链（项目/图片集/运行结果/真值/迭代）自带归属项目：进入时把它设为当前项目，
// 否则用户从链接进来后，顶部条的「当前项目」与他正在看的内容对不上。
function adoptProjectOf(item) {
  const p = projectOf(item);
  if (p && p !== "未归档项目" && p !== currentProject()) setProject(p, { rerender: false });
}

// 统一从各种数据结构里取项目名：图片集用 project，运行用 dataset_project，
// 真值/评估只存 "项目::图片集" 的 ref。
function projectOf(item) {
  if (!item) return "";
  if (item.project != null) return item.project;
  if (item.dataset_project != null) return item.dataset_project;
  return refProject(item.dataset || item.ref || "");
}

function refProject(ref) {
  ref = String(ref || "");
  return ref.includes("::") ? ref.split("::")[0] : "未归档项目";
}

function inProject(item) {
  const p = currentProject();
  return !p || projectOf(item) === p;
}

function projectDatasets(datasets) {
  return (datasets || []).filter(inProject);
}

function projectRuns(runs) {
  return (runs || []).filter(inProject);
}

// 全局共享资源（提示词库、模型配置、模板）不属于任何项目，切换项目时
// 不能跟着过滤，否则会"数据凭空消失"。但也不能一声不吭——用一条说明条
// 告诉用户"这页不随项目切换"，避免误以为切换失效。
function sharedScopeBar(text) {
  const cur = currentProject();
  if (!cur) return "";
  return `<div class="scope-bar" role="note">
    <span class="tag blue">全站共享</span>
    <span>${esc(text)}</span>
    <span class="muted">当前项目「${esc(cur)}」只作用于图片集、运行、审核、裁判与优化。</span>
  </div>`;
}

// 页面级作用域提示：用于确实按项目收口、但用户需要一眼确认范围的页面
function projectScopeBar(text) {
  const cur = currentProject();
  if (!cur) return "";
  return `<div class="scope-bar" role="note">
    <span class="tag green">当前项目</span>
    <span>${esc(text || "以下内容只显示当前项目的记录")}</span>
  </div>`;
}

// 空态统一带下一步：只写「暂无 XX」用户不知道接着该点哪
function emptyState(text, action, hash, focus) {
  let btn = "";
  if (action && hash) btn = `<a class="btn small" href="${hash}">${esc(action)}</a>`;
  else if (action && focus) btn = `<button class="btn small" type="button" data-focus="${esc(focus)}">${esc(action)}</button>`;
  return `<div class="empty"><div class="empty-text">${esc(text)}</div>${btn}</div>`;
}

// 空态的「去填写」只聚焦页内表单，不跳页；CSP 禁止内联事件，统一走委托
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-focus]");
  if (!b) return;
  const el = document.getElementById(b.dataset.focus);
  if (!el) return;
  // 目标是按钮就直接触发（「载入模型框」「新建对话」），是输入框才聚焦
  if (el.tagName === "BUTTON") { el.click(); return; }
  el.focus();
  el.scrollIntoView({ block: "center" });
});

// 项目卡默认 href 指向项目详情；JS 可用时原地把工作台切到该项目（方案 2A）。
// 修饰键、中键保留浏览器原生「新标签打开」行为。
document.addEventListener("click", (e) => {
  const open = e.target.closest("[data-open-project]");
  if (!open) return;
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  setProject(open.dataset.openProject);
});

// 项目切换器：原生 <select> 项目一多就退化成「一条超长列表」，既不能搜也撑出屏幕。
// 这里改为「按钮 + 带搜索框的浮层」，列表固定最大高度、内部滚动，最多渲染 50 条。
const CTX_LIST_MAX = 50;
let ctxActive = 0;

function ctxProjects() {
  const list = (state._projects || []).map(p => ({
    name: p.name || p.id || "",
    sub: ctxMeta(p),
  })).filter(x => x.name);
  // 深链进入的历史/兼容项目可能不在清单里，临时补一项，否则显示成「全部项目」
  const cur = currentProject();
  if (cur && !list.some(x => x.name === cur)) list.unshift({ name: cur, sub: "" });
  return list;
}

function ctxMeta(p) {
  const d = p.dataset_count || 0, i = p.image_count || 0;
  return d || i ? `${d} 个图片集 · ${i} 张图片` : "";
}

function ctxFiltered() {
  const input = document.getElementById("ctx-search");
  const q = ((input && input.value) || "").trim().toLowerCase();
  const all = ctxProjects();
  const items = [];
  // 有搜索词时不再把「全部项目」钉在第一位：否则搜完按回车会退回全部，
  // 用户以为是自己搜到的那一项。
  const allText = `全部项目（${all.length}）`;
  if (!q || allText.toLowerCase().includes(q)) items.push({ value: "", text: allText, sub: "" });
  for (const p of all) {
    if (q && !p.name.toLowerCase().includes(q)) continue;
    items.push({ value: p.name, text: p.name, sub: p.sub, q });
  }
  return items;
}

function ctxHighlight(text, q) {
  if (!q) return esc(text);
  const idx = text.toLowerCase().indexOf(q);
  if (idx < 0) return esc(text);
  return esc(text.slice(0, idx)) + "<mark>" + esc(text.slice(idx, idx + q.length)) +
    "</mark>" + esc(text.slice(idx + q.length));
}

function ctxRenderList() {
  const box = document.getElementById("ctx-list");
  if (!box) return;
  const items = ctxFiltered();
  const cur = currentProject();
  if (ctxActive >= items.length) ctxActive = items.length - 1;
  if (ctxActive < 0) ctxActive = 0;
  // 项目清单还在路上（项目多时首屏要 1s+）：给明确反馈，而不是一个空浮层
  if (!items.length && !(state._projects || []).length) {
    box.innerHTML = `<div class="ctx-empty">${_projectsPromise ? "正在加载项目…" : "还没有项目"}</div>`;
    return;
  }
  const shown = items.slice(0, CTX_LIST_MAX);
  const rows = shown.map((it, i) => `
    <div class="ctx-opt${i === ctxActive ? " active" : ""}" role="option"
         id="ctx-opt-${i}" data-value="${esc(it.value)}"
         aria-selected="${it.value === cur ? "true" : "false"}">
      <span class="ctx-opt-name">${ctxHighlight(it.text, it.q)}</span>
      ${it.sub ? `<span class="ctx-opt-sub">${esc(it.sub)}</span>` : ""}
    </div>`).join("");
  const rest = items.length - shown.length;
  box.innerHTML = (rows || `<div class="ctx-empty">没有匹配的项目</div>`) +
    (rest > 0 ? `<div class="ctx-more">还有 ${rest} 个，输入关键字继续筛选</div>` : "");
  const input = document.getElementById("ctx-search");
  if (input) input.setAttribute("aria-activedescendant", "ctx-opt-" + ctxActive);
  const act = box.querySelector(".ctx-opt.active");
  if (act && act.scrollIntoView) act.scrollIntoView({ block: "nearest" });
}

function ctxRenderTrigger() {
  const btn = document.getElementById("ctx-project");
  if (!btn) return;
  const label = btn.querySelector(".ctx-select-label");
  const cur = currentProject();
  // 清单还在路上时不要显示「全部项目（0）」：项目多时首屏要 1s+，
  // 用户会以为项目丢了。先只显示「全部项目」，到货后再补数量。
  const loaded = !!(state._projects && state._projects.length) || !_projectsPromise;
  const text = cur || (loaded ? `全部项目（${(state._projects || []).length}）` : "全部项目");
  if (label) label.textContent = text;
  btn.title = text;
}

function ctxOpen() {
  const pop = document.getElementById("ctx-pop");
  const btn = document.getElementById("ctx-project");
  const input = document.getElementById("ctx-search");
  if (!pop || !btn || !pop.hidden) return;
  pop.hidden = false;
  btn.setAttribute("aria-expanded", "true");
  if (input) input.value = "";
  const items = ctxFiltered();
  const idx = items.findIndex(x => x.value === currentProject());
  ctxActive = idx < 0 ? 0 : idx;
  ctxRenderList();
  if (input) { input.focus(); input.select(); }
  // 首次进入时清单可能还没到，到了再补一次渲染，避免停在「正在加载项目…」
  if (!(state._projects || []).length) {
    ensureProjects().then(() => {
      if (pop.hidden) return;
      ctxRenderTrigger();
      const list = ctxFiltered();
      const i = list.findIndex(x => x.value === currentProject());
      ctxActive = i < 0 ? 0 : i;
      ctxRenderList();
    });
  }
}

function ctxClose(restoreFocus) {
  const pop = document.getElementById("ctx-pop");
  const btn = document.getElementById("ctx-project");
  if (!pop || pop.hidden) return;
  pop.hidden = true;
  if (btn) {
    btn.setAttribute("aria-expanded", "false");
    if (restoreFocus) btn.focus();
  }
}

function ctxChoose(value) {
  ctxClose(true);
  setProject(value);
}

function setupCtxPicker() {
  const btn = document.getElementById("ctx-project");
  const pop = document.getElementById("ctx-pop");
  const input = document.getElementById("ctx-search");
  const box = document.getElementById("ctx-list");
  const picker = document.getElementById("ctx-picker");
  if (!btn || !pop || !input || !box || !picker) return;

  btn.addEventListener("click", () => { if (pop.hidden) ctxOpen(); else ctxClose(true); });
  btn.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") { e.preventDefault(); ctxOpen(); }
  });

  input.addEventListener("input", () => { ctxActive = 0; ctxRenderList(); });
  input.addEventListener("keydown", (e) => {
    const items = ctxFiltered();
    if (e.key === "ArrowDown") { e.preventDefault(); ctxActive = Math.min(ctxActive + 1, items.length - 1); ctxRenderList(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); ctxActive = Math.max(ctxActive - 1, 0); ctxRenderList(); }
    else if (e.key === "Home") { e.preventDefault(); ctxActive = 0; ctxRenderList(); }
    else if (e.key === "End") { e.preventDefault(); ctxActive = items.length - 1; ctxRenderList(); }
    else if (e.key === "Enter") {
      e.preventDefault();
      const it = items[Math.min(ctxActive, items.length - 1)];
      if (it) ctxChoose(it.value);
    } else if (e.key === "Escape") {
      e.preventDefault(); e.stopPropagation();
      ctxClose(true);
    }
  });

  box.addEventListener("click", (e) => {
    const row = e.target.closest(".ctx-opt");
    if (row) ctxChoose(row.dataset.value || "");
  });

  document.addEventListener("click", (e) => {
    if (pop.hidden) return;
    if (!picker.contains(e.target)) ctxClose(false);
  });
}
// 返回工作台 = 退出当前项目作用域 + 回到全部项目视图。
// 只改 hash 不够：工作台会按 state.project 继续渲染单项目视图。
(function setupCtxHome() {
  const btn = document.getElementById("ctx-home");
  if (!btn) return;
  btn.addEventListener("click", () => {
    setProject(PROJECT_ALL, { rerender: false });
    if (location.hash === "#/home" || location.hash === "" || location.hash === "#/") navigate();
    // 其它页面交给 hashchange 触发；这里不改 hash，避免和链接默认行为重复跳转
  });
})();

setupCtxPicker();

function renderContextBar(name, arg) {
  const bar = document.getElementById("ctxbar");
  const sel = document.getElementById("ctx-project");
  const crumbs = document.getElementById("ctx-crumbs");
  if (!bar || !sel || !crumbs) return;
  // 只在真正换页时收起浮层。navigate() 会对同一页调用两次（同步一次 + 项目清单
  // 到达后补一次），无条件关闭会让刚点开的浮层瞬间消失——项目多、清单慢时必现。
  const routeSig = name + "/" + (arg || "");
  if (routeSig !== state._ctxRoute) {
    state._ctxRoute = routeSig;
    ctxClose(false);
  }
  if (CTX_HIDDEN_ROUTES.has(name)) { bar.hidden = true; return; }

  bar.hidden = false;
  // 只在「已经选定某个项目」时显示回退入口：全部项目视图下它没有意义。
  // 工作台也保留——项目视图下的工作台正是用户切换项目后看到的第一屏。
  const homeBtn = document.getElementById("ctx-home");
  if (homeBtn) homeBtn.hidden = !currentProject();
  ctxRenderTrigger();

  const pageNames = {
    home: "工作台", datasets: "项目与图片集", prompts: "提示词库",
    "prompt-ai": "提示词生成", runs: "运行测试", "judge-iter": "裁判与优化",
    viewer: "结果查看器", project: "项目详情", datasetDetail: "图片集详情",
    truth: "真值标注", truthEdit: "标注", evals: "效果评估",
    workflow: "迭代详情", extract: "字段提取",
  };
  const parts = [];
  const active = currentProject();
  const refOfArg = arg ? decodeURIComponent(arg) : "";
  // 已经在某个项目里：从项目开始；否则从「全部项目」开始
  const rootProject = name === "project" ? refOfArg : (name === "datasetDetail" ? refProject(refOfArg) : active);
  if (rootProject) {
    parts.push(`<a href="#/project/${encodeURIComponent(rootProject)}" class="cur">${esc(rootProject)}</a>`);
  } else {
    parts.push(`<a href="#/datasets">全部项目</a>`);
  }
  if (name === "datasetDetail" && refOfArg) {
    parts.push(`<span class="sep">/</span><span class="page">${esc(refOfArg.includes("::") ? refOfArg.split("::").pop() : refOfArg)}</span>`);
  } else if (name === "project") {
    parts.push(`<span class="sep">/</span><span class="page">项目详情</span>`);
  } else {
    parts.push(`<span class="sep">/</span><span class="page">${esc(pageNames[name] || "页面")}</span>`);
  }
  crumbs.innerHTML = parts.join("");
}

function setupNavToggle() {
  const nav = document.getElementById("nav");
  const btn = document.getElementById("nav-toggle");
  if (!nav || !btn) return;
  const setOpen = (open) => {
    nav.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  };
  btn.onclick = () => setOpen(!nav.classList.contains("open"));
  // 手机端点导航后自动收起，避免遮挡内容
  nav.addEventListener("click", (e) => {
    // 窄屏「工具」是分组标题，点它应该展开子项而不是直接跳到字段提取
    const trigger = e.target.closest(".nav-dropbtn");
    if (trigger && window.matchMedia("(max-width: 1000px)").matches) {
      e.preventDefault();
      trigger.parentElement.classList.toggle("open");
      trigger.setAttribute("aria-expanded", trigger.parentElement.classList.contains("open") ? "true" : "false");
      return;
    }
    if (e.target.closest("a") && window.matchMedia("(max-width: 1000px)").matches) setOpen(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });
  document.addEventListener("click", (e) => {
    if (!nav.classList.contains("open")) return;
    if (e.target.closest("#nav") || e.target.closest("#nav-toggle")) return;
    setOpen(false);
  });
}
setupNavToggle();
// 键盘用户：焦点落在「工具」上时展开子菜单，Tab 才能继续进入子项
document.querySelectorAll(".nav-dropbtn").forEach((btn) => {
  btn.addEventListener("focus", () => {
    btn.parentElement.classList.add("open");
    btn.setAttribute("aria-expanded", "true");
  });
  btn.parentElement.addEventListener("focusout", (e) => {
    if (!btn.parentElement.contains(e.relatedTarget)) {
      btn.parentElement.classList.remove("open");
      btn.setAttribute("aria-expanded", "false");
    }
  });
});
const themeBtn = document.getElementById("theme-toggle");
if (themeBtn) themeBtn.onclick = toggleTheme;

// 退出程序：打包成无窗口程序后没有控制台可关，必须给一个明确的入口。
// 开发态没有注入停机回调，接口返回 supported=false，按钮保持隐藏。
const quitBtn = document.getElementById("quit-toggle");
if (quitBtn) {
  get("/api/app/can-shutdown").then((r) => {
    if (r && r.supported) quitBtn.hidden = false;
  }).catch(() => {});
  quitBtn.onclick = async () => {
    const ok = await confirmDlg(
      "退出后本地服务会停止，正在运行的测试会被中断。确定退出吗？",
      { title: "退出程序", okText: "退出", danger: true });
    if (!ok) return;
    quitBtn.disabled = true;
    try {
      await post("/api/app/shutdown");
    } catch (e) {
      quitBtn.disabled = false;
      toast("退出失败：" + e.message, false);
      return;
    }
    document.body.innerHTML =
      `<div class="quit-done"><h2>已退出</h2>
        <p class="muted">本地服务已停止，可以直接关闭这个页面。</p></div>`;
  };
}

// 骨架屏：列表/详情首次加载时占位，避免空白闪烁
function skeleton(lines, kind) {
  const n = Math.max(1, Number(lines) || 3);
  const rows = Array.from({ length: n }, () => `<div class="sk-line${kind === "card" ? " sk-card" : ""}"></div>`).join("");
  return `<div class="skeleton" role="status" aria-label="加载中">${rows}</div>`;
}
window.skeleton = skeleton;

// 项目清单只取一次（切换项目时靠这份缓存填下拉框），失败时静默降级为「全部项目」
let _projectsPromise = null;
function ensureProjects(force) {
  // 项目清单是上下文条与工作台共用的缓存。首页需要最新的图片集/图片数，
  // 因此允许 force 刷新；同一时刻的并发调用仍然共用同一个请求。
  if (_projectsPromise) return _projectsPromise;
  if (state._projects && !force) return Promise.resolve(state._projects);
  _projectsPromise = get("/api/projects").then(d => {
    state._projects = (d.items || []).filter(p => !p.legacy);
    return state._projects;
  }).catch(() => {
    state._projects = state._projects || [];
    return state._projects;
  }).then(items => {
    _projectsPromise = null;
    return items;
  });
  return _projectsPromise;
}

function navigate() {
  clearPageTimers();
  runPageCleanups();
  // 页面级键盘快捷键随路由卸载，避免上个页面的 handler 在新页面误触发
  document.onkeydown = null;
  // 导航序号：异步路由在写 DOM 前校验，防止慢接口返回后覆盖已切换的新页面
  state._navSeq = (state._navSeq || 0) + 1;
  // 引导进行中：引导自己驱动的跳转让路，用户手动点导航则退出引导
  // 切换页面时收起移动端导航，防止遮挡内容
  const navEl = document.getElementById("nav");
  if (navEl && navEl.classList.contains("open")) {
    navEl.classList.remove("open");
    const nb = document.getElementById("nav-toggle");
    if (nb) nb.setAttribute("aria-expanded", "false");
  }
  if (typeof _tour !== "undefined" && _tour) {
    // 引导自己发起的 hash 跳转用计数抵消：每次赋值恰好产生一次 hashchange，
    // 排队的旧事件可能晚于下一步操作到达，单个布尔标记会被覆盖，
    // 导致「前进后立刻后退」时引导被误判成用户导航而关闭。
    if (_tour.hops > 0) _tour.hops--;
    else stopGuide(false);
  }
  // 重新进入页面时必须重建 DOM：否则会把上一次遗留的内容当成"未变化"而跳过渲染，
  // 导致 URL 已切换但页面仍显示旧内容、列表永久空白等问题。
  state._wfLastSig = null;
  state._itLastSig = null;
  const hash = location.hash.slice(2) || "home";
  const [name, arg] = hash.split("/");
  const toolRoutes = ["extract", "truth", "evals", "jsontool", "truthEdit"];
  ensureProjects().then(() => renderContextBar(name, arg));
  renderContextBar(name, arg);
  $$("#nav a").forEach(a => a.classList.toggle("active",
    a.dataset.route === name || (name === "viewer" && a.dataset.route === "runs") ||
    (["project", "datasetDetail"].includes(name) && a.dataset.route === "datasets") ||
    (toolRoutes.includes(name) && a.dataset.route === "tools") ||
    (name === "profiles" && a.dataset.route === "config") ||
    (name === "workflow" && a.dataset.route === "judge-iter")));
  const fn = routes[name] || routes["home"];
  window.scrollTo(0, 0);
  const seq = state._navSeq;
  let out;
  try {
    out = fn(arg);
  } catch (e) {
    // 路由同步抛错时页面会停在上一帧或骨架屏，必须换成可理解、可重试的失败态
    renderRouteError(name, e);
    return null;
  }
  // 路由内容可能是异步渲染的：先补一次，异步分支完成后由 MutationObserver 兜底
  if (out && typeof out.then === "function") {
    out.then(() => enhanceA11y(document), (e) => {
      // 切页后旧路由的失败不该盖住新页面
      if (seq !== state._navSeq) return;
      renderRouteError(name, e);
    });
  } else enhanceA11y(document);
  return out;
}

// 统一失败态：标题 + 具体原因 + 重试 + 去帮助，而不是只剩一句"暂无数据"。
function renderRouteError(name, err) {
  const msg = (err && err.message) ? err.message : String(err || "未知错误");
  const titles = { home: "工作台", datasets: "项目与图片集", prompts: "提示词库",
    "prompt-ai": "提示词生成", runs: "运行测试", "judge-iter": "裁判与优化",
    config: "系统配置", extract: "字段提取归档", truth: "真值标注任务",
    evals: "效果评估与提示词对比", jsontool: "JSON 工具", help: "帮助与操作指南" };
  $("#app").innerHTML = `
  <div class="page-title">${esc(titles[name] || "页面")}</div>
  <div class="card">
    <div class="msg err" role="alert">页面数据加载失败：${esc(msg)}</div>
    <p class="muted">可能是后端未启动、服务正在重启，或本机防火墙拦截了 127.0.0.1 的请求。</p>
    <div class="row u-mt-12">
      <button class="btn primary" id="route-retry" type="button">重试</button>
      <a class="btn" href="#/help">查看帮助</a>
    </div>
  </div>`;
  const btn = $("#route-retry");
  if (btn) btn.onclick = () => { btn.disabled = true; btn.textContent = "重试中…"; navigate(); };
  enhanceA11y(document);
}
window.addEventListener("hashchange", navigate);

// ---------------------------------------------------------------- 首页工作台
const HOME_CACHE_KEY = "home_dashboard_cache";

function homeShortDate(value) {
  const text = String(value || "");
  return text ? text.slice(0, 10) : "暂无记录";
}

function homeStatsHtml(items) {
  return `<div class="home-stats" aria-label="当前进度">${items.map(item => `
    <div class="hs"><b>${esc(String(item[0]))}${item[2] ? `<span class="hs-of">${esc(item[2])}</span>` : ""}</b><span>${esc(item[1])}</span></div>`).join("")}</div>`;
}

// 七步流程按「一个项目」计算。配置模型与生成提示词是全站共用资源，
// 因此在项目视图里保留这两步，但明确标注 shared，避免让用户误以为是项目私有状态。
function projectFlowSteps(d, project, runs, latest, review, job, optCount) {
  const sitesReady = d.sites.some(s => s.has_keys && s.models > 0);
  const promptCount = d.prompt_count || 0;
  const running = runs.filter(r => r.status === "running").length;
  const reviewed = review ? (review.reviewed || 0) : 0;
  const reviewTotal = latest ? (latest.done || latest.total || 0) : 0;
  const reviewDone = !!latest && reviewTotal > 0 && reviewed >= reviewTotal;
  const eligible = job ? (job.eligible || 0) : 0;
  const pending = job
    ? (job.pending != null ? job.pending : Math.max(0, (job.total || 0) - (job.done || 0) - (job.failed || 0)))
    : 0;
  const judged = Math.max(0, eligible - pending);
  const judgeDone = !!job && eligible > 0 && pending === 0 && reviewDone;
  const reviewHash = latest ? "#/viewer/" + encodeURIComponent(latest.id) : "#/runs";

  const steps = [
    { key: "config", name: "配置模型", hash: "#/config", done: sitesReady, shared: true,
      desc: sitesReady ? `${d.sites.length} 个站点已就绪 · 全站共用` : "全站尚未配置模型",
      title: "先配一个模型站点",
      text: "模型站点是全站共用的：运行测试、裁判归因、生成提示词都用这里配置的模型。配好一次，所有项目都能用。",
      action: "去配置" },
    { key: "datasets", name: "准备图片",
      hash: "#/project/" + encodeURIComponent(project.name),
      done: (project.dataset_count || 0) > 0,
      desc: project.dataset_count ? `${project.dataset_count} 个图片集 · ${project.image_count || 0} 张图` : "在该项目下新建图片集",
      title: `在「${project.name}」下准备图片`,
      text: "这个项目还没有图片集。按场景建 1–3 个图片集，把要测的图片传进来；图片集是测试和真值的基本单位。",
      action: "去准备图片" },
    { key: "prompt", name: "生成提示词", hash: "#/prompt-ai", done: promptCount > 0, shared: true,
      desc: promptCount ? `提示词库 ${promptCount} 个 · 全站共用` : "提示词库为空 · 全站共用",
      title: promptCount ? "提示词库已有可复用版本" : "提示词库还是空的",
      text: "提示词是全站共用的，任何项目都能选。先用对话描述检测需求，生成结构化的五模块提示词。",
      action: "去生成提示词" },
    { key: "runs", name: "运行测试", hash: "#/runs", done: runs.length > 0,
      desc: runs.length ? `${runs.length} 次运行${running ? ` · ${running} 进行中` : ""}` : "用提示词跑本项目图片集",
      title: "跑第一轮测试",
      text: `这个项目已有 ${project.image_count || 0} 张图。选好图片集与提示词版本发起运行，结果会逐张保存。`,
      action: "去运行测试" },
    { key: "review", name: "人工审核", hash: reviewHash, done: reviewDone,
      desc: latest ? (reviewTotal ? `已审 ${reviewed}/${reviewTotal}` : "等待运行完成") : "先完成一次运行",
      title: "审核最近一轮结果",
      text: latest
        ? `最近运行「${latest.prompt_name} V${latest.prompt_version}」还有 ${Math.max(0, reviewTotal - reviewed)} 张没审。审核结论会沉淀为真值。`
        : "先完成一次运行，再逐张确认模型判断是否正确。",
      action: latest ? "继续审核" : "去运行测试" },
    { key: "judge", name: "裁判定位", hash: "#/judge-iter", done: judgeDone,
      desc: job
        ? (eligible ? `已裁判 ${judged}/${eligible}` : (reviewDone ? "可以启动裁判" : "等待人工审核"))
        : "审核完成后启动裁判",
      title: "启动裁判定位",
      text: "人工审核完成后，用裁判模型逐张归因：是漏报、误报还是部分正确，为改提示词提供依据。",
      action: "去裁判定位" },
    { key: "opt", name: "优化验证", hash: "#/judge-iter", done: optCount > 0,
      desc: optCount ? `本项目已生成 ${optCount} 条优化建议` : "综合裁判结果改提示词",
      title: "把裁判结论变成优化建议",
      text: "基于裁判证据生成候选提示词，保存为新版本后再跑一轮，对比准确率。",
      action: "去优化验证" },
  ];
  return { steps, nextStep: steps.find(s => !s.done) || null, doneCount: steps.filter(s => s.done).length };
}

function projectFlowHero(entry) {
  const next = entry.nextStep;
  if (!next) return {
    kicker: "流程已走通",
    title: "这个项目的闭环已经跑通",
    text: "改提示词 → 再跑一轮 → 对比准确率。版本对比能在「效果评估」里看到量化结果。",
    action: "再跑一轮验证", hash: "#/runs" };
  const index = entry.steps.indexOf(next) + 1;
  return {
    kicker: `第 ${index} 步 · ${next.name}${next.shared ? "（全站共用）" : ""}`,
    title: next.title,
    text: next.text,
    action: next.action,
    hash: next.hash,
  };
}

function allProjectsHero(d, entries, sitesReady) {
  if (!sitesReady) return {
    kicker: "全站前置 · 配置模型",
    title: "先配一个模型站点",
    text: "模型站点是全站共用的。配置好 Base URL、API Key 和模型 ID 后，所有项目都能开始跑测试。",
    action: "去配置", hash: "#/config" };
  if (!entries.length) return {
    kicker: "第一步 · 准备图片",
    title: "还没有项目",
    text: "先建一个项目，再把要测的图片按场景导入图片集。每个项目会独立记录自己的流程进度。",
    action: "去新建项目", hash: "#/datasets" };
  const recent = entries[0];
  return {
    kicker: `全部项目 · ${entries.length} 个`,
    title: "从项目列表继续",
    text: "每张项目卡都显示它自己的流程进度。点卡片进入该项目的工作台，七步状态会按该项目的数据重算。",
    action: `继续「${recent.name}」`,
    hash: `#/project/${encodeURIComponent(recent.name)}`,
    openProject: recent.name,
  };
}

// 工作台「全部项目」每页固定 10 条：再多首屏就会被撑得很长，
// 用户找项目只能靠肉眼扫。
const PROJECT_PAGE_SIZE = 10;

function projectCardHtml(entry) {
  const next = entry.nextStep;
  const index = next ? entry.steps.indexOf(next) + 1 : 7;
  const stateText = next
    ? `第 ${index} 步 · ${next.name}${next.shared ? "（全站）" : ""}`
    : "7 步已走通";
  const dots = entry.steps.map((step, i) => {
    const cls = `hp-dot${step.done ? " done" : ""}${step === next ? " todo" : ""}`;
    return `<span class="${cls}" title="${i + 1}. ${esc(step.name)}：${esc(step.desc)}"></span>`;
  }).join("");
  return `<a class="home-proj" href="#/project/${encodeURIComponent(entry.name)}" data-open-project="${esc(entry.name)}" aria-label="进入项目 ${esc(entry.name)} 的工作台，当前${esc(stateText)}">
    <div class="project-icon" aria-hidden="true">▣</div>
    <div class="project-main">
      <div class="home-proj-head"><h3>${esc(entry.name)}</h3><span class="tag ${next ? "blue" : "green"}">${esc(stateText)}</span></div>
      <div class="muted home-proj-desc">${esc(entry.description || "暂无说明")}</div>
      <div class="home-proj-meta">
        <span>${entry.dataset_count} 图片集</span><span>${entry.image_count} 张图</span><span>${entry.run_count} 次运行</span><span>最近 ${esc(homeShortDate(entry.last_activity))}</span>
      </div>
      <div class="home-proj-track" aria-hidden="true">${dots}</div>
    </div>
    <div class="home-proj-next"><b>${next ? esc(next.name) : "已走通"}</b><span>${next ? `第 ${index} / 7 步` : "7 / 7 步"}</span></div>
    <span class="project-arrow" aria-hidden="true">›</span>
  </a>`;
}

async function loadHomeProgress(d) {
  const projects = await ensureProjects(true);
  const [runsRes, jobsRes, optsRes] = await Promise.all([
    get("/api/runs").catch(() => null),
    get("/api/judge-jobs").catch(() => null),
    get("/api/prompt-ai/optimizations").catch(() => null),
  ]);
  const runs = (runsRes && runsRes.items) || [];
  const jobs = (jobsRes && jobsRes.items) || [];
  const opts = (optsRes && optsRes.items) || [];
  const runProject = new Map();
  runs.forEach(r => runProject.set(r.id, r.dataset_project || refProject(r.dataset)));
  const jobByRun = new Map();
  jobs.forEach(job => { if (job && job.run_id) jobByRun.set(job.run_id, job); });
  const recentById = new Map((d.recent_runs || []).map(r => [r.id, r]));
  const optCounts = new Map();
  opts.forEach(opt => {
    const name = runProject.get(opt.source_run);
    if (name) optCounts.set(name, (optCounts.get(name) || 0) + 1);
  });

  const entries = projects.map(project => {
    const projectRuns = runs.filter(r => (r.dataset_project || refProject(r.dataset)) === project.name);
    const latest = projectRuns.find(r => r.status === "done" || (r.done || 0) > 0) || projectRuns[0] || null;
    return { project, runs: projectRuns, latest, optCount: optCounts.get(project.name) || 0 };
  });

  const reviewNeeded = [];
  entries.forEach(entry => {
    if (entry.latest && !recentById.has(entry.latest.id)) reviewNeeded.push(entry.latest.id);
  });
  const reviewMap = new Map();
  await Promise.all([...new Set(reviewNeeded)].map(async id => {
    try {
      const summary = await get(`/api/runs/${encodeURIComponent(id)}/reviews`);
      reviewMap.set(id, { reviewed: ((summary && summary.metrics) || {}).reviewed || 0 });
    } catch (err) {
      reviewMap.set(id, { reviewed: 0 });
    }
  }));

  return { projects: entries.map(entry => {
    const latest = entry.latest;
    const recent = latest ? recentById.get(latest.id) : null;
    const review = latest ? ((recent && recent.review) || reviewMap.get(latest.id) || null) : null;
    const job = latest ? jobByRun.get(latest.id) || null : null;
    const flow = projectFlowSteps(d, entry.project, entry.runs, latest, review, job, entry.optCount);
    const reviewTotal = latest ? (latest.done || latest.total || 0) : 0;
    const reviewed = review ? (review.reviewed || 0) : 0;
    const eligible = job ? (job.eligible || 0) : 0;
    const pending = job
      ? (job.pending != null ? job.pending : Math.max(0, (job.total || 0) - (job.done || 0) - (job.failed || 0)))
      : 0;
    const judged = Math.max(0, eligible - pending);
    const slimRun = run => ({
      id: run.id,
      prompt_name: run.prompt_name,
      prompt_version: run.prompt_version,
      dataset: run.dataset,
      dataset_name: run.dataset_name,
      status: run.status,
      done: run.done || 0,
      total: run.total || 0,
      created: run.created,
      review: latest && run.id === latest.id && review ? { reviewed } : null,
      judge: latest && run.id === latest.id && job ? { judged, eligible, coverage: eligible ? judged / eligible : 1 } : null,
      judge_active: !!(latest && run.id === latest.id && job && job.is_active),
    });
    return {
      name: entry.project.name,
      description: entry.project.description || "",
      created: entry.project.created || "",
      dataset_count: entry.project.dataset_count || 0,
      image_count: entry.project.image_count || 0,
      run_count: entry.runs.length,
      running_count: entry.runs.filter(r => r.status === "running").length,
      opt_count: entry.optCount,
      review_total: reviewTotal,
      reviewed,
      judge_eligible: eligible,
      judged,
      last_activity: latest ? (latest.created || "") : (entry.project.created || ""),
      recent_runs: entry.runs.slice(0, 6).map(slimRun),
      steps: flow.steps,
      nextStep: flow.nextStep,
      doneCount: flow.doneCount,
    };
  }).sort((a, b) => String(b.last_activity).localeCompare(String(a.last_activity))) };
}

route("home", async () => {
  const seq = state._navSeq;
  // 先渲染上次缓存（stale-while-revalidate），新数据到了再替换，首页秒开
  let cached = null;
  try { cached = JSON.parse(localStorage.getItem(HOME_CACHE_KEY) || "null"); } catch (e) {}
  if (cached && cached.v === 2 && cached.d) renderHome(cached.d, true, state._demoStatus || null, cached.pp);
  else $("#app").innerHTML = `<div class="page-title">工作台</div><div class="card">${skeleton(4)}</div>`;
  const [d, demoSt] = await Promise.all([
    get("/api/dashboard"),
    get("/api/demo/status").catch(() => null),
  ]);
  if (seq !== state._navSeq) return;
  let pp = null;
  try { pp = await loadHomeProgress(d); }
  // 失败时要标记 failed：否则「当前项目»不在空列表里»会被误判成项目已删除而被清空
  catch (e) { pp = { projects: [], failed: true }; }
  if (seq !== state._navSeq) return;
  state._demoStatus = demoSt;
  try { localStorage.setItem(HOME_CACHE_KEY, JSON.stringify({ v: 2, d, pp })); } catch (e) {}
  renderHome(d, false, demoSt, pp);
  // 全新工作区（没跑过运行、没提示词）且未看过引导时，自动带新用户走一遍
  if (!localStorage.getItem("guide_done") && !d.run_count && !d.prompt_count) {
    setTimeout(() => { if (location.hash === "" || location.hash === "#/" || location.hash === "#/home") startGuide(); }, 400);
  }
});

function renderHome(d, stale, demo, pp) {
  const sitesReady = d.sites.some(s => s.has_keys && s.models > 0);
  // v2 缓存写的是 { projects: [...] }；兼容中途版本曾直接写成数组的缓存
  const entries = Array.isArray(pp) ? pp : ((pp && pp.projects) || []);
  const loadFailed = !!(pp && pp.failed);
  let activeName = currentProject();
  let entry = activeName ? entries.find(e => e.name === activeName) || null : null;
  if (activeName && !entry && !loadFailed) {
    // 项目已删除或改名：不要让工作台卡在一个不存在的上下文里
    setProject(PROJECT_ALL, { rerender: false });
    activeName = PROJECT_ALL;
  }
  const isAll = !activeName || !entry;
  const recentRuns = isAll ? (d.recent_runs || []) : (entry.recent_runs || []);
  const hero = loadFailed && isAll
    ? { kicker: "数据加载失败", title: "项目清单没能加载出来",
        text: "可能是服务正在重启或网络中断。重试即可；上一次缓存的汇总数据仍会显示。",
        action: "重试", retry: true }
    : (isAll ? allProjectsHero(d, entries, sitesReady) : projectFlowHero(entry));

  // 待办：只保留当前作用域内真实存在的下一步
  const todos = [];
  const seenTodo = new Set();
  recentRuns.forEach(r => {
    const dedupKey = r.prompt_name + "@" + (r.dataset || "");
    const total = r.done || 0;
    const rv = r.review ? r.review.reviewed : 0;
    if ((r.status === "done" || total > 0) && total > 0 && rv < total) {
      if (seenTodo.has(dedupKey)) return;
      seenTodo.add(dedupKey);
      todos.push({ text: `运行「${r.prompt_name} V${r.prompt_version}」待审核`, sub: `${r.dataset_name || r.dataset || ""} · 已审 ${rv}/${total} 张`, action: "继续审核", hash: "#/viewer/" + encodeURIComponent(r.id) });
    } else if (total > 0 && rv >= total && r.judge && (r.judge.judged || 0) < (r.judge.eligible || 0) && !r.judge_active) {
      if (seenTodo.has(dedupKey)) return;
      seenTodo.add(dedupKey);
      todos.push({ text: `运行「${r.prompt_name} V${r.prompt_version}」审核完成，可以启动裁判`, sub: `裁判覆盖 ${r.judge.judged}/${r.judge.eligible}`, action: "去裁判", hash: "#/judge-iter" });
    } else if (r.judge && r.judge.judged > 0 && r.judge.coverage >= 1 && r.review && r.review.counts) {
      const errs = (r.review.counts["误报"] || 0) + (r.review.counts["漏报"] || 0) + (r.review.counts["部分正确"] || 0);
      if (!errs || seenTodo.has(dedupKey)) return;
      seenTodo.add(dedupKey);
      todos.push({ text: `「${r.prompt_name} V${r.prompt_version}」裁判完成，发现 ${errs} 个错误`, sub: "综合裁判结果生成优化建议", action: "去优化", hash: "#/judge-iter" });
    }
  });
  const runningCount = isAll ? (d.running_count || 0) : (entry.running_count || 0);
  if (runningCount) todos.push({ text: `${runningCount} 个运行正在进行`, sub: "查看实时进度", action: "查看", hash: "#/runs" });
  // 真值与量化评估建议：审核沉淀是真值来源，积累够了就引导跑评估对比
  const reviewedAny = recentRuns.some(r => r.review && (r.review.reviewed || 0) > 0);
  const scopedTruth = (d.truth_tasks || []).filter(t => isAll || projectOf({ dataset: t.dataset }) === entry.name);
  if (!scopedTruth.length && reviewedAny) {
    todos.push({ text: "审核时顺手填「期望状态」或画「期望框」，会自动沉淀为真值",
                 sub: "真值积累后可以做提示词版本的量化对比", action: "了解真值", hash: "#/truth" });
  }
  const unevaled = scopedTruth.filter(t => (t.labeled || 0) >= 10 && !(d.eval_tasks || []).includes(t.id));
  if (unevaled.length) {
    todos.push({ text: `真值任务「${unevaled[0].name}」已积累 ${unevaled[0].labeled} 张标注`,
                 sub: "可以跑量化评估，客观对比提示词版本效果", action: "去评估", hash: "#/evals" });
  }

  // 示例项目只在「全部项目」视图出现；单项目视图不重复全局入口
  const demoStrip = isAll && demo && demo.available ? `
  <div class="home-demo">
    <div class="hd-text">
      <b>${demo.created ? "示例项目已就绪" : "第一次用？先拿示例练手"}</b>
      <span>${demo.created
        ? `${esc(demo.prompt_name)} · ${demo.created_images || demo.image_count} 张图 · 现成提示词 · 预置真值`
        : `${demo.image_count} 张示例图 + 现成提示词 + 预置真值，5 分钟走完一遍闭环`}</span>
    </div>
    ${demo.created
      ? `<button class="btn small" id="demo-run" type="button">运行示例项目</button>`
      : `<button class="btn small" id="demo-create" type="button">创建示例项目</button>`}
  </div>` : "";

  const stats = isAll
    ? [[entries.length, "项目"], [d.dataset_count || 0, "图片集"], [d.image_count || 0, "图片"],
       [d.run_count || 0, "运行"], [d.prompt_count || 0, "提示词"], [d.eval_count || 0, "评估"]]
    : [[entry.doneCount, "步骤", `/${entry.steps.length}`], [entry.image_count || 0, "图片"],
       [entry.run_count || 0, "运行"], [`${entry.reviewed || 0}/${entry.review_total || 0}`, "已审"],
       [`${entry.judged || 0}/${entry.judge_eligible || 0}`, "已裁判"], [entry.opt_count || 0, "优化建议"]];
  // 还没有运行 / 裁判时，「0/0」只会制造噪音，用「—」表示尚未开始
  if (!isAll) {
    if (!entry.review_total) stats[3][0] = "—";
    if (!entry.judge_eligible) stats[4][0] = "—";
  }
  const statsHtml = homeStatsHtml(stats);

  const heroAction = hero.retry
    ? `<button class="btn primary" id="home-retry" type="button">${esc(hero.action)}</button>`
    : hero.openProject
      ? `<a class="btn primary" href="${hero.hash}" data-open-project="${esc(hero.openProject)}">${esc(hero.action)}</a>`
      : `<a class="btn primary" href="${hero.hash}">${esc(hero.action)}</a>`;

  const scopeHtml = isAll ? "" : `<div class="home-scope">
    <div class="home-scope-main">
      <span class="hh-kicker">当前项目</span>
      <h3>${esc(entry.name)}</h3>
      <span class="muted">${esc(entry.description || "暂无说明")}</span>
    </div>
    <div class="row home-scope-actions">
      <button class="btn small" id="home-all-projects" type="button">查看全部项目</button>
      <a class="btn small" href="#/project/${encodeURIComponent(entry.name)}">项目详情</a>
    </div>
  </div>`;

  const railHtml = isAll ? "" : `<div class="home-rail-wrap">
    <div class="home-rail" role="list" aria-label="项目流程进度">
      ${entry.steps.map((s, i) => `<a role="listitem" class="home-step ${s.done ? "done" : ""} ${entry.nextStep === s ? "todo" : ""}${s.shared ? " shared" : ""}"
          href="${s.hash}"${entry.nextStep === s ? ' aria-current="step"' : ""} title="${esc(s.desc)}${s.shared ? " · 全站共用" : ""}">
        <span class="sn">${s.done ? "✓" : i + 1}</span><span class="st">${esc(s.name)}</span>
      </a>`).join("")}
    </div>
  </div>
  <div class="home-shared-note muted">「配置模型」和「生成提示词」是全站共用资源；其余 5 步按本项目的数据判定。</div>`;

  const projectListHtml = isAll ? `<div class="card home-project-card">
    <div class="row u-ai-c">
      <h3 class="u-f2 u-m0">全部项目 <span class="tag blue">${entries.length}</span></h3>
      ${entries.length > PROJECT_PAGE_SIZE ? `<div class="u-f1"><input type="text" id="home-pj-search" placeholder="搜索项目名称…" aria-label="搜索项目名称"></div>` : ""}
      <a class="btn small" href="#/datasets">管理项目和图片集</a>
    </div>
    <div class="muted u-mt-6">点项目卡进入该项目的工作台；每张卡片的步骤状态只由该项目的数据决定。</div>
    ${loadFailed ? `<div class="msg err u-mt-8">项目清单加载失败，请刷新后重试。</div>` : ""}
    <div class="home-projects u-mt-10" id="home-projects"></div>
    <div class="home-pager" id="home-pj-pager" hidden></div>
  </div>` : "";

  const runTable = recentRuns.length ? `<div class="tbl-scroll"><table class="tbl"><tbody>${recentRuns.slice(0, 6).map(r => `
        <tr>
          <td><a href="#/viewer/${encodeURIComponent(r.id)}">${esc(r.prompt_name)} V${r.prompt_version}</a><br><span class="muted">${esc(r.dataset_name || r.dataset || "")}${r.dataset_split ? " · " + esc(r.dataset_split) : ""}</span></td>
          <td>${statusTag(r.status)}</td>
          <td class="muted">${r.done || 0}/${r.total || 0}${r.review && r.review.accuracy != null ? `<br>准确率 ${(r.review.accuracy * 100).toFixed(1)}%` : ""}</td>
        </tr>`).join("")}</tbody></table></div>`
    : emptyState(isAll ? "还没有运行记录——配好模型后跑第一轮" : "这个项目还没有运行记录", "去运行测试", "#/runs");

  $("#app").innerHTML = `
  <div class="page-title">工作台${stale ? '<span class="muted page-title-note">数据更新中…</span>' : ""}
    <button class="btn small" id="home-guide" type="button">新手引导</button></div>

  ${scopeHtml}

  <div class="card home-hero">
    <div class="home-hero-main">
      <div class="hh-kicker">${esc(hero.kicker)}</div>
      <h3>${esc(hero.title)}</h3>
      <p>${esc(hero.text)}</p>
      ${heroAction}
    </div>
    ${statsHtml}
  </div>

  ${railHtml}
  ${projectListHtml}
  ${demoStrip}

  <div class="grid grid-2">
    <div class="card">
      <h3>${isAll ? "待办" : "项目待办"}</h3>
      ${todos.length ? todos.slice(0, 6).map(t => `
        <div class="home-todo-item">
          <div class="td">${esc(t.text)}<div class="muted">${esc(t.sub)}</div></div>
          <a class="btn small" href="${t.hash}">${esc(t.action)}</a>
        </div>`).join("") : emptyState(isAll ? "当前没有待处理事项" : "这个项目当前没有待处理事项", "去运行测试", "#/runs")}
    </div>
    <div class="card">
      <h3>${isAll ? "最近运行" : "本项目最近运行"}</h3>
      ${runTable}
    </div>
  </div>`;

  const guideBtn = $("#home-guide");
  if (guideBtn) guideBtn.onclick = () => startGuide();
  const retryBtn = $("#home-retry");
  if (retryBtn) retryBtn.onclick = () => { retryBtn.disabled = true; retryBtn.textContent = "重试中…"; navigate(); };
  const allProjectsBtn = $("#home-all-projects");
  if (allProjectsBtn) allProjectsBtn.onclick = () => setProject(PROJECT_ALL);
  // 项目列表：按名称搜索 + 固定每页 10 条分页。
  if (isAll && $("#home-projects")) {
    const renderProjectPage = () => {
      const box = $("#home-projects");
      const pager = $("#home-pj-pager");
      if (!box) return;
      const searchEl = $("#home-pj-search");
      const q = ((searchEl && searchEl.value) || "").trim().toLowerCase();
      const shown = q ? entries.filter(e => String(e.name).toLowerCase().includes(q)) : entries;
      const pages = Math.max(1, Math.ceil(shown.length / PROJECT_PAGE_SIZE));
      const page = Math.min(Math.max(1, state._pjPage || 1), pages);
      state._pjPage = page;
      const start = (page - 1) * PROJECT_PAGE_SIZE;
      const slice = shown.slice(start, start + PROJECT_PAGE_SIZE);
      box.innerHTML = slice.map(projectCardHtml).join("") || (q
        ? `<div class="empty"><div class="empty-text">没有名称包含「${esc(q)}」的项目</div></div>`
        : emptyState("还没有项目——先建一个项目再导入图片", "去新建项目", "#/datasets"));
      if (!pager) return;
      if (!shown.length || pages <= 1) {
        pager.hidden = true;
        pager.innerHTML = "";
        return;
      }
      const end = Math.min(start + PROJECT_PAGE_SIZE, shown.length);
      const nums = [];
      for (let i = 1; i <= pages; i += 1) {
        if (i === 1 || i === pages || Math.abs(i - page) <= 1) nums.push(i);
        else if (nums[nums.length - 1] !== "...") nums.push("...");
      }
      pager.hidden = false;
      pager.innerHTML = `<span class="muted home-pager-info">${q ? "匹配 " + shown.length + " 个 · " : ""}${start + 1}-${end} / ${shown.length}</span>
        <button class="btn small" type="button" data-pj-page="${page - 1}"${page <= 1 ? " disabled" : ""}>上一页</button>
        ${nums.map(n => n === "..."
          ? '<span class="home-pager-gap" aria-hidden="true">...</span>'
          : `<button class="btn small${n === page ? " primary" : ""}" type="button" data-pj-page="${n}"${n === page ? ' aria-current="page"' : ""}>${n}</button>`).join("")}
        <button class="btn small" type="button" data-pj-page="${page + 1}"${page >= pages ? " disabled" : ""}>下一页</button>`;
      $$("#home-pj-pager [data-pj-page]").forEach(btn => {
        btn.onclick = () => {
          const to = Number(btn.dataset.pjPage);
          if (!to || to === state._pjPage) return;
          state._pjPage = to;
          renderProjectPage();
        };
      });
    };
    const projectSearch = $("#home-pj-search");
    if (projectSearch) projectSearch.oninput = () => {
      state._pjPage = 1;
      renderProjectPage();
    };
    renderProjectPage();
  }
  // 示例项目：创建 / 运行
  const demoCreateBtn = $("#demo-create");
  if (demoCreateBtn) demoCreateBtn.onclick = async () => {
    demoCreateBtn.disabled = true; demoCreateBtn.textContent = "创建中…";
    try {
      const r = await post("/api/demo/create");
      toast(r.created ? `示例项目已创建：${r.images} 张图 + 提示词 + ${r.truth_labeled} 张预置真值` : (r.message || "示例已存在"));
      state._demoStatus = null;
      navigate();
    } catch (e) {
      toast(e.message, false);
      demoCreateBtn.disabled = false; demoCreateBtn.textContent = "创建示例项目";
    }
  };
  const demoRun = $("#demo-run");
  if (demoRun && demo) demoRun.onclick = () => {
    state._runPreselect = { dataset: demo.dataset_ref, prompt_name: demo.prompt_name, prompt_version: 1 };
    location.hash = "#/runs";
  };
}

// ---------------------------------------------------------------- 新手引导
// 轻量分步引导：高亮目标元素 + 气泡说明，可随时跳过；localStorage 记录已完成
// selector=有数据时的内容区；entry=永远存在的创建入口；mock=空状态时气泡里的示意图
const GUIDE_STEPS = [
  { title: "欢迎使用多模态测试平台", center: true,
    text: "这个平台帮你把「提示词效果」变成可量化、可迭代的事：用图片集跑测试 → 人工审核对错 → 裁判定位问题 → 优化提示词 → 再跑一轮验证。接下来花一分钟带你走一遍核心流程。想先练手的话，工作台可以一键创建「防溺水示例项目」，自带图片、提示词和真值。" },
  { title: "第一步：配置模型", hash: "#/config", selector: "#c-sites .site-card", entry: "#c-add-site",
    text: "先在这里添加模型站点：填 Base URL、API Key 和模型 ID。运行测试、裁判、提示词生成都用这里配置的模型。配好一次，终身受用。" },
  { title: "第二步：准备图片", hash: "#/datasets", selector: ".project-row", entry: "#pj-create",
    text: "创建项目和图片集，把要测试的图片传上来。图片集是测试的基本单位，建议按场景分开管理。",
    emptyText: "你现在还没有项目，点高亮的「创建项目」按钮建第一个。建好后长这样：",
    mock: `<div class="tm-card"><b>城市治理项目</b><span class="muted">3 图片集 · 314 张图</span></div>
           <div class="tm-card"><b>工地安全项目</b><span class="muted">2 图片集 · 128 张图</span></div>` },
  { title: "第三步：生成提示词", hash: "#/prompt-ai", selector: "#pai-sessions .sess-item", entry: "#pai-new",
    text: "用对话方式描述你的检测需求，AI 会帮你生成结构化的五模块提示词。生成的提示词会收进提示词库，可以反复迭代版本。",
    emptyText: "点高亮的「新建对话」开始描述你的需求，对话过程长这样：",
    mock: `<div class="tm-chat me">帮我写一个"检测吊车下方是否站人"的提示词</div>
           <div class="tm-chat ai">好的，已为你生成五模块提示词：任务描述、判定标准、工作流程…</div>` },
  { title: "第四步：运行测试", hash: "#/runs", selector: "#r-list .p-group", entry: "#r-create",
    text: "选图片集 + 提示词版本，发起运行。每张图都会调用模型并保存结果，支持多次复现检验稳定性。",
    emptyText: "在上面表单选好图片集和提示词，点「创建并运行」。运行中的任务长这样：",
    mock: `<div class="tm-run"><b>非机动车违停 V4</b><div class="tm-bar"><i class="u-w-68p"></i></div><span class="muted">64/94</span></div>
           <div class="tm-run"><b>吊车下方站人 V2</b><div class="tm-bar"><i class="u-w-full"></i></div><span class="muted">完成</span></div>` },
  { title: "第五步：人工审核", hash: "#/runs", selector: "#r-list .p-group", entry: "#r-list",
    text: "运行完成后点进结果页逐张审核，标「正确/误报/漏报」。顺手填期望状态或画期望框——它们会自动沉淀为真值，积累够了就能做量化版本对比。",
    emptyText: "有运行记录后，点进任意运行即可逐张审核。审核界面长这样：",
    mock: `<div class="tm-review"><div class="tm-img">图片 + 模型结果</div>
           <div class="tm-vbtns"><i class="ok">正确</i><i class="bad">误报</i><i class="bad">漏报</i><i class="mid">部分正确</i></div></div>` },
  { title: "第六步：裁判与优化", hash: "#/judge-iter", selector: "#ji-results", entry: "#ji-start",
    text: "审核出的错误交给裁判模型自动归因，定位到提示词的具体模块；一键生成优化建议，确认后存为新版本，再跑一轮验证效果，完成迭代闭环。",
    emptyText: "完成审核后点「启动裁判」，裁判会给出这样的归因和优化建议：",
    mock: `<div class="tm-judge"><b>误报 · definition 模块</b>：边界定义不清 → 建议补充排除规则</div>
           <div class="tm-flow">↓ 生成优化建议，确认后保存</div>
           <div class="tm-ver">提示词 V2 → <b>V3</b>（再跑一轮验证效果）</div>` },
  { title: "准备就绪", center: true,
    text: "核心闭环就是这些。平时打开工作台，它会根据你的进度告诉你下一步该做什么。这个引导可以随时在工作台右上角重新观看。" },
];

let _tour = null;

function isTourVisible(el) {
  if (!el || !el.isConnected) return false;
  const cs = getComputedStyle(el);
  if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}

function tourClamp(v, min, max) {
  return Math.min(Math.max(v, min), Math.max(min, max));
}

function detachTourListeners(my) {
  if (!my) return;
  if (my.reposition) {
    window.removeEventListener("scroll", my.reposition);
    window.removeEventListener("resize", my.reposition);
    my.reposition = null;
  }
  if (my.timer) {
    clearTimeout(my.timer);
    my.timer = null;
  }
}

function isTourTyping(e) {
  const t = e.target;
  if (!t || !t.tagName) return false;
  if (t.isContentEditable) return true;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName);
}

function onTourKey(e) {
  if (!_tour) return;
  if (e.key === "Escape") { e.preventDefault(); stopGuide(true); return; }
  // 引导页上可能正在填写 Base URL / API Key，方向键必须留给光标移动
  if (isTourTyping(e)) return;
  if (e.key === "ArrowRight") { e.preventDefault(); stepGuide(1); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); stepGuide(-1); }
}

function ensureTourRoot() {
  let root = document.getElementById("tour-root");
  if (root) return root;
  root = document.createElement("div");
  root.id = "tour-root";
  root.innerHTML = `
    <div class="tour-mask"></div>
    <div class="tour-spot" hidden></div>
    <div class="tour-bubble" title="按住可拖动">
      <div class="tour-step-tag"></div>
      <div class="tour-title"></div>
      <div class="tour-text"></div>
      <div class="tour-mock-wrap" hidden>
        <div class="tour-mock-note"></div>
        <div class="tour-mock"></div>
      </div>
      <div class="tour-actions">
        <button class="btn small" id="tour-skip">跳过引导</button>
        <span class="u-f1"></span>
        <button class="btn small" id="tour-prev">上一步</button>
        <button class="btn small primary" id="tour-next">下一步</button>
      </div>
    </div>`;
  document.body.appendChild(root);
  root.querySelector("#tour-skip").onclick = () => stopGuide(true);
  root.querySelector("#tour-next").onclick = () => stepGuide(1);
  root.querySelector("#tour-prev").onclick = () => stepGuide(-1);
  bindTourDrag(root);
  document.addEventListener("keydown", onTourKey);
  return root;
}

// 气泡可拖动：目标过大或窗口过矮时，用户能把它挪开看内容。
// 拖动过之后位置由用户决定，scroll/resize 只挪高亮，不再抢回气泡。
function bindTourDrag(root) {
  const bubble = root.querySelector(".tour-bubble");
  if (!bubble) return;
  let drag = null;
  const stop = () => {
    if (!drag) return;
    bubble.classList.remove("dragging");
    if (bubble.hasPointerCapture && bubble.hasPointerCapture(drag.id)) {
      try { bubble.releasePointerCapture(drag.id); } catch (e) {}
    }
    drag = null;
  };
  bubble.addEventListener("pointerdown", (e) => {
    if (e.button !== undefined && e.button !== 0) return;
    // 按钮、输入框和链接保留原生交互，不当作拖动手柄
    if (e.target.closest("button, a, input, textarea, select, label")) return;
    if (!_tour) return;
    if (bubble.classList.contains("center")) bubble.classList.remove("center");
    // 手动拖动时恢复完整内容，不再沿用自动限高
    bubble.style.maxHeight = "";
    const r = bubble.getBoundingClientRect();
    drag = { id: e.pointerId, dx: e.clientX - r.left, dy: e.clientY - r.top };
    bubble.classList.add("dragging");
    try { bubble.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  bubble.addEventListener("pointermove", (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    const vw = document.documentElement.clientWidth;
    const vh = window.innerHeight;
    const w = bubble.offsetWidth;
    const h = bubble.offsetHeight;
    const x = tourClamp(e.clientX - drag.dx, 8, vw - w - 8);
    const y = tourClamp(e.clientY - drag.dy, 8, vh - h - 8);
    bubble.style.transform = `translate3d(${Math.round(x)}px, ${Math.round(y)}px, 0)`;
    if (_tour) _tour.dragPos = { x, y };
  });
  bubble.addEventListener("pointerup", stop);
  bubble.addEventListener("pointercancel", stop);
  bubble.addEventListener("lostpointercapture", stop);
}

function startGuide() {
  if (_tour) stopGuide(false);
  _tour = { idx: 0, seq: 0, hops: 0, target: null, timer: null, reposition: null, dragPos: null };
  renderGuideStep();
}

function stopGuide(markDone = true) {
  if (markDone) { try { localStorage.setItem("guide_done", "1"); } catch (e) {} }
  if (_tour) {
    _tour.seq++;
    detachTourListeners(_tour);
  }
  const el = document.getElementById("tour-root");
  if (el) el.remove();
  document.removeEventListener("keydown", onTourKey);
  _tour = null;
}

function stepGuide(delta) {
  if (!_tour) return;
  const next = _tour.idx + delta;
  if (next < 0) return;
  if (next >= GUIDE_STEPS.length) {
    stopGuide(true);
    location.hash = "#/home";
    return;
  }
  _tour.idx = next;
  renderGuideStep();
}

function tourViewport() {
  // 顶栏是 sticky 的，滚到顶部时目标会被它压住，可视区上边界要让开
  const bar = document.querySelector(".topbar");
  const barBottom = bar ? Math.min(bar.getBoundingClientRect().bottom, window.innerHeight / 3) : 0;
  return {
    left: 8,
    right: document.documentElement.clientWidth - 8,
    top: Math.round(Math.max(0, barBottom)) + 8,
    bottom: window.innerHeight - 8,
  };
}

function scrollTourTarget(el) {
  const vp = tourViewport();
  const rect = el.getBoundingClientRect();
  const avail = vp.bottom - vp.top;
  if (rect.height <= avail) {
    const delta = rect.top - (vp.top + (avail - rect.height) / 2);
    if (Math.abs(delta) >= 1) scrollByInstant(delta);
    return;
  }

  // 目标比可视区高：只在「能看到它从哪开始」的前提下滚动。
  // 锚点取目标、所属卡片、页面标题里最靠上的那个，避免把页头滚出屏幕后
  // 用户完全不知道自己在哪一页。
  let anchor = rect.top;
  const card = el.closest(".card");
  if (card) anchor = Math.min(anchor, card.getBoundingClientRect().top);
  const title = document.querySelector(".page-title");
  if (title) {
    const tr = title.getBoundingClientRect();
    if (tr.bottom <= anchor && anchor - tr.top <= avail * 0.6) anchor = tr.top;
  }
  const delta = anchor - (vp.top + 8);
  if (Math.abs(delta) >= 1) scrollByInstant(delta);
}

function scrollByInstant(delta) {
  try {
    window.scrollBy({ top: delta, behavior: "instant" });
  } catch (e) {
    window.scrollBy(0, delta);
  }
}

// 高亮框 = 目标 ∩ 可视区：不撑高、不收口，保证框线永远贴着目标本体。
// 气泡单独择位：下 → 右 → 左 → 上，取第一个放得下的空带；
// 都放不下时（目标特别高 / 窗口特别矮）取上下空带里较高的一条，
// 并把气泡限高后内部滚动——宁可气泡变小，也不能盖住目标。
function placeBubble(spotBox, size, vp, gap) {
  const gapPx = gap;
  const bands = {
    below: { left: vp.left, right: vp.right, top: spotBox.bottom + gapPx, bottom: vp.bottom },
    above: { left: vp.left, right: vp.right, top: vp.top, bottom: spotBox.top - gapPx },
    right: { left: spotBox.right + gapPx, right: vp.right, top: vp.top, bottom: vp.bottom },
    left: { left: vp.left, right: spotBox.left - gapPx, top: vp.top, bottom: vp.bottom },
  };
  const order = ["below", "right", "left", "above"];
  const minX = vp.left + 4;
  const maxX = vp.right - size.w - 4;
  const minY = vp.top + 4;
  const maxY = vp.bottom - size.h - 8;

  for (const name of order) {
    const b = bands[name];
    const w = b.right - b.left;
    const h = b.bottom - b.top;
    if (w < size.w || h < size.h) continue;
    // 沿带的内侧对齐：下方/上方贴目标的水平起点，左方/右方贴可视区顶
    let x = name === "right" ? b.left : name === "left" ? b.right - size.w : spotBox.left;
    let y = name === "below" ? b.top : name === "above" ? b.bottom - size.h : vp.top;
    return {
      x: Math.round(tourClamp(x, minX, maxX)),
      y: Math.round(tourClamp(y, minY, maxY)),
      band: name,
      shrink: 0,
    };
  }

  // 四条带都塞不下（窗口特别矮 / 目标特别高）：取上下里更宽裕的一条，
  // 把气泡限高后内部滚动。高亮框一动不动，所以绝不会盖住目标。
  const belowH = bands.below.bottom - bands.below.top;
  const aboveH = bands.above.bottom - bands.above.top;
  const name = belowH >= aboveH ? "below" : "above";
  const b = bands[name];
  const h = Math.max(48, Math.min(size.h, Math.floor(b.bottom - b.top)));
  const y = name === "below" ? b.top : b.bottom - h;
  return {
    x: Math.round(tourClamp(spotBox.left, minX, maxX)),
    y: Math.round(tourClamp(y, minY, Math.max(minY, vp.bottom - h - 8))),
    band: name,
    shrink: h,
  };
}

function positionTour(root, target, my) {
  if (!target || !target.isConnected) return;
  const spot = root.querySelector(".tour-spot");
  const bubble = root.querySelector(".tour-bubble");
  if (!spot || !bubble) return;
  const vp = tourViewport();
  const r = target.getBoundingClientRect();
  const pad = 6;

  const left = Math.max(r.left - pad, vp.left);
  const right = Math.min(r.right + pad, vp.right);
  const top = Math.max(r.top - pad, vp.top);
  const bottom = Math.min(r.bottom + pad, vp.bottom);
  const spotBox = { left, right, top, bottom };

  spot.style.transform = "translate3d(" + Math.round(left) + "px, " + Math.round(top) + "px, 0)";
  spot.style.width = Math.max(8, right - left) + "px";
  spot.style.height = Math.max(8, bottom - top) + "px";

  if (bubble.classList.contains("center")) return;
  const bw = bubble.offsetWidth;
  if (my && my.dragPos) {
    const bh0 = bubble.offsetHeight;
    const dx = tourClamp(my.dragPos.x, vp.left, vp.right - bw);
    const dy = tourClamp(my.dragPos.y, vp.top, vp.bottom - bh0);
    bubble.style.transform = "translate3d(" + Math.round(dx) + "px, " + Math.round(dy) + "px, 0)";
    return;
  }

  // 先按当前内容试排一次；放不下就把气泡限高（内部滚动）再排一次
  bubble.style.maxHeight = "";
  let pos = placeBubble(spotBox, { w: bw, h: bubble.offsetHeight }, vp, 14);
  if (pos.shrink) {
    bubble.style.maxHeight = pos.shrink + "px";
    // 限高后高度变了，重排一次确认不会压到目标
    const before = pos.band;
    pos = placeBubble(spotBox, { w: bw, h: bubble.offsetHeight }, vp, 14);
    if (pos.shrink) pos.band = before;
  }
  bubble.style.transform = "translate3d(" + pos.x + "px, " + pos.y + "px, 0)";
}

// 记住气泡当前的视觉位置，再切换定位方式（center <-> 自由定位）时不会跳一下。
function pinTourBubble(bubble) {
  const r = bubble.getBoundingClientRect();
  bubble.style.transform = "translate3d(" + Math.round(r.left) + "px, " + Math.round(r.top) + "px, 0)";
  bubble.classList.remove("center");
}

function locateTourTarget(step, seq) {
  return new Promise((resolve) => {
    const started = performance.now();
    // 目标内容本地渲染，实测 30-80ms 就出现。旧实现要「先等 400ms 再试 entry」，
    // 于是每步都要 500ms 以上框才到位——这就是用户感觉到的「操作滞后」。
    // 现在 selector 一出现就用它，没有就立刻退回 entry（两者 ID 各自唯一，不会误判）。
    // 有 entry 兜底的步骤本来就不会空等，预算给宽一点即可。
    const totalBudget = step.entry ? 2500 : 900;
    const check = () => {
      if (!_tour || _tour.seq !== seq) return resolve(null);
      const elapsed = performance.now() - started;
      if (step.selector) {
        const el = document.querySelector(step.selector);
        if (isTourVisible(el)) return resolve({ el, empty: false });
      }
      if (step.entry) {
        const el = document.querySelector(step.entry);
        if (isTourVisible(el)) return resolve({ el, empty: !!step.selector });
      }
      if (elapsed >= totalBudget) return resolve(null);
      setTimeout(check, elapsed < 200 ? 24 : 50);
    };
    check();
  });
}

function applyTourTarget(root, my, match) {
  const spot = root.querySelector(".tour-spot");
  const mask = root.querySelector(".tour-mask");
  const bubble = root.querySelector(".tour-bubble");
  const mockWrap = root.querySelector(".tour-mock-wrap");
  const step = my.step;

  if (!match) {
    // 没有可指向的目标：退回全屏压暗 + 居中气泡，不留上一帧的旧框
    my.target = null;
    spot.hidden = true;
    mask.hidden = false;
    mockWrap.hidden = !step.mock;
    bubble.classList.toggle("wide", !!step.mock);
    bubble.classList.add("center");
    bubble.style.transform = "";
    bubble.style.maxHeight = "";
    return;
  }

  my.target = match.el;
  mask.hidden = true;
  spot.hidden = false;
  bubble.classList.remove("center");
  mockWrap.hidden = !(match.empty && step.mock);
  bubble.classList.toggle("wide", !mockWrap.hidden);

  scrollTourTarget(match.el);
  positionTour(root, match.el, my);
  requestAnimationFrame(() => {
    if (!_tour || _tour !== my) return;
    positionTour(root, match.el, my);
    spot.classList.add("smooth");
  });

  my.reposition = () => {
    if (!_tour || _tour !== my) return;
    positionTour(root, my.target, my);
  };
  window.addEventListener("scroll", my.reposition, { passive: true });
  window.addEventListener("resize", my.reposition);
  my.timer = setTimeout(my.reposition, 220);
}

function renderGuideStep() {
  if (!_tour) return;
  const my = _tour;
  const root = ensureTourRoot();
  const seq = ++my.seq;
  const step = GUIDE_STEPS[my.idx];
  const isLast = my.idx === GUIDE_STEPS.length - 1;
  my.step = step;
  my.target = null;
  my.dragPos = null;
  detachTourListeners(my);

  const spot = root.querySelector(".tour-spot");
  const mask = root.querySelector(".tour-mask");
  const bubble = root.querySelector(".tour-bubble");
  const mockWrap = root.querySelector(".tour-mock-wrap");

  root.querySelector(".tour-step-tag").textContent = `${my.idx + 1} / ${GUIDE_STEPS.length}`;
  root.querySelector(".tour-title").textContent = step.title;
  root.querySelector(".tour-text").textContent = step.text;
  root.querySelector("#tour-prev").hidden = my.idx === 0;
  root.querySelector("#tour-next").textContent = isLast ? "开始使用" : "下一步";

  if (step.mock) {
    root.querySelector(".tour-mock-note").textContent = step.emptyText || "";
    root.querySelector(".tour-mock").innerHTML = step.mock;
  } else {
    root.querySelector(".tour-mock-note").textContent = "";
    root.querySelector(".tour-mock").innerHTML = "";
  }
  mockWrap.hidden = true;
  spot.classList.remove("smooth");

  const needNav = !!step.hash && location.hash !== step.hash;
  if (needNav) {
    my.hops++;
    location.hash = step.hash;
  }

  if (!step.selector && !step.entry) {
    // 纯说明步骤：全屏压暗，气泡居中
    spot.hidden = true;
    mask.hidden = false;
    bubble.classList.remove("wide");
    bubble.classList.add("center");
    bubble.style.transform = "";
    bubble.style.maxHeight = "";
    return;
  }

  // 有目标的步骤：气泡留在原地（不先闪到屏幕中间）；
  // 目标就绪前保持整屏压暗，不要沿用上一页的旧框（会闪出一个错误位置的洞）。
  mask.hidden = false;
  spot.hidden = true;
  pinTourBubble(bubble);

  locateTourTarget(step, seq).then((match) => {
    if (!_tour || _tour !== my || my.seq !== seq) return;
    applyTourTarget(root, my, match);
  });
}

// ---------------------------------------------------------------- 配置页
route("config", async () => {
  const cfg = await get("/api/config");
  $("#app").innerHTML = `
  <div class="page-title">系统配置</div>
  <div class="tabs" id="c-tabs">
    <div class="tab active" data-tab="sites">站点与参数</div>
    <div class="tab" data-tab="profiles">提示词模板</div>
  </div>
  <div data-pane="sites">
  <div class="card">
    <div class="row u-ai-c">
      <h3 class="u-f2 u-m0">模型站点 <span class="tag blue">${cfg.api.sites.length}</span></h3>
      <div class="u-f0"><button class="btn small" id="c-add-site">+ 添加站点</button></div>
    </div>
    <div class="muted u-m-6-0-10">每个站点是一套独立的 Base URL、API Keys 和模型列表；运行、裁判、提示词生成等所有模型选择都会按站点分组同步到这里配置的模型。</div>
    <div id="c-sites"></div>
  </div>
  <div class="card">
    <h3>默认运行参数</h3>
    <div class="row">
      <div><label class="f">默认站点 / 模型</label><select id="c-model"></select></div>
      <div><label class="f">并发数</label><input type="number" id="c-conc" value="${cfg.defaults.concurrency}" min="1" max="20"></div>
      <div><label class="f">超时（秒）</label><input type="number" id="c-timeout" value="${cfg.defaults.timeout}"></div>
    </div>
    <div class="row">
      <div><label class="f">最大重试</label><input type="number" id="c-retry" value="${cfg.defaults.max_retries}"></div>
      <div><label class="f">重试间隔（秒）</label><input type="number" id="c-delay" value="${cfg.defaults.retry_delay}"></div>
      <div><label class="f">max_tokens</label><input type="number" id="c-tokens" value="${cfg.defaults.max_tokens}"></div>
    </div>
    <div class="row">
      <div><label class="f">单 Key 并发上限</label><input type="number" id="c-key-conc" value="${cfg.defaults.key_concurrency ?? 1}" min="1" max="8"></div>
      <div><label class="f">429 冷却秒数</label><input type="number" id="c-key-cooldown" value="${cfg.defaults.key_cooldown ?? 10}" min="0" max="600"></div>
      <div class="u-as-c"><label class="f"><input type="checkbox" id="c-auto-conc" ${cfg.defaults.auto_concurrency !== false ? "checked" : ""}> 按 API Key 数量自动限制有效并发</label></div>
    </div>
    <div class="row">
      <div><label class="f">temperature（留空=不设置）</label><input type="text" id="c-temp" value="${cfg.defaults.temperature ?? ""}"></div>
      <div><label class="f">seed（留空=不设置）</label><input type="text" id="c-seed" value="${cfg.defaults.seed ?? ""}"></div>
      <div><label class="f">裁判 temperature（0-2）</label><input type="number" id="c-judge-temp" value="${cfg.defaults.judge_temperature ?? 0.3}" min="0" max="2" step="0.1"></div>
    </div>
    <div class="row">
     <div><label class="f">优化器 max_tokens</label><input type="number" id="c-opt-tokens" value="${cfg.defaults.optimizer_max_tokens ?? 8192}" min="128" max="131072"></div>
     <div><label class="f">优化器超时（秒）</label><input type="number" id="c-opt-timeout" value="${cfg.defaults.optimizer_timeout ?? 600}" min="30" max="1800"></div>
      <div><label class="f">裁判 max_tokens</label><input type="number" id="c-judge-tokens" value="${cfg.defaults.judge_max_tokens ?? 8192}" min="128" max="131072"></div>
      <div><label class="f">提示词 max_tokens</label><input type="number" id="c-prompt-tokens" value="${cfg.defaults.prompt_max_tokens ?? 8192}" min="128" max="131072"></div>
   </div>
    <div  class="row u-mt-14">
      <div class="u-f0"><button class="btn primary" id="c-save">保存配置</button></div>
      <div class="u-f0"><button class="btn" id="c-test">测试全部站点</button></div>
      <div class="u-f2 u-as-c"  id="c-testout"></div>
    </div>
  </div>
  </div>
  <div class="u-hide" data-pane="profiles"></div>`;
  // 配置页 tab 切换；模板管理按需懒加载
  let profilesLoaded = false;
  const activateTab = (name) => {
    $$("#c-tabs .tab").forEach(x => x.classList.toggle("active", x.dataset.tab === name));
    $$("#app [data-pane]").forEach(p => setShown(p, p.dataset.pane === name));
    if (name === "profiles" && !profilesLoaded) {
      profilesLoaded = true;
      renderProfilesPage($('#app [data-pane="profiles"]'));
    }
  };
  $$("#c-tabs .tab").forEach(t => t.onclick = () => activateTab(t.dataset.tab));
  if (state._configTab === "profiles") { state._configTab = null; activateTab("profiles"); }
  // 站点卡片：本地编辑模型，保存时统一提交
  let sites = cfg.api.sites.map(s => ({ name: s.name, base_url: s.base_url,
    api_keys: (s.api_keys_masked || []).join("\n"), models: (s.models || []).join("\n"),
    masked: (s.api_keys_masked || []).join("，") }));
  const renderSites = () => {
    $("#c-sites").innerHTML = sites.map((s, i) => `
    <div class="site-card" data-i="${i}">
      <div class="row u-ai-c">
        <div class="u-f1"><label class="f">站点名称</label><input type="text" data-f="name" value="${esc(s.name)}" placeholder="如：海康MaaS / 公司内网平台"></div>
        <div class="u-f2"><label class="f">Base URL</label><input type="text" data-f="base_url" value="${esc(s.base_url)}" placeholder="https://…/v1"></div>
        <div class="u-f0 u-as-fe"><button class="btn small" data-test="${i}">测试</button></div>
        <div class="u-f0 u-as-fe"><button class="btn small danger" data-rm="${i}" ${sites.length <= 1 ? "disabled" : ""}>删除</button></div>
      </div>
      <div class="site-fields">
        <label class="f" for="cf-keys-${i}">API Keys（每行一个，可多个用于并发）</label>
        <label class="f" for="cf-models-${i}">可用模型（每行一个，需与平台模型 ID 一致）</label>
        <textarea id="cf-keys-${i}" data-f="api_keys" rows="3" placeholder="sk-…">${esc(s.api_keys)}</textarea>
        <textarea id="cf-models-${i}" data-f="models" rows="3" placeholder="模型ID">${esc(s.models)}</textarea>
        <div class="site-saved">${s.masked ? `已保存：${esc(s.masked)}` : ""}</div>
        <div class="site-saved"></div>
      </div>
      <div class="muted" data-testout="${i}"></div>
    </div>`).join("");
    $$("#c-sites .site-card").forEach(card => {
      const i = Number(card.dataset.i);
      $$("[data-f]", card).forEach(inp => {
        inp.oninput = () => { sites[i][inp.dataset.f] = inp.value; };
        // 模型列表直接决定下方「默认站点 / 模型」的可选项，必须跟着重建，
        // 否则用户刚填的模型要刷新整页才出现在默认下拉里。
        if (inp.dataset.f === "models") inp.addEventListener("input", refreshDefaultSelect);
        // 站点名同时是下拉的 optgroup 与选项值前缀：输入过程中会短暂为空，
        // 实时重建会让选项忽隐忽现，改成失焦后再刷新。
        if (inp.dataset.f === "name") inp.addEventListener("change", refreshDefaultSelect);
      });
      $(`[data-rm="${i}"]`, card).onclick = async () => {
        if (sites.length <= 1) return;
        if (!(await confirmDlg(`确定删除站点「${sites[i].name}」？`, { title: "删除站点" }))) return;
        sites.splice(i, 1); renderSites(); refreshDefaultSelect();
      };
      $(`[data-test="${i}"]`, card).onclick = async () => {
        const out = $(`[data-testout="${i}"]`, card);
        out.innerHTML = '<span class="muted">正在连接…</span>';
        try { await saveCfg(); } catch (e) { out.innerHTML = `<span class="tag red">保存失败</span> <span class="muted">${esc(e.message)}</span>`; return; }
        try {
          const r = await post("/api/config/test?site=" + encQ(sites[i].name));
          const one = (r.results || [])[0] || {};
          if (one.ok) {
            const hit = (one.models || []).filter(m => sites[i].models.split("\n").map(x => x.trim()).includes(m));
            const label = one.probe === "chat"
              ? `对话探测成功，配置模型 ${one.models.length} 个`
              : `平台可用模型 ${one.models.length} 个${hit.length ? "，本站点配置命中：" + hit.map(esc).join("、") : ""}`;
            out.innerHTML = `<span class="tag green">连接成功</span> <span class="muted">${label}</span>`;
          } else {
            out.innerHTML = `<span class="tag red">连接失败</span> <span class="muted">${esc(one.error || "")}</span>`;
          }
        } catch (e) { out.innerHTML = `<span class="tag red">连接失败</span> <span class="muted">${esc(e.message)}</span>`; }
      };
    });
  };
  const collectSites = () => sites.map(s => ({
    name: s.name.trim(), base_url: s.base_url.trim(),
    api_keys: s.api_keys.split("\n").map(x => x.trim()).filter(Boolean),
    models: s.models.split("\n").map(x => x.trim()).filter(Boolean),
  })).filter(s => s.name);
  const refreshDefaultSelect = () => {
    const valid = collectSites().filter(s => s.models.length);
    const sel = $("#c-model");
    const cur = sel.value;
    sel.innerHTML = valid.map(s => `<optgroup label="${esc(s.name)}">${s.models.map(m => {
      const v = `${s.name}::${m}`;
      return `<option value="${esc(v)}">${esc(m)}</option>`;
    }).join("")}</optgroup>`).join("");
    const all = valid.flatMap(s => s.models.map(m => `${s.name}::${m}`));
    // 兜底顺序：保持当前选择 → 原默认值 → 列表第一项。
    // 不能只回退到 smValue(cfg)：用户删掉默认模型后那个值已不存在，
    // select 会显示空白，看起来像「下拉里什么都没了」。
    if (all.includes(cur)) sel.value = cur;
    else if (all.includes(smValue(cfg))) sel.value = smValue(cfg);
    else sel.value = all[0] || "";
  };
  const saveCfg = async () => {
    const num = (id, d) => { const v = $(id).value.trim(); return v === "" ? d : Number(v); };
    const dm = smParse($("#c-model").value);
    const body = {
      api: { sites: collectSites() },
      defaults: {
        site: dm.site, model: dm.model,
        concurrency: num("#c-conc", 3), timeout: num("#c-timeout", 120),
        max_retries: num("#c-retry", 3), retry_delay: num("#c-delay", 2),
        max_tokens: num("#c-tokens", 4096),
        key_concurrency: num("#c-key-conc", 1),
        key_cooldown: num("#c-key-cooldown", 10),
        auto_concurrency: $("#c-auto-conc").checked,
        temperature: $("#c-temp").value.trim() === "" ? null : Number($("#c-temp").value),
        seed: $("#c-seed").value.trim() === "" ? null : Number($("#c-seed").value),
        judge_temperature: num("#c-judge-temp", 0.3),
       optimizer_max_tokens: num("#c-opt-tokens", 8192),
       optimizer_timeout: num("#c-opt-timeout", 600),
        judge_max_tokens: num("#c-judge-tokens", 8192),
        prompt_max_tokens: num("#c-prompt-tokens", 8192),
     },
    };
    await put("/api/config", body);
  };
  renderSites();
  refreshDefaultSelect();
  $("#c-add-site").onclick = () => {
    sites.push({ name: `站点${sites.length + 1}`, base_url: "https://", api_keys: "", models: "", masked: "" });
    renderSites(); refreshDefaultSelect();
  };
  $("#c-save").onclick = async () => {
    try { await saveCfg(); toast("配置已保存"); }
    catch (e) { toast(e.message, false); }
  };
  $("#c-test").onclick = async () => {
    const out = $("#c-testout");
    out.innerHTML = '<span class="muted">正在连接全部站点…</span>';
    try { await saveCfg(); }  // 先保存当前表单再测，保证测的是最新配置
    catch (e) { out.innerHTML = `<span class="tag red">保存失败</span> <span class="muted">${esc(e.message)}</span>`; return; }
    try {
      const r = await post("/api/config/test");
        out.innerHTML = (r.results || []).map(one => one.ok
          ? `<div><span class="tag green">${esc(one.site)} 连接成功</span> <span class="muted">${one.probe === "chat" ? "对话探测成功，配置模型" : "平台可用模型"} ${one.models.length} 个</span></div>`
        : `<div><span class="tag red">${esc(one.site)} 连接失败</span> <span class="muted">${esc(one.error || "")}</span></div>`).join("");
    } catch (e) { out.innerHTML = `<span class="tag red">连接失败</span> <span class="muted">${esc(e.message)}</span>`; }
  };
});

// ---------------------------------------------------------------- 项目 / 图片集
route("datasets", async () => {
  const [projects, cfg] = await Promise.all([get("/api/projects"), get("/api/config")]);
  const scope = currentProject();
  // 选了具体项目时，这一页收口成"这个项目下的图片集"，
  // 项目清单留给「全部项目」视图；否则用户在这里点了另一个项目，
  // 页面标题和右上角上下文会对不上。
  const scoped = projects.items.filter(p => p.name === scope);
  const keyWarn = !(cfg.api.sites || []).some(s => (s.api_keys_masked || []).length)
    ? `<div class="msg err">尚未配置 API Key，请先前往 <a href="#/config">配置页</a> 填写。</div>` : "";
  $("#app").innerHTML = `
  <div class="page-title">${scope ? `项目与图片集 · ${esc(scope)}` : "项目与图片集"}</div>
  ${keyWarn}
  ${scope ? `<div class="scope-bar" role="note">
    <span class="tag green">当前项目</span>
    <span>只显示「${esc(scope)}」下的图片集。</span>
    <button class="btn small" type="button" id="pj-show-all">查看全部项目</button>
  </div>` : ""}
  ${scope ? "" : `<div class="card">
    <h3>新建项目</h3>
    <div class="row">
      <div><label class="f">项目名称</label><input type="text" id="pj-name" placeholder="如：城市治理算法评测"></div>
      <div><label class="f">项目说明</label><input type="text" id="pj-desc" placeholder="可选"></div>
      <div class="u-f0"><button class="btn primary" id="pj-create">创建项目</button></div>
    </div>
    <div class="muted">先进入项目，再创建和导入该项目下的图片集。旧图片集自动显示在“未归档项目”中。</div>
  </div>`}
  ${scope ? `
  <div class="card">
    <div class="row u-ai-c">
      <h3 class="u-f2 u-m0">图片集 <span class="tag blue">${scoped.reduce((n, p) => n + p.dataset_count, 0)}</span></h3>
      <div class="u-f1"><input type="text" id="pj-search" placeholder="搜索图片集…" aria-label="搜索图片集"></div>
      <a class="btn small" href="#/project/${encodeURIComponent(scope)}">进入项目详情</a>
    </div>
    <div class="dataset-list u-mt-10" id="pj-list"></div>
  </div>` : `
  <div class="card">
    <div class="row u-ai-c">
      <h3 class="u-f2 u-m0">全部项目 <span class="tag blue">${projects.items.length}</span></h3>
      <div class="u-f1"><input type="text" id="pj-search" placeholder="搜索项目…" aria-label="搜索项目"></div>
    </div>
    <div class="project-list u-mt-10" id="pj-list"></div>
  </div>`}`;
  const renderProjects = () => {
    const q = ($("#pj-search").value || "").trim().toLowerCase();
    if (scope) {
      // 项目视图：这一页就是"当前项目下的图片集"，不再多一层项目行，
      // 否则用户点进来还要再点一次才能看到图片集。
      const rows = scoped.flatMap(p => p.datasets || [])
        .filter(d => !q || d.name.toLowerCase().includes(q));
      $("#pj-list").innerHTML = rows.map(d => `<div class="dataset-row" data-ref="${esc(d.ref)}">
        <div class="dataset-icon">▧</div><div class="dataset-main"><h3>${esc(d.name)}</h3>
        <div class="split-summary">${Object.entries(d.split_counts || {}).map(([k, v]) => `<span>${esc(k)} ${v}</span>`).join("") || '<span>尚未分组</span>'}</div></div>
        <div class="project-stat"><b>${d.count}</b><span>图片</span></div><span class="project-arrow">›</span></div>`).join("")
        || emptyState(`「${scope}」还没有图片集，去项目详情里创建或导入`, "进入项目详情", `#/project/${encodeURIComponent(scope)}`);
      $$("#pj-list [data-ref]").forEach(x => x.onclick = () =>
        location.hash = "#/datasetDetail/" + encodeURIComponent(x.dataset.ref));
      return;
    }
    const shown = projects.items.filter(p => !q || p.name.toLowerCase().includes(q));
    $("#pj-list").innerHTML = shown.map(p => `<div class="project-row" data-project="${esc(p.name)}">
      <div class="project-icon">▣</div><div class="project-main"><h3>${esc(p.name)}</h3>
      <div class="muted">${esc(p.description || "暂无说明")}</div></div>
      <div class="project-stat"><b>${p.dataset_count}</b><span>图片集</span></div>
      <div class="project-stat"><b>${p.image_count}</b><span>图片</span></div><span class="project-arrow">›</span></div>`).join("") || emptyState("还没有项目，用上方「新建项目」建第一个", "去填写名称", null, "pj-name");
    $$("#pj-list [data-project]").forEach(x => x.onclick = () => location.hash = "#/project/" + encodeURIComponent(x.dataset.project));
  };
  renderProjects();
  $("#pj-search").oninput = renderProjects;
  if ($("#pj-show-all")) $("#pj-show-all").onclick = () => setProject(PROJECT_ALL);
  if ($("#pj-create")) $("#pj-create").onclick = async () => {
    const name = $("#pj-name").value.trim();
    if (!name) return toast("请填写名称", false);
    try { await post("/api/projects", { name, description: $("#pj-desc").value }); location.hash = "#/project/" + encodeURIComponent(name); }
    catch (e) { toast(e.message, false); }
  };
});

route("project", async (name) => {
  if (!name) return location.hash = "#/datasets";
  name = decodeURIComponent(name);
  setProject(name, { rerender: false });
  const p = await get(`/api/projects/${encodeURIComponent(name)}`);
  $("#app").innerHTML = `<div class="page-title"><a href="#/datasets">项目</a> / ${esc(name)}</div>
    ${p.legacy ? `<div class="msg info">这里是升级前图片集的兼容入口。新图片集请在独立项目中创建。</div>` : `<div class="card"><h3>新建 / 导入图片集</h3><div class="row">
      <div><label class="f">图片集名称</label><input type="text" id="pd-name" placeholder="如：头盔检测验证集"></div>
      <div><label class="f">本机目录（可选）</label><input type="text" id="pd-path" placeholder="如：D:\\图片\\批次1"></div>
      <div class="u-f0"><button class="btn primary" id="pd-create">创建 / 导入</button></div></div></div>`}
    <div class="card"><div class="row u-ai-c"><h3 class="u-f2 u-m0">图片集 <span class="tag blue">${p.dataset_count}</span></h3>
      <div class="u-f1"><input type="text" id="pd-search" placeholder="搜索图片集…" aria-label="搜索图片集"></div>
      ${!p.legacy && !p.dataset_count ? `<button class="btn small danger u-f0" id="pd-del-project">删除空项目</button>` : ""}
      </div><div class="dataset-list u-mt-10" id="pd-list"></div></div>`;
  const render = () => {
    const q = ($("#pd-search").value || "").trim().toLowerCase();
    const rows = p.datasets.filter(d => !q || d.name.toLowerCase().includes(q));
    $("#pd-list").innerHTML = rows.map(d => `<div class="dataset-row" data-ref="${esc(d.ref)}">
      <div class="dataset-icon">▧</div><div class="dataset-main"><h3>${esc(d.name)}</h3>
      <div class="split-summary">${Object.entries(d.split_counts || {}).map(([k,v]) => `<span>${esc(k)} ${v}</span>`).join("") || '<span>尚未分组</span>'}</div></div>
      <div class="project-stat"><b>${d.count}</b><span>图片</span></div><span class="project-arrow">›</span></div>`).join("") || (p.legacy ? emptyState("兼容入口不含新图片集，请到独立项目中创建", "去项目列表", "#/datasets") : emptyState("这个项目还没有图片集，用上方表单创建或导入", "去填写名称", null, "pd-name"));
    $$("#pd-list [data-ref]").forEach(x => x.onclick = () => location.hash = "#/datasetDetail/" + encodeURIComponent(x.dataset.ref));
  };
  render(); $("#pd-search").oninput = render;
  if ($("#pd-create")) $("#pd-create").onclick = async () => {
    const dsName = $("#pd-name").value.trim(); if (!dsName) return toast("请填写图片集名称", false);
    try { const created = await post("/api/datasets", { name: dsName, project: name }); const path = $("#pd-path").value.trim(); if (path) await post(`/api/datasets/${encodeURIComponent(created.ref)}/import`, { path }); location.hash = "#/datasetDetail/" + encodeURIComponent(created.ref); }
    catch (e) { toast(e.message, false); }
  };
  if ($("#pd-del-project")) $("#pd-del-project").onclick = async () => {
    if (!(await confirmDlg(`确定删除空项目「${name}」？`, { title: "删除空项目" }))) return;
    try { await del(`/api/projects/${encodeURIComponent(name)}`); location.hash = "#/datasets"; }
    catch (e) { toast(e.message, false); }
  };
});

// ---------------------------------------------------------------- 图片集详情
route("datasetDetail", async (name) => {
  if (!name) { location.hash = "#/datasets"; return; }
  name = decodeURIComponent(name);
  adoptProjectOf({ ref: name });
  const r = await get(`/api/datasets/${encodeURIComponent(name)}/images`);
  const images = r.items;
  const refParts = name.includes("::") ? name.split("::") : ["未归档项目", name];
  $("#app").innerHTML = `
  <div class="page-title"><a href="#/datasets">项目</a> / <a href="#/project/${encodeURIComponent(refParts[0])}">${esc(refParts[0])}</a> / ${esc(refParts[1])} <span class="tag blue">${images.length} 张</span></div>
  <div class="card">
    <div class="row u-ai-c">
      <div class="u-f2"><input type="text" id="dd-search" placeholder="搜索图片名…" aria-label="搜索图片名"></div>
      <div><select id="dd-split-filter"><option value="">全部分组</option>${["未分组","优化集","验证集","测试集","回归集"].map(s => `<option>${s}</option>`).join("")}</select></div>
      <div class="u-f0"><label class="btn primary u-m0">上传图片
        <input class="u-hide" type="file" multiple accept="image/*" id="dd-up"></label></div>
      <div class="u-f0"><button class="btn danger" id="dd-del">删除图片集</button></div>
      <div class="u-f0"><a class="btn" href="#/project/${encodeURIComponent(refParts[0])}">返回项目</a></div>
    </div>
    <div class="row batch-row u-mt-8"><div class="muted batch-note">缩略图按原比例完整显示；点击放大。新运行和新真值任务会保存独立原图快照。</div>
      <div class="batch-split"><select id="dd-batch-split">${["未分组","优化集","验证集","测试集","回归集"].map(s => `<option>${s}</option>`).join("")}</select></div>
      <div class="batch-apply"><button class="btn" id="dd-batch-apply">把当前筛选图片批量分组</button></div></div>
  </div>
  <div class="thumb-grid" id="dd-grid"></div>`;
  const filteredImages = () => {
    const q = ($("#dd-search").value || "").trim().toLowerCase();
    const split = $("#dd-split-filter").value;
    return images.filter(i => (!q || i.rel.toLowerCase().includes(q)) && (!split || i.split === split));
  };
  const renderGrid = () => {
    const shown = filteredImages();
    const grid = $("#dd-grid");
    grid.innerHTML = "";
    if (!shown.length) { grid.innerHTML = '<div class="muted">无匹配图片</div>'; return; }
    // 大图片集分批插入：先出首屏，再按帧补齐，避免一次性重排造成长时间白屏
    const CHUNK = 120;
    let cursor = 0;
    let painted = 0;
    const paint = () => {
      const slice = shown.slice(cursor, cursor + CHUNK);
      cursor += CHUNK;
      painted += slice.length;
      grid.insertAdjacentHTML("beforeend", slice.map(i => `
      <div class="thumb">
        <img src="/api/file/dataset/${enc(name)}/${enc(i.rel)}" loading="lazy" data-zoom="${esc(i.rel)}">
        <button class="del" data-del="${esc(i.rel)}" title="删除此图">×</button>
        <div class="tn" title="${esc(i.rel)}">${esc(i.rel)}</div>
        <select class="thumb-split" data-split="${esc(i.rel)}">${["未分组","优化集","验证集","测试集","回归集"].map(s => `<option ${i.split === s ? "selected" : ""}>${s}</option>`).join("")}</select>
      </div>`).join(""));
      if (painted < shown.length) requestAnimationFrame(paint);
    };
    paint();
    // 事件委托统一处理，第二遍在全部插入后绑定（增量渲染下一次性绑定最新节点）
    const bindGrid = () => {
    $$("#dd-grid [data-split]").forEach(sel => sel.onchange = async (e) => {
      e.stopPropagation();
      try { await put(`/api/datasets/${encodeURIComponent(name)}/split`, { rel: sel.dataset.split, split: sel.value }); const row = images.find(x => x.rel === sel.dataset.split); if (row) row.split = sel.value; toast("数据分组已更新"); }
      catch (err) { toast(err.message, false); }
    });
    $$("#dd-grid [data-del]").forEach(b => b.onclick = async () => {
      if (!(await confirmDlg(`确定删除图片「${b.dataset.del}」？\n新运行和新真值任务已有原图快照；升级前未保存快照的旧记录可能无法再显示原图。`, { title: "删除图片" }))) return;
      try {
        await del(`/api/datasets/${encodeURIComponent(name)}/image?rel=${encQ(b.dataset.del)}`);
        toast("已删除");
        const idx = images.findIndex(x => x.rel === b.dataset.del);
        if (idx >= 0) images.splice(idx, 1);
        renderGrid();
      } catch (e) { toast(e.message, false); }
    });
    };
    // 全部节点插入后再绑定，避免中途节点漏绑
    const bindWhenDone = () => {
      if (painted < shown.length) return requestAnimationFrame(bindWhenDone);
      bindGrid();
    };
    requestAnimationFrame(bindWhenDone);
  };
  renderGrid();
  $("#dd-search").oninput = renderGrid;
  $("#dd-split-filter").onchange = renderGrid;
  $("#dd-batch-apply").onclick = async () => {
    const shown = filteredImages();
    if (!shown.length) return toast("当前筛选没有图片", false);
    if (!(await confirmDlg(`确定把当前 ${shown.length} 张图片设为「${$("#dd-batch-split").value}」？`, { title: "批量设置拆分" }))) return;
    const button = $("#dd-batch-apply"); button.disabled = true;
    let done = 0;
    try {
      for (const image of shown) {
        await put(`/api/datasets/${encodeURIComponent(name)}/split`, { rel: image.rel, split: $("#dd-batch-split").value });
        image.split = $("#dd-batch-split").value; done++;
      }
      toast(`已更新 ${done} 张`); renderGrid();
    } catch (e) { toast(`已更新 ${done} 张；${e.message}`, false); }
    button.disabled = false;
  };
  $("#dd-up").onchange = async (e) => {
    const inp = e.target;
    if (!inp.files.length) return;
    const fd = new FormData();
    for (const f of inp.files) fd.append("files", f);
    fd.append("sub", "");
    try {
      const r2 = await api(`/api/datasets/${encodeURIComponent(name)}/upload`, { method: "POST", body: fd });
      toast(`已上传 ${r2.count} 张`);
      const fresh = await get(`/api/datasets/${encodeURIComponent(name)}/images`);
      images.length = 0;
      images.push(...fresh.items);
      renderGrid();
    } catch (e2) { toast(e2.message, false); }
  };
  $("#dd-del").onclick = async () => {
    if (!(await confirmDlg(`确定删除整个图片集「${name}」？共 ${images.length} 张图片。`, { title: "删除图片集" }))) return;
    try { await del(`/api/datasets/${encodeURIComponent(name)}`); location.hash = `#/project/${encodeURIComponent(refParts[0])}`; }
    catch (e) { toast(e.message, false); }
  };
});

// ---------------------------------------------------------------- 提示词库
const pCollapsed = new Set();  // 记住分组折叠状态（页面内）

route("prompts", async () => {
  const ps = await get("/api/prompts");
  const groups = {};
  ps.items.forEach(p => { const g = p.group || ""; (groups[g] = groups[g] || []).push(p); });
  const gnames = Object.keys(groups).sort((a, b) =>
    (a === "" ? 1 : 0) - (b === "" ? 1 : 0) || a.localeCompare(b, "zh"));
  const groupHtml = gnames.map(g => {
    const items = groups[g];
    const collapsed = pCollapsed.has(g || "\0");
    return `
    <div class="p-group" data-g="${esc(g)}">
      <div class="p-group-head" data-g="${esc(g)}">
        <span class="p-group-arrow">${collapsed ? "▸" : "▾"}</span>
        <span class="u-f1">${g ? esc(g) : "未分组"}</span>
        <span class="tag">${items.length}</span>
      </div>
      <div class="p-group-items" style="display:${collapsed ? "none" : ""}">
        ${items.map(p => `
        <div class="img-item" data-p="${esc(p.name)}">
          <div class="u-f1 u-minw-0">
            <div class="u-ellipsis">${esc(p.name)}</div>
            <div class="muted u-fs-xs">${p.version_count || 0} 个版本${p.best_accuracy != null ? ` · 最优 ${(p.best_accuracy * 100).toFixed(1)}%` : ""}</div>
          </div>
          <span class="tag blue">${p.latest ? "V" + p.latest : ""}</span>
          ${p.latest_status ? `<span class="tag ${p.latest_status === "released" ? "green" : p.latest_status === "archived" ? "" : "orange"}">${esc(p.latest_status)}</span>` : ""}
        </div>`).join("")}
      </div>
    </div>`;
  }).join("");
  $("#app").innerHTML = `
  <div class="page-title">提示词库</div>
  ${sharedScopeBar("提示词库不属于单个项目，所有项目共用同一套提示词与版本。")}
  <div class="grid u-gtc-260">
    <div>
      <div class="card">
        <div class="row u-ai-c u-mb-8">
          <h3 class="u-f1 u-m0">提示词</h3>
          <span class="tag blue">${ps.items.length}</span>
        </div>
        <input class="u-mb-8" type="text" id="p-search" placeholder="搜索提示词…" aria-label="搜索提示词">
        <div id="p-list">
          ${groupHtml || emptyState("还没有提示词", "去填写名称", null, "p-new")}
        </div>
        <hr class="u-hr u-my-10">
        <input class="u-mb-6" type="text" id="p-new" placeholder="新提示词名称">
        <input class="u-mb-6" type="text" id="p-new-group" placeholder="分组（可留空，可选已有或新建）"
               autocomplete="off" data-suggest="${esc(JSON.stringify(gnames.filter(Boolean)))}">
        <label class="f u-fx u-ai-c u-gap-6 u-mb-8 u-fw-400">
          <input class="u-w-auto" type="checkbox" id="p-new-tpl"  checked disabled> 使用五模块骨架与最小 JSON 协议
        </label>
        <button class="btn primary u-w-full"  id="p-create">创建提示词</button>
      </div>
    </div>
    <div id="p-detail"><div class="card muted">← 选择左侧提示词查看与编辑</div></div>
  </div>`;
  $("#p-search").oninput = () => {
    const q = $("#p-search").value.trim().toLowerCase();
    $$("#p-list .p-group").forEach(g => {
      let hit = 0;
      $$(".img-item", g).forEach(it => {
        const show = !q || it.dataset.p.toLowerCase().includes(q);
        setShown(it, show);
        if (show) hit++;
      });
      // 搜索时强制展开有命中的分组，隐藏无命中的分组
      setShown(g, hit);
      setShown($(".p-group-items", g), q || !pCollapsed.has(g.dataset.g || "\0"));
      $(".p-group-arrow", g).textContent =
        (q || !pCollapsed.has(g.dataset.g || "\0")) ? "▾" : "▸";
    });
  };
  $("#p-create").onclick = async () => {
    const name = $("#p-new").value.trim();
    if (!name) return toast("请填写名称", false);
    try {
      await post("/api/prompts", {
        name,
        group: $("#p-new-group").value.trim(),
        use_template: $("#p-new-tpl").checked,
      });
      toast("已创建"); navigate();
    }
    catch (e) { toast(e.message, false); }
  };
  $$("#p-list .p-group-head").forEach(h => h.onclick = () => {
    const key = h.dataset.g || "\0";
    if (pCollapsed.has(key)) pCollapsed.delete(key); else pCollapsed.add(key);
    const items = h.parentElement.querySelector(".p-group-items");
    const collapsed = pCollapsed.has(key);
    setShown(items, !collapsed);
    h.querySelector(".p-group-arrow").textContent = collapsed ? "▸" : "▾";
  });
  $$("#p-list .img-item").forEach(it =>
    it.onclick = () => showPromptDetail(it.dataset.p));
});

async function showPromptDetail(name, showV) {
  const ps = await get("/api/prompts");
  const p = ps.items.find(x => x.name === name);
  if (!p) return;
  $$("#p-list .img-item").forEach(it => it.classList.toggle("active", it.dataset.p === name));
  const v = showV || p.latest;
  const [ver, settings, dsList, cfg, tpl, best] = await Promise.all([
    get(`/api/prompts/${encodeURIComponent(name)}/versions/${v}`),
    get(`/api/prompts/${encodeURIComponent(name)}/settings`),
    get("/api/datasets"),
    get("/api/config"),
    get("/api/prompts/template"),
    get(`/api/prompts/${encodeURIComponent(name)}/best?metric=accuracy`),
  ]);
  const isCustom = settings.output_mode === "custom";
  const structuredReady = !!(ver.sections && ver.sections.output_format);
  const versionInfo = ver.info || {};
  const box = $("#p-detail");
  const metaParts = [versionInfo.note || "", versionInfo.created || "", `${versionInfo.chars || 0} 字`].filter(Boolean);
  box.innerHTML = `
  <div class="card">
    <div class="prompt-head">
      <h3>${esc(name)}</h3>
      <div class="tabs u-m0 tabs-inline" id="p-vtabs">${p.versions.map(x =>
        `<div class="tab ${x.version === v ? "active" : ""}" data-v="${x.version}" title="${esc(x.note || "")}">V${x.version}</div>`).join("")}</div>
    </div>
    <div class="row u-ai-c u-my-6">
      <div class="muted u-f3">${esc(metaParts.join(" · "))}
        <span class="tag blue">${esc(versionInfo.branch || "main")}</span><span class="tag ${versionInfo.status === "released" ? "green" : versionInfo.status === "archived" ? "red" : "orange"}">${esc(versionInfo.status || "draft")}</span>
        ${best.version ? `<span class="tag green">当前最优 V${best.version} · ${(best.value*100).toFixed(1)}%</span>` : ""}</div>
      <div class="u-f2 u-fx u-ai-c u-gap-6">
        <span class="muted u-fnone">分组</span>
        <input class="u-m0" type="text" id="p-group" value="${esc(p.group || "")}" placeholder="未分组"
               autocomplete="off" data-suggest="${esc(JSON.stringify([...new Set(ps.items.map(x => x.group).filter(Boolean))]))}">
      </div>
    </div>
    <div class="row u-my-10 u-mb-8 u-ai-c">
 <div class="tabs sm u-m0 u-f0" id="p-edit-tabs"><div class="tab" data-edit="structured">五模块展开</div><div class="tab active" data-edit="raw">原文</div></div>
      <div class="u-f0"><button class="btn small" id="t-insert">插入标准输出格式</button></div>
      ${p.versions.length > 1 ? `<div class="u-f0"><button class="btn small danger" id="p-delver">删除当前版本 V${v}</button></div>` : ""}
        <div class="muted u-f3">自动优化只允许修改前四个模块，output_format 会做哈希校验并保持不变。</div>
    </div>
 <div id="p-structured" class="prompt-sections u-hide">
      ${PROMPT_SECTIONS.map(([key,title]) => `<div class="prompt-section ${key === "output_format" ? "locked-section" : ""}"><div class="prompt-section-head"><b>${esc(title)}</b>${key === "output_format" ? '<span class="tag green">自动优化锁定</span>' : ""}</div><textarea data-section="${key}" rows="${key === "output_format" ? 12 : 5}" placeholder="填写${esc(title)}">${esc((ver.sections || {})[key] || "")}</textarea></div>`).join("")}
    </div>
 <div id="p-raw"><textarea id="p-content" rows="20">${esc(ver.content)}</textarea></div>
    <div class="row u-mt-10">
      <div><label class="f">版本说明</label><input type="text" id="p-note" placeholder="改了什么，为什么改"></div>
      <div><label class="f">分支</label><input type="text" id="p-branch" value="${esc(versionInfo.branch || "main")}" placeholder="main / experiment-a"></div>
      <div><label class="f">预期效果</label><input type="text" id="p-effect" placeholder="预期降低哪类错误"></div>
      <div class="u-f0"><button class="btn primary" id="p-savever">保存为新版本 V${(p.latest || 0) + 1}</button></div>
    </div>
    <div class="row version-actions u-mt-8">
      <button class="btn small" id="p-release">发布当前版本</button><button class="btn small" id="p-archive">归档当前版本</button>
      <button class="btn small" id="p-rollback" title="以当前查看版本的内容创建一个新版本，历史版本全部保留">回滚到此版本</button>
      <button class="btn small" id="p-rename">重命名</button><button class="btn small" id="p-dup">复制副本</button>
      <button class="btn small danger" id="p-del">删除整个提示词</button>
      <div class="muted">历史版本内容不可覆盖；发布、回滚、合并均保留完整轨迹。</div>
    </div>
  </div>
  <div class="card">
    <div class="tabs u-mb-14" id="p-subtabs">
      <div class="tab active" data-sub="trial">快速试跑</div>
      <div class="tab" data-sub="settings">输出设置</div>
      <div class="tab" data-sub="diff">版本对比</div>
      <div class="tab" data-sub="merge">模块合并</div>
    </div>
    <div data-pane="trial">
      <div class="muted u-mb-8">用当前编辑器内容直接测几张图，不保存版本、不产生运行记录。</div>
      <div class="row">
        <div><label class="f">图片集</label><select id="tr-ds">${dsList.items.map(d =>
          `<option value="${esc(d.ref || d.name)}">${esc(d.project || "未归档项目")} / ${esc(d.name)}</option>`).join("")}</select></div>
        <div><label class="f">取图方式</label><select id="tr-mode">
          <option value="sample">随机抽取</option><option value="pick">手动选择</option></select></div>
        <div id="tr-nbox"><label class="f">张数（1-4）</label><input type="number" id="tr-n" value="2" min="1" max="4"></div>
        <div><label class="f">站点 / 模型</label><select id="tr-model">${smOptions(cfg)}</select></div>
        <div class="u-f0"><button class="btn primary" id="tr-go">开始试跑</button></div>
      </div>
      <div class="u-hide u-mt-8" id="tr-pickbox">
        <label class="f">选择图片（最多取前 4 张）</label>
        <select id="tr-images" multiple size="7"></select>
      </div>
      <div id="tr-out"></div>
    </div>
    <div class="u-hide" data-pane="settings">
      <div class="row">
        <div><label class="f">输出模式</label>
          <select id="s-mode">
            <option value="fixed" ${!isCustom ? "selected" : ""}>开放标准 JSON（scene_analysis/objects/analysis_summary）</option>
            <option value="custom" ${isCustom ? "selected" : ""}>完全自定义（按字段映射解析）</option>
          </select></div>
        <div class="u-f0"><button class="btn primary" id="s-save">保存设置</button></div>
      </div>
      <div class="row">
        <div><label class="f">二值结果标签（阳性/阴性）</label>
          <input type="text" id="s-positive" value="${esc((settings.status_labels || ["abnormal", "normal"])[0])}" placeholder="如：不合格 / 是"></div>
        <div><label class="f">二值结果标签（阴性）</label>
          <input type="text" id="s-negative" value="${esc((settings.status_labels || ["abnormal", "normal"])[1])}" placeholder="如：合格 / 否"></div>
      </div>
      <div class="muted">解析器会按此顺序把 true/1 归为第一个标签、false/0 归为第二个标签；模型返回的自定义标签会原样保留。</div>
      <div id="s-mapbox" style="display:${isCustom ? "" : "none"}">
        <div class="msg info u-my-10">完全自定义模式：输出不使用标准 head 时，按下面的映射告诉系统关键字段位置；
          其余字段会完整保留在结果的 custom 中，字段提取/评估可按任意路径使用（如 custom.缺陷列表[].类型）。</div>
        <div class="row">
          <div><label class="f">分类结论字段路径</label><input type="text" id="s-status" value="${esc(settings.map.status_field)}" placeholder="如：是否异常 / result.status"></div>
          <div><label class="f">目标列表字段路径</label><input type="text" id="s-objects" value="${esc(settings.map.objects_path)}" placeholder="如：缺陷列表"></div>
        </div>
        <div class="row">
          <div><label class="f">目标名称子字段</label><input type="text" id="s-name" value="${esc(settings.map.name_field)}" placeholder="如：类型"></div>
          <div><label class="f">目标框子字段</label><input type="text" id="s-bbox" value="${esc(settings.map.bbox_field)}" placeholder="如：位置"></div>
        </div>
      </div>
      <div class="muted" id="s-fixednote" style="display:${isCustom ? "none" : ""};margin-top:8px">
        输出格式建议使用最小协议；模型原始 JSON 和扩展字段会完整保存，系统不会修改你的提示词内容。</div>
    </div>
    <div class="u-hide" data-pane="diff">
      <div class="row">
        <div><label class="f">基准版本</label><select id="p-v1">${p.versions.map(x =>
          `<option value="${x.version}" ${x.version === v - 1 ? "selected" : ""}>V${x.version}</option>`).join("")}</select></div>
        <div><label class="f">对比版本</label><select id="p-v2">${p.versions.map(x =>
          `<option value="${x.version}" ${x.version === v ? "selected" : ""}>V${x.version}</option>`).join("")}</select></div>
        <div class="u-f0"><button class="btn" id="p-diff">对比</button></div>
      </div>
      <div class="u-mt-10" id="p-diffbox"></div>
    </div>
    <div class="u-hide" data-pane="merge">
      <div class="msg info">为每个模块选择来源版本。未选择的模块沿用最新版本；合并会创建新版本，不覆盖历史。</div>
      <div class="merge-grid">${PROMPT_SECTIONS.map(([key,title]) => `<div><label class="f">${esc(title)}</label><select data-merge="${key}"><option value="">沿用最新版本</option>${p.versions.map(x => `<option value="${x.version}">来自 V${x.version}</option>`).join("")}</select></div>`).join("")}</div>
      <div class="row u-mt-10"><input id="p-merge-note" placeholder="合并说明"><input id="p-merge-branch" value="main" placeholder="分支"><button class="btn primary" id="p-merge">创建合并版本</button></div>
    </div>
  </div>`;
  $$("#p-vtabs .tab", box).forEach(t => t.onclick = () => showPromptDetail(name, Number(t.dataset.v)));
 let promptEditMode = "raw";
  const sectionValues = () => Object.fromEntries($$("#p-structured [data-section]").map(area => [area.dataset.section, area.value]));
  const currentPromptContent = () => promptEditMode === "structured" ? composePromptSections(sectionValues()) : $("#p-content").value;
  $$("#p-edit-tabs .tab", box).forEach(tab => tab.onclick = async () => {
    const next = tab.dataset.edit;
    if (next === "raw" && promptEditMode === "structured") $("#p-content").value = composePromptSections(sectionValues());
    if (next === "structured" && promptEditMode === "raw") {
      try {
        const parsed = await post("/api/prompt-ai/parse-sections", { content: $("#p-content").value });
        if (!(parsed.recognized || []).length) return toast("原文中没有可识别的五模块标题，请先按 ROLE / TASK / DEFINITION / WORKFLOW / OUTPUT FORMAT 分段", false);
        $$("#p-structured [data-section]").forEach(area => area.value = (parsed.sections || {})[area.dataset.section] || "");
      } catch (e) { return toast(e.message, false); }
    }
    promptEditMode = next;
    $$("#p-edit-tabs .tab", box).forEach(item => item.classList.toggle("active", item === tab));
    setShown($("#p-structured"), next === "structured");
    setShown($("#p-raw"), next === "raw");
  });
  $("#p-group").onchange = async () => {
    try {
      await put(`/api/prompts/${encodeURIComponent(name)}/meta`, { group: $("#p-group").value.trim() });
      toast("分组已更新");
      await navigate();  // 刷新侧栏分组
      showPromptDetail(name, v);
    } catch (e) { toast(e.message, false); }
  };
  const delVerBtn = $("#p-delver");
  if (delVerBtn) delVerBtn.onclick = async () => {
    if (!(await confirmDlg(`确定删除「${name}」的 V${v}？\n历史运行中保存有提示词快照，删除不影响已产生的结果查看。`, { title: "删除版本" }))) return;
    try {
      await del(`/api/prompts/${encodeURIComponent(name)}/versions/${v}`);
      toast(`已删除 V${v}`);
      await navigate();
      showPromptDetail(name);
    } catch (e) { toast(e.message, false); }
  };
  $$("#p-subtabs .tab", box).forEach(t => t.onclick = () => {
    $$("#p-subtabs .tab", box).forEach(x => x.classList.toggle("active", x === t));
    $$("[data-pane]", box).forEach(pn => setShown(pn, pn.dataset.pane === t.dataset.sub));
  });
  $("#t-insert").onclick = async () => {
    if (promptEditMode === "structured") {
      const output = $('#p-structured [data-section="output_format"]');
      if (output.value.trim() && !(await confirmDlg("当前 output_format 已有内容，确定替换为最小协议？", { title: "替换输出格式" }))) return;
      output.value = tpl.reference;
    } else {
      const ta = $("#p-content");
      ta.value = ta.value.replace(/\s*$/, "") + "\n\n## OUTPUT FORMAT / 输出格式约束\n" + tpl.reference;
    }
    toast("已写入开放式标准 JSON 最小协议");
  };
  $("#s-mode").onchange = () => {
    const c = $("#s-mode").value === "custom";
    setShown($("#s-mapbox"), c);
    setShown($("#s-fixednote"), !c);
  };
  $("#s-save").onclick = async () => {
    try {
      await put(`/api/prompts/${encodeURIComponent(name)}/settings`, {
        output_mode: $("#s-mode").value,
        map: {
          status_field: $("#s-status").value.trim(),
          objects_path: $("#s-objects").value.trim(),
          name_field: $("#s-name").value.trim(),
          bbox_field: $("#s-bbox").value.trim(),
        },
        status_labels: [$("#s-positive").value.trim(), $("#s-negative").value.trim()],
      });
      toast("输出设置已保存（对之后新建的运行生效）");
    } catch (e) { toast(e.message, false); }
  };
  $("#p-savever").onclick = async () => {
    try {
      const sections = sectionValues();
      const changedModules = promptEditMode === "raw" ? PROMPT_SECTIONS.map(([key]) => key) :
        PROMPT_SECTIONS.filter(([key]) => (ver.sections || {})[key] !== sections[key]).map(([key]) => key);
      const body = { content: currentPromptContent(), note: $("#p-note").value, parent: v,
        branch: $("#p-branch").value.trim() || "main", change_summary: $("#p-note").value,
        expected_effect: $("#p-effect").value, changed_modules: changedModules };
      if (promptEditMode === "structured") body.sections = sections;
      const r = await post(`/api/prompts/${encodeURIComponent(name)}/versions`, body);
      toast(`已保存 V${r.version}`);
      showPromptDetail(name, r.version);
    } catch (e) { toast(e.message, false); }
  };
  $("#p-del").onclick = async () => {
    if (!(await confirmDlg(`确定删除提示词「${name}」全部版本？`, { title: "删除提示词" }))) return;
    try { await del(`/api/prompts/${encodeURIComponent(name)}`); navigate(); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-rename").onclick = async () => {
    const newName = await promptDlg("重命名提示词", name, { label: "新的提示词名称" });
    if (!newName || newName.trim() === name) return;
    try { await post(`/api/prompts/${encodeURIComponent(name)}/rename`, { new_name: newName.trim() }); toast("已重命名"); navigate(); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-dup").onclick = async () => {
    const newName = await promptDlg("创建副本", `${name}-副本`, { label: "副本名称" });
    if (!newName) return;
    try { await post(`/api/prompts/${encodeURIComponent(name)}/duplicate`, { new_name: newName.trim() }); toast("已创建副本"); navigate(); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-release").onclick = async () => {
    if (!(await confirmDlg(`确定发布 ${name} V${v}？此前发布版本会自动转为已测试。`, { title: "发布版本", danger: false }))) return;
    try { await put(`/api/prompts/${encodeURIComponent(name)}/versions/${v}`, { note: versionInfo.note || "", status: "released" }); toast("版本已发布"); showPromptDetail(name, v); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-archive").onclick = async () => {
    if (!(await confirmDlg(`确定归档 ${name} V${v}？`, { title: "归档版本" }))) return;
    try { await put(`/api/prompts/${encodeURIComponent(name)}/versions/${v}`, { note: versionInfo.note || "", status: "archived" }); toast("版本已归档"); showPromptDetail(name, v); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-rollback").onclick = async () => {
    if (!(await confirmDlg(`确定基于 V${v} 创建一个新的回滚版本？`, { title: "回滚版本", danger: false }))) return;
    try { const r = await post(`/api/prompts/${encodeURIComponent(name)}/rollback`, { target: v, note: `回滚到 V${v}` }); toast(`已创建 V${r.version}`); showPromptDetail(name, r.version); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-merge").onclick = async () => {
    const sources = {};
    $$("[data-merge]", box).forEach(select => { if (select.value) sources[select.dataset.merge] = Number(select.value); });
    if (!Object.keys(sources).length) return toast("请至少选择一个模块来源", false);
    try { const r = await post(`/api/prompts/${encodeURIComponent(name)}/merge`, { sources, note: $("#p-merge-note").value, branch: $("#p-merge-branch").value || "main" }); toast(`已创建合并版本 V${r.version}`); showPromptDetail(name, r.version); }
    catch (e) { toast(e.message, false); }
  };
  $("#p-diff").onclick = async () => {
    const v1 = $("#p-v1").value, v2 = $("#p-v2").value;
    try {
      const d = await get(`/api/prompts/${encodeURIComponent(name)}/diff?v1=${v1}&v2=${v2}`);
      let html = `<div class="muted u-mb-8">V${v1} → V${v2}：
        <span class="tag green">新增 ${d.summary.added} 行</span>
        <span class="tag red">删除 ${d.summary.deleted} 行</span>
        <span class="tag orange">修改 ${d.summary.changed} 行</span></div>
        <div class="module-diff">${PROMPT_SECTIONS.map(([key,title]) => `<div class="module-diff-item ${d.sections[key] && d.sections[key].changed ? "changed" : ""}"><b>${esc(title)}</b><span>${d.sections[key] && d.sections[key].changed ? "有修改" : "未修改"}</span></div>`).join("")}</div><div class="diff-box">`;
      for (const row of d.rows) {
        if (row.tag === "equal") {
          row.v1_lines.forEach((l, i) => html += diffLine(row.v1_start + i, " ", l, ""));
        } else {
          row.v1_lines.forEach((l, i) => html += diffLine(row.v1_start + i, "-", l, "del"));
          row.v2_lines.forEach((l, i) => html += diffLine(row.v2_start + i, "+", l, "add"));
        }
      }
      $("#p-diffbox").innerHTML = html + "</div>";
    } catch (e) { toast(e.message, false); }
  };

  // ---- 快速试跑：用编辑器当前内容直接调模型，不存版本、不产生运行记录
  const trMode = $("#tr-mode"), trDs = $("#tr-ds");
  const loadTrialImages = async () => {
    const sel = $("#tr-images");
    sel.innerHTML = `<option disabled>加载中…</option>`;
    try {
      const d = await get(`/api/datasets/${encodeURIComponent(trDs.value)}/images`);
      sel.innerHTML = d.items.map(i =>
        `<option value="${esc(i.rel)}">${esc(i.rel)}</option>`).join("")
        || `<option disabled>图片集为空</option>`;
    } catch (e) { sel.innerHTML = `<option disabled>${esc(e.message)}</option>`; }
  };
  trMode.onchange = () => {
    const pick = trMode.value === "pick";
    setShown($("#tr-pickbox"), pick);
    setShown($("#tr-nbox"), !pick);
    if (pick && !$("#tr-images").options.length) loadTrialImages();
  };
  trDs.onchange = () => { $("#tr-images").innerHTML = ""; if (trMode.value === "pick") loadTrialImages(); };
  $("#tr-go").onclick = async () => {
    const out = $("#tr-out");
    const content = currentPromptContent().trim();
    if (!content) return toast("编辑器内容为空", false);
    if (!trDs.value) return toast("请先创建图片集", false);
    const body = {
      dataset: trDs.value,
      prompt_content: content,
      ...smParse($("#tr-model").value),
      output_mode: $("#s-mode").value,
      map: {
        status_field: $("#s-status").value.trim(),
        objects_path: $("#s-objects").value.trim(),
        name_field: $("#s-name").value.trim(),
        bbox_field: $("#s-bbox").value.trim(),
      },
      status_labels: [$("#s-positive").value.trim(), $("#s-negative").value.trim()],
    };
    if (trMode.value === "pick") {
      body.images = $$("#tr-images option:checked").map(o => o.value).slice(0, 4);
      if (!body.images.length) return toast("请先选择图片", false);
    } else {
      body.sample = Math.min(Math.max(1, Number($("#tr-n").value) || 2), 4);
    }
    const btn = $("#tr-go");
    btn.disabled = true;
    out.innerHTML = `<div class="muted u-mt-10">正在调用模型，请稍候…（结果不落盘）</div>`;
    try {
      const r = await post("/api/trial", body);
      out.innerHTML = `<div class="muted u-mt-12 u-mb-2">试跑完成 · ${esc(r.model)} · ${r.count} 张</div>`
        + r.items.map(trialCard).join("");
    } catch (e) {
      out.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
    }
    btn.disabled = false;
  };
}

function trialCard(it) {
  const tag = it.error ? `<span class="tag red">调用失败</span>`
    : it.parse_ok ? statusTag(it.overall_status)
    : `<span class="tag orange">解析失败</span>`;
  const lat = it.latency != null ? `<span class="muted u-f0">${Number(it.latency).toFixed(1)}s</span>` : "";
  let body;
  if (it.error) {
    body = `<div class="msg err u-m0">${esc(it.error)}</div>`;
  } else {
    body = `<div class="panels">`
      + (it.annotated
        ? `<div class="panel"><h4>推理图（${it.object_count} 个目标）</h4><img src="${it.annotated}" data-zoom="1"></div>`
        : "")
      + `<div class="panel"><h4>解析结果</h4>${it.result ? resultPanel(it.result) : '<div class="json-view">（无）</div>'}</div>`
      + `</div>`;
    if (!it.parse_ok && it.raw) {
      body += `<details class="u-mt-8"><summary class="muted u-pointer">查看原始输出</summary>
        <div class="json-view u-mt-6">${esc(it.raw)}</div></details>`;
    }
  }
  return `<div class="trial-item">
    <div class="row"><h4 class="u-f2 u-m0">${esc(it.rel)}</h4>${tag}${lat}</div>${body}</div>`;
}
function diffLine(ln, sign, text, cls) {
  return `<div class="diff-line ${cls}"><div class="ln">${ln}</div><div class="lc">${sign} ${esc(text)}</div></div>`;
}

function distTable(title, dist) {
  const entries = Object.entries(dist || {});
  const head = `<h4 class="u-fs-sm u-c-text2 u-m-0-0-6">${esc(title)}</h4>`;
  if (!entries.length) return `<div>${head}<div class="muted">无数据</div></div>`;
  const max = Math.max(...entries.map(e => e[1]), 1);
  const total = entries.reduce((a, e) => a + e[1], 0);
  return `<div>${head}${entries.map(([k, v]) => `
    <div class="u-fx u-ai-c u-gap-6 u-fs-sm u-mb-3">
      <span class="u-f-0-0-90 u-ellipsis"  title="${esc(k)}">${esc(k)}</span>
      <span class="u-bar-track"><i style="display:block;height:100%;width:${(v / max * 100).toFixed(1)}%;background:var(--primary)"></i></span>
      <span class="muted u-f-0-0-70 u-ta-r">${v} · ${(v / total * 100).toFixed(0)}%</span>
    </div>`).join("")}</div>`;
}

// ---------------------------------------------------------------- 运行测试
const rCollapsed = new Set();  // 运行记录分组折叠状态（页面内）
route("runs", async () => {
  const [runs, ds, ps, cfg] = await Promise.all([
    get("/api/runs"), get("/api/datasets"), get("/api/prompts"), get("/api/config")]);
  const promptOpts = ps.items.map(p => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join("");
  $("#app").innerHTML = `
  <div class="page-title">运行测试</div>
  ${projectScopeBar("新建运行只列出当前项目的图片集；下方运行记录也只显示当前项目。")}
  <div class="card">
    <h3>新建测试运行</h3>
    <div class="row">
      <div class="row-wide"><label class="f">图片集</label><select id="r-ds">${projectDatasets(ds.items).map(d =>
        `<option value="${esc(d.ref || d.name)}">${esc(d.project || "未归档项目")} / ${esc(d.name)}</option>`).join("")
        || `<option value="">当前项目下没有图片集</option>`}</select></div>
      <div><label class="f">数据分组</label><select id="r-split"><option value="">全部图片</option><option>优化集</option><option>验证集</option><option>测试集</option><option>回归集</option><option>未分组</option></select></div>
      <div class="row-wide"><label class="f">提示词</label><select id="r-p">${promptOpts}</select></div>
      <div><label class="f">版本</label><select id="r-pv"></select></div>
      <div><label class="f">站点 / 模型</label><select id="r-model">${smOptions(cfg)}</select></div>
    </div>
    <div class="row">
      <div><label class="f">重复次数 N（稳定性测试）</label><input type="number" id="r-repeat" value="1" min="1" max="100"></div>
      <div><label class="f">并发数</label><input type="number" id="r-conc" value="${cfg.defaults.concurrency}" min="1" max="20"></div>
      <div><label class="f">temperature（空=默认）</label><input type="text" id="r-temp"></div>
      <div><label class="f">seed（空=默认）</label><input type="text" id="r-seed"></div>
    </div>
    <div class="row u-mt-12 u-ai-c">
      <div class="u-f0"><button class="btn primary" id="r-create">创建并运行</button></div>
      <div class="muted u-f2" id="r-totalhint"></div>
    </div>
  </div>
  <div class="card">
    <h3>运行记录</h3>
    <div id="r-list"></div>
  </div>`;

  const pvSel = $("#r-pv");
  const updPV = () => {
    const p = ps.items.find(x => x.name === $("#r-p").value);
    pvSel.innerHTML = p ? p.versions.map(v =>
      `<option value="${v.version}" ${v.version === p.latest ? "selected" : ""}>V${v.version}</option>`).join("") : "";
  };
  $("#r-p").onchange = updPV; updPV();

  const updTotal = () => {
    const d = ds.items.find(x => (x.ref || x.name) === $("#r-ds").value);
    const n = Number($("#r-repeat").value) || 1;
    const conc = Math.max(1, Number($("#r-conc").value) || 1);
    const split = $("#r-split").value;
    const count = d ? (split ? ((d.split_counts || {})[split] || 0) : d.count) : 0;
    if (!count) { $("#r-totalhint").textContent = ""; return; }
    const calls = count * n;
    // 按每张图每次调用约 5 秒估算，并发摊薄总时长
    const secs = Math.ceil(calls * 5 / conc);
    const timeStr = secs < 60 ? `约 ${secs} 秒`
      : secs < 3600 ? `约 ${Math.ceil(secs / 60)} 分钟`
      : `约 ${Math.floor(secs / 3600)} 小时 ${Math.ceil((secs % 3600) / 60)} 分钟`;
    $("#r-totalhint").textContent = `共 ${count} 张图 × ${n} 次 = ${calls} 次模型调用，预计 ${timeStr}（按每次 5 秒、并发 ${conc} 估算）`;
  };
  $("#r-ds").onchange = updTotal;
  $("#r-split").onchange = updTotal;
  $("#r-repeat").oninput = updTotal;
  $("#r-conc").oninput = updTotal;
  updTotal();

  // 从「裁判与优化」保存新版本后跳转过来：预填图片集与新版本，直接验证
  if (state._runPreselect) {
    const pre = state._runPreselect;
    state._runPreselect = null;
    if (pre.dataset && [...$("#r-ds").options].some(o => o.value === pre.dataset)) $("#r-ds").value = pre.dataset;
    if (pre.prompt_name && [...$("#r-p").options].some(o => o.value === pre.prompt_name)) {
      $("#r-p").value = pre.prompt_name;
      updPV();
      if (pre.prompt_version && [...pvSel.options].some(o => o.value === String(pre.prompt_version))) pvSel.value = String(pre.prompt_version);
    }
    if (pre.split) $("#r-split").value = pre.split;
    updTotal();
    toast(`已预填优化后的 V${pre.prompt_version}，确认参数后直接运行验证`);
  }

  $("#r-create").onclick = async () => {
    if ($("#r-create").disabled) return;
    const sm = smParse($("#r-model").value);
    const body = {
      dataset: $("#r-ds").value, prompt_name: $("#r-p").value,
      prompt_version: Number(pvSel.value), model: sm.model, site: sm.site,
      repeat: Number($("#r-repeat").value) || 1,
      concurrency: Number($("#r-conc").value) || 3,
      split: $("#r-split").value || null,
      temperature: $("#r-temp").value.trim() === "" ? null : Number($("#r-temp").value),
      seed: $("#r-seed").value.trim() === "" ? null : Number($("#r-seed").value),
    };
    if (!body.prompt_name) return toast("请先创建提示词", false);
    try {
      $("#r-create").disabled = true;
      const r = await post("/api/runs", body);
      toast("已开始运行");
      location.hash = "#/viewer/" + r.id;
    } catch (e) { toast(e.message, false); }
    finally { const b = $("#r-create"); if (b) b.disabled = false; }
  };

  async function refresh() {
    try {
      const data = await get("/api/runs");
      data.items = projectRuns(data.items);
      const hasActiveRun = data.items.some(r => r.status === "running" || r.is_active);
      // 按「图片集 + 提示词」分组，同组合的多次运行折叠在一起
      const groups = {};
      data.items.forEach(r => {
        const key = `${r.dataset}||${r.prompt_name}`;
        (groups[key] = groups[key] || []).push(r);
      });
      const rowHtml = (r) => {
        return `<tr>
        <td class="mono u-fs-xs"><a href="#/viewer/${r.id}">${esc(r.id)}</a><br>
          <span class="muted">${esc(r.dataset_name || r.dataset)}${r.dataset_split ? ` · ${esc(r.dataset_split)}` : ""} · ×${r.repeat}</span></td>
        <td><span class="tag blue">V${r.prompt_version}</span></td>
        <td class="muted">${esc(r.site ? r.site + " / " : "")}${esc(r.model)}</td>
        <td class="u-minw-170"><div class="progress-wrap">${progressBar((r.done || 0) + (r.failed || 0), r.total, r.failed, r.parse_failed)}</div></td>
        <td>${statusTag(r.status)}</td>
        <td>
          <button class="btn small" data-clone="${r.id}">克隆</button>
          ${r.status === "running" || r.is_active ? `<button class="btn small" data-stop="${r.id}">停止</button>` : ""}
          ${["stopped", "failed", "done", "pending", "interrupted"].includes(r.status) && r.done + r.failed < r.total
            ? `<button class="btn small" data-start="${r.id}">继续</button>` : ""}
          ${r.parse_failed ? `<button class="btn small" data-reparse="${r.id}" title="用当前解析器重试这些接口已返回、但 JSON 未能解析的结果；原文件会先备份">重新解析 ${r.parse_failed}</button>` : ""}
          <button class="btn small danger" data-del="${r.id}">删除</button>
        </td></tr>`;
      };
      const gkeys = Object.keys(groups);
      if (!gkeys.length) {
        $("#r-list").innerHTML = currentProject()
          ? emptyState(`「${currentProject()}」还没有运行记录——用上方表单创建第一次运行`, "去选择图片集", null, "r-ds")
          : emptyState("还没有运行记录——用上方表单创建第一次运行", "去选择图片集", null, "r-ds");
        return;
      }
      $("#r-list").innerHTML = gkeys.map(key => {
        const items = groups[key];
        const first = items[0];
        const collapsed = rCollapsed.has(key);
        return `<div class="p-group">
          <div class="p-group-head" data-rg="${esc(key)}">
            <span class="p-group-arrow">${collapsed ? "▸" : "▾"}</span>
            <span class="u-f1"><b>${esc(first.dataset_project || "未归档项目")} / ${esc(first.dataset_name || first.dataset)}</b>
              <span class="muted">+</span> ${esc(first.prompt_name)}</span>
            <span class="tag">${items.length} 次运行</span>
          </div>
          <div class="p-group-items" style="display:${collapsed ? "none" : ""}">
            <div class="tbl-scroll"><table class="tbl"><thead><tr>
              <th>运行 ID</th><th>版本</th><th>站点 / 模型</th><th>进度</th><th>状态</th><th>操作</th>
            </tr></thead><tbody>${items.map(rowHtml).join("")}</tbody></table></div>
          </div>
        </div>`;
      }).join("") || emptyState("还没有运行记录——用上方表单创建第一次运行", "去选择图片集", null, "r-ds");
      $$("#r-list [data-rg]").forEach(h => h.onclick = () => {
        const key = h.dataset.rg;
        if (rCollapsed.has(key)) rCollapsed.delete(key); else rCollapsed.add(key);
        const items = h.parentElement.querySelector(".p-group-items");
        const collapsed = rCollapsed.has(key);
    setShown(items, !collapsed);
        h.querySelector(".p-group-arrow").textContent = collapsed ? "▸" : "▾";
      });
      $$("#r-list [data-clone]").forEach(b => b.onclick = () => {
        const r = data.items.find(x => x.id === b.dataset.clone);
        if (!r) return;
        $("#r-ds").value = r.dataset;
        $("#r-p").value = r.prompt_name;
        updPV();
        pvSel.value = r.prompt_version;
        const mv = r.site ? `${r.site}::${r.model}` : "";
        const msel = $("#r-model");
        msel.value = mv;
        if (msel.value !== mv) {
          const opt = Array.from(msel.options).find(o => o.value.endsWith(`::${r.model}`));
          if (opt) msel.value = opt.value;
        }
        $("#r-repeat").value = r.repeat;
        $("#r-conc").value = r.concurrency || cfg.defaults.concurrency;
        $("#r-split").value = r.dataset_split || "";
        $("#r-temp").value = r.temperature == null ? "" : r.temperature;
        $("#r-seed").value = r.seed == null ? "" : r.seed;
        updTotal();
        window.scrollTo(0, 0);
        toast("已把该运行的配置填入上方表单，确认后点「创建并运行」");
      });
      $$("#r-list [data-stop]").forEach(b => b.onclick = async () => { await post(`/api/runs/${b.dataset.stop}/stop`); refreshNow(); });
      $$("#r-list [data-start]").forEach(b => b.onclick = async () => { await post(`/api/runs/${b.dataset.start}/start`); refreshNow(); });
      $$("#r-list [data-reparse]").forEach(b => b.onclick = async () => {
        b.disabled = true;
        try {
          const res = await post(`/api/runs/${b.dataset.reparse}/reparse`, {});
          toast(res.repaired ? `已重新解析 ${res.repaired} 条结果${res.still_failed ? `，仍有 ${res.still_failed} 条无法解析` : ""}` : "这些结果仍无法解析，原始输出已保留在 raw 目录", !!res.repaired);
          refreshNow();
        } catch (e) { toast(e.message, false); b.disabled = false; }
      });
      $$("#r-list [data-del]").forEach(b => b.onclick = async () => {
        if (!(await confirmDlg("确定删除该运行及全部结果？", { title: "删除运行" }))) return;
        await del(`/api/runs/${b.dataset.del}`); refreshNow();
      });
      return hasActiveRun;
    } catch (e) { return false; }
  }
  const pollRuns = async () => {
    pollTimer = null;
    if (!location.hash.startsWith("#/runs")) return;
    const hasActiveRun = await refresh();
    if (hasActiveRun && location.hash.startsWith("#/runs")) {
      pollTimer = schedulePagePoll(pollRuns, 2500);
    }
  };
  const refreshNow = () => {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    return pollRuns();
  };
  await pollRuns();
});

// ---------------------------------------------------------------- 裁判与迭代中心
route("judge-iter", async () => {
  const [cfg, profileData, runs, judgeJobData] = await Promise.all([
    get("/api/config"), get("/api/prompt-profiles"), get("/api/runs"), get("/api/judge-jobs")]);
  const profiles = profileData.items || [];
  const doneRuns = projectRuns(runs.items).filter(r => r.done + r.failed > 0);
  const judgeProfiles = profiles.filter(p => p.type === "judge");
  const optProfiles = profiles.filter(p => p.type === "optimizer");
  const judgeJobs = judgeJobData.items || [];
  const runIds = new Set(doneRuns.map(r => r.id));
  const activeJudge = judgeJobs.find(j => j.is_active && runIds.has(j.run_id));
  const latestJudge = judgeJobs.find(j => runIds.has(j.run_id));
  const initialJudgeRun = runIds.has(state._jiRun) ? state._jiRun :
    ((activeJudge || latestJudge || {}).run_id || (doneRuns[0] && doneRuns[0].id) || "");
  const runOpts = (sel) => doneRuns.map(r =>
    `<option value="${r.id}" ${sel === r.id ? "selected" : ""}>${esc(r.id)} · ${esc(r.prompt_name)} V${r.prompt_version} · ${esc(r.model)}</option>`).join("");

  $("#app").innerHTML = `
  <div class="page-title">裁判与优化</div>
  ${projectScopeBar("可选运行、裁判任务与迭代任务都只显示当前项目的记录。")}
  <div class="msg info">裁判对每张图比较模型结果与人工审核，输出结构化错误定位（模块/问题/依据/建议）。裁判完成后可一键生成优化建议，确认后存为提示词新版本并立即运行验证。</div>
  <div class="tabs" id="ji-tabs">
    <div class="tab active" data-tab="judge">裁判运行</div>
    <div class="tab" data-tab="errors">错误池</div>
    <div class="tab" data-tab="diff">版本对比</div>
  </div>

  <div data-pane="judge">
    <div class="card">
      <h3>裁判运行</h3>
      <div class="muted u-mb-8">选择已完成人工审核的运行，启动裁判模型逐图判定。裁判输入：原图、推理图、分析结果 JSON、人工审核结果。输出：正报/误报/漏报 + 原因 + 模块级错误定位。</div>
      <div class="row">
        <div><label class="f">选择运行</label><select id="ji-run">${runOpts(initialJudgeRun)}</select></div>
        <div><label class="f">裁判站点 / 模型</label><select id="ji-model">${smOptions(cfg)}</select></div>
        <div><label class="f">裁判模板</label><select id="ji-profile"><option value="">默认裁判协议</option>${judgeProfiles.map(p => `<option value="${esc(p.name)}">${esc(p.name)}${p.builtin ? "（内置）" : ""}</option>`).join("")}</select></div>
        <div><label class="f">并发数</label><input type="number" id="ji-conc" value="2" min="1" max="8"></div>
         <div><label class="f">覆盖率阈值</label><input type="number" id="ji-cov" value="1" step="0.01" min="0" max="1"></div>
        <div class="u-f0 u-as-fe"><label class="f u-fx u-ai-c u-gap-6 u-fw-400"><input class="u-w-auto" type="checkbox" id="ji-force"> 强制重新裁判</label></div>
        <div class="u-f0 u-as-fe"><button class="btn primary" id="ji-start">启动裁判</button></div>
        <div class="u-f0 u-as-fe"><button class="btn danger u-hide" id="ji-stop">停止</button></div>
      </div>
      <div class="muted u-mt-6">裁判在服务端后台执行，切换页面不会中断；返回后会自动恢复任务进度和历史结果。</div>
      <div class="u-mt-8" id="ji-jobs"></div>
      <div class="u-mt-10" id="ji-status"></div>
    </div>
    <div class="card u-hide" id="ji-results">
      <div class="row u-ai-c u-mb-4">
        <h3 class="u-f2 u-m0">裁判结果</h3>
        <div class="u-f0"><button class="btn" id="ji-optimize">生成优化建议</button></div>
      </div>
      <div id="ji-summary"></div>
      <div class="row u-mt-8" id="ji-filterbar">
        <div><label class="f">结论筛选</label><select id="ji-f-verdict"><option value="">全部</option></select></div>
        <div><label class="f">模块筛选</label><select id="ji-f-module"><option value="">全部模块</option></select></div>
      </div>
      <div class="u-mt-10" id="ji-list"></div>
      <div class="u-mt-14" id="ji-opts"></div>
    </div>
  </div>

  <div class="u-hide" data-pane="errors">
    <div class="card">
      <h3>错误池</h3>
      <div class="muted u-mb-8">汇总裁判判为非"正确"的结果，按结论/模块/严重度统计，用于定位提示词哪部分需要优化。</div>
      <div class="row">
        <div><label class="f">选择运行</label><select id="ep-run">${runOpts()}</select></div>
        <div class="u-f0 u-as-fe"><button class="btn primary" id="ep-load">加载错误池</button></div>
      </div>
      <div class="row u-mt-8">
        <div><label class="f">回归图片集项目</label><input type="text" id="ep-proj" placeholder="项目名称"></div>
        <div><label class="f">回归图片集名称</label><input type="text" id="ep-name" placeholder="如：误报漏报回归集"></div>
        <div class="u-f0 u-as-fe"><button class="btn small" id="ep-regression">创建回归集</button></div>
      </div>
      <div class="u-mt-10" id="ep-box"></div>
    </div>
  </div>

  <div class="u-hide" data-pane="diff">
    <div class="card">
      <h3>版本对比</h3>
      <div class="muted u-mb-8">选择两个运行（通常是同一提示词的不同版本），逐图对比识别结果差异：状态变化、目标数变化、标签变化。点击行查看双版本推理图并排对比。</div>
      <div class="row">
        <div><label class="f">运行 A（基准）</label><select id="df-run1">${runOpts()}</select></div>
        <div><label class="f">运行 B（对比）</label><select id="df-run2">${runOpts()}</select></div>
        <div class="u-f0 u-as-fe"><button class="btn primary" id="df-go">对比</button></div>
      </div>
      <div class="u-mt-10" id="df-box"></div>
    </div>
  </div>

  <details class="adv" id="ji-adv">
    <summary>高级：自动迭代（运行 → 裁判 → 优化 → 验证 全自动循环）</summary>
    <div class="adv-body">
    <div class="card">
      <h3>自动迭代配置</h3>
      <div class="muted u-mb-8">从基线运行开始，自动循环：运行 → 裁判 → 定位错误 → 优化提示词（锁定 output_format）→ 新运行 → 直到达到稳定阈值或连续无提升。</div>
      <div class="row">
        <div><label class="f">基线运行</label><select id="it-run">${runOpts()}</select></div>
        <div><label class="f">运行站点 / 模型</label><select id="it-model">${smOptions(cfg)}</select></div>
       <div><label class="f">裁判站点 / 模型</label><select id="it-judge-model">${smOptions(cfg)}</select></div>
     </div>
      <div class="row">
        <div><label class="f">优化器站点 / 模型</label><select id="it-opt-model">${smOptions(cfg)}</select></div>
        <div><label class="f">裁判覆盖率阈值</label><input type="number" id="it-judge-cov" value="1.0" step="0.05" min="0" max="1"></div>
        <div><label class="f">候选数/轮</label><input type="number" id="it-candidates" value="1" min="1" max="3"></div>
      </div>
     <div class="row">
       <div><label class="f">裁判模板</label><select id="it-judge-profile"><option value="">默认</option>${judgeProfiles.map(p => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join("")}</select></div>
       <div><label class="f">优化器模板</label><select id="it-opt-profile"><option value="">默认</option>${optProfiles.map(p => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join("")}</select></div>
        <div><label class="f">最大轮次</label><input type="number" id="it-maxrounds" value="5" min="1" max="20"></div>
        <div><label class="f">耐心值（连续无提升停止）</label><input type="number" id="it-patience" value="2" min="1" max="10"></div>
      </div>
      <div class="row">
        <div><label class="f">最小提升幅度</label><input type="number" id="it-min-improve" value="0.005" step="0.001" min="0" max="1"></div>
        <div><label class="f">解析率阈值</label><input type="number" id="it-min-parse" value="0.98" step="0.01" min="0" max="1"></div>
        <div><label class="f">协议合规阈值</label><input type="number" id="it-min-proto" value="0.95" step="0.01" min="0" max="1"></div>
        <div><label class="f">准确率阈值</label><input type="number" id="it-min-acc" value="0.95" step="0.01" min="0" max="1"></div>
        <div><label class="f">兼容并发数</label><input type="number" id="it-conc" value="2" min="1" max="20"></div>
        <div><label class="f">分析并发</label><input type="number" id="it-analysis-conc" value="2" min="1" max="20"></div>
       <div><label class="f">裁判并发</label><input type="number" id="it-judge-conc" value="2" min="1" max="20"></div>
     </div>
     <div class="row">
       <div><label class="f">快测样本数（0=全量）</label><input type="number" id="it-quick-test" value="0" min="0" max="50"></div>
       <div class="muted u-as-c">设为 0 跑全量；>0 时先用 N 张代表性图片快速验证候选方向，通过后再跑全量</div>
       <div></div>
     </div>
     <div class="u-mt-10"><button class="btn" id="it-start">启动迭代</button></div>
    </div>
    <div class="card">
      <h3>迭代任务列表</h3>
      <div id="it-list"></div>
    </div>
    </div>
  </details>`;

  // ---- Tab switching
  $$("#ji-tabs .tab").forEach(t => t.onclick = () => {
    $$("#ji-tabs .tab").forEach(x => x.classList.toggle("active", x === t));
    $$("[data-pane]").forEach(p => setShown(p, p.dataset.pane === t.dataset.tab));
  });

  // ---- Tab 1: Judge run
 const renderJudgeJobs = (jobs) => {
   const box = $("#ji-jobs");
   if (!box) return;
    const items = jobs || [];
    if (!items.length) { box.innerHTML = ""; return; }
    // 按状态分组：运行中 → 暂停 → 已完成/失败
    const groups = { running: [], paused: [], done: [], other: [] };
    items.forEach(j => {
      const s = j.status || "idle";
      if (s === "running" || j.is_active) groups.running.push(j);
      else if (s === "paused" || s === "idle") groups.paused.push(j);
      else if (s === "done" || s === "done_with_errors") groups.done.push(j);
      else groups.other.push(j);
    });
    const groupCfg = [
      { key: "running", label: "运行中", cls: "blue" },
      { key: "paused", label: "暂停/待继续", cls: "orange" },
      { key: "done", label: "已完成", cls: "green" },
      { key: "other", label: "其他", cls: "" },
    ].filter(g => groups[g.key].length);
    const renderJobCard = (job) => {
      const isMine = job.run_id === $("#ji-run").value;
      const isActive = job.is_active || job.status === "running";
      return `<div class="u-list-row">
        <button type="button" class="btn small ${isMine ? "primary" : ""}" data-judge-run="${esc(job.run_id)}" title="${esc(job.run_id)}">${statusTag(job.status)} <span class="mono">${esc(job.run_id.slice(0, 20))}${job.run_id.length > 20 ? "…" : ""}</span> ${job.done || 0}/${job.total || 0}</button>
        ${isActive ? `<button class="btn small" data-judge-stop="${esc(job.run_id)}">暂停</button>` : ""}
        <button class="btn small danger" data-judge-del="${esc(job.run_id)}" ${isActive ? "disabled title='运行中不可删除'" : ""}>删除</button>
      </div>`;
    };
    box.innerHTML = groupCfg.map(g =>
      `<div class="u-mb-8"><div class="muted u-mb-3 u-fs-xs">${g.label}（${groups[g.key].length}）</div>${groups[g.key].map(renderJobCard).join("")}</div>`
    ).join("");
    $$("#ji-jobs [data-judge-run]").forEach(btn => btn.onclick = () => {
      $("#ji-run").value = btn.dataset.judgeRun;
      state._jiRun = btn.dataset.judgeRun;
      setShown($("#ji-results"), false);
      jiStatus();
      loadJudgeResults(btn.dataset.judgeRun);
    });
    $$("#ji-jobs [data-judge-stop]").forEach(btn => btn.onclick = async () => {
      try { await post(`/api/runs/${encodeURIComponent(btn.dataset.judgeStop)}/judge/stop`, {}); toast("已暂停裁判任务"); jiStatus(); }
      catch (e) { toast(e.message, false); }
    });
    $$("#ji-jobs [data-judge-del]").forEach(btn => btn.onclick = async () => {
      try { await del(`/api/runs/${encodeURIComponent(btn.dataset.judgeDel)}/judge`); toast("已删除裁判任务"); jiStatus(); }
      catch (e) { toast(e.message, false); }
    });
  };
  const jiStatus = () => {
    const select = $("#ji-run");
    if (!select) return;
    const runId = select.value;
    if (!runId) return;
    state._jiRun = runId;
    Promise.all([
      get(`/api/runs/${encodeURIComponent(runId)}/judge-job`),
      get("/api/judge-jobs"),
    ]).then(([job, jobsData]) => {
      const box = $("#ji-status");
      if (!box || !$("#ji-run") || $("#ji-run").value !== runId) return;
      // 裁判任务挂在运行上，运行属于项目：只列当前项目里的那些任务，
      // 否则切到「示例项目」仍会看到别的项目的历史裁判卡片。
      renderJudgeJobs((jobsData.items || []).filter(j => runIds.has(j.run_id)));
      const processed = (job.done || 0) + (job.failed || 0) + (job.skipped || 0);
      const total = job.total || 0;
      const pct = total ? Math.round(processed / total * 100) : 100;
      const coverage = job.coverage == null ? (job.eligible ? (job.done / job.eligible) : (total ? 0 : 1)) : job.coverage;
      const workerText = (job.active_workers || 0) + "/" + (job.concurrency || job.requested_concurrency || "-");
      const keyStats = job.key_stats || {};
      const keyText = Object.keys(keyStats).length ? Object.entries(keyStats).map(([name, st]) =>
        `<span class="tag ${st.cooldown_until && st.cooldown_until > Date.now()/1000 ? "orange" : "blue"}">${esc(name)} · 并发 ${st.inflight || 0} · 失败 ${st.failures || 0}</span>`).join(" ") : "未返回 Key 状态";
      const heartbeat = job.heartbeat ? new Date(job.heartbeat * 1000).toLocaleTimeString() : "-";
      const errors = (job.errors || []).slice(0, 5).map(e => typeof e === "string" ? e : (e.image ? e.image + "：" + (e.error || "失败") : JSON.stringify(e)));
      box.innerHTML = `<div class="row u-ai-c"><div class="u-f14">${statusTag(job.status)}</div><div class="muted u-f3">成功 ${job.done || 0} · 调用失败 ${job.failed || 0} · 跳过 ${job.skipped || 0}${job.parse_failed ? ` · 未纳入裁判（解析失败）${job.parse_failed}` : ""}</div><div class="muted u-f2">覆盖率 ${(coverage * 100).toFixed(1)}% · Worker ${workerText}</div><div class="u-f22"><div class="progress-wrap">${progressBar(processed, total, job.failed)}</div></div></div><div class="muted u-mt-6">当前样本：${esc((job.current && job.current.image) || "-")} · 心跳：${esc(heartbeat)} · 请求并发：${job.requested_concurrency || job.concurrency || "-"} · 有效并发：${job.concurrency || "-"}</div><div class="u-mt-6">Key 状态：${keyText}</div>${job.error ? `<div class="msg err u-mt-8">${esc(job.error)}</div>` : ""}${errors.length ? `<div class="msg err u-mt-8">${errors.map(e => `<div>${esc(e)}</div>`).join("")}</div>` : ""}${job.note ? `<div class="msg u-mt-8 u-bg-success u-bd-green">${esc(job.note)}</div>` : ""}`;
      const isActive = job.is_active || job.status === "running";
      setShown($("#ji-start"), !isActive);
      setShown($("#ji-stop"), isActive);
      if (isActive) schedulePagePoll(jiStatus, 2000);
      if (["done", "done_with_errors", "paused", "failed"].includes(job.status)) loadJudgeResults(runId);
    }).catch(() => {});
  };
  const loadJudgeResults = async (runId) => {
    try {
      const data = await get(`/api/runs/${encodeURIComponent(runId)}/judgments`);
      const items = data.items || [];
      if (!$("#ji-results") || $("#ji-run").value !== runId) return;
      if (!items.length) { setShown($("#ji-results"), false); return; }
      setShown($("#ji-results"), true);
      const counts = {};
      items.forEach(i => { counts[i.verdict] = (counts[i.verdict] || 0) + 1; });
      const rootCauses = {};
      items.forEach(i => { if (i.root_cause) rootCauses[i.root_cause] = (rootCauses[i.root_cause] || 0) + 1; });
      $("#ji-summary").innerHTML = `<div class="grid grid-4">${distTable("裁判结论分布", counts)}${distTable("严重度分布", items.reduce((m, i) => { if (i.severity) m[i.severity] = (m[i.severity] || 0) + 1; return m; }, {}))}${distTable("错误模块分布", items.reduce((m, i) => { (i.fault_location || []).forEach(f => { m[f.module] = (m[f.module] || 0) + 1; }); return m; }, {}))}${distTable("根因归类", rootCauses)}</div>`;
      // 筛选选项
      const verdicts = Object.keys(counts);
      const modules = [...new Set(items.flatMap(i => (i.fault_location || []).map(f => f.module)))];
      $("#ji-f-verdict").innerHTML = `<option value="">全部结论</option>` + verdicts.map(v => `<option>${esc(v)}</option>`).join("");
      $("#ji-f-module").innerHTML = `<option value="">全部模块</option>` + modules.map(m => `<option>${esc(m)}</option>`).join("");
      const expanded = new Set();
      const renderList = () => {
        const fv = $("#ji-f-verdict").value, fm = $("#ji-f-module").value;
        const shown = items.filter(i =>
          (!fv || i.verdict === fv) &&
          (!fm || (i.fault_location || []).some(f => f.module === fm)));
        $("#ji-list").innerHTML = `<div class="tbl-scroll"><table class="tbl"><thead><tr><th class="u-w-20"></th><th>图片</th><th>结论</th><th>严重度</th><th>错误模块</th><th>根因</th><th>原因</th></tr></thead><tbody>${shown.map((i, idx) => {
          const key = i.image + "#" + i.repeat;
          const isOpen = expanded.has(key);
          const modulesHtml = (i.fault_location || []).map(f => `<span class="tag orange">${esc(f.module)}</span>`).join("") || "-";
          const detail = isOpen ? `<tr><td></td><td colspan="6" class="judge-detail-cell">
            <div class="judge-detail-grid">
               <div>
                 <div class="muted u-fs-xs u-mb-4">推理图（模型输出）</div>
                 <img src="/api/file/run/${encQ(runId)}/annotated/${enc(i.image)}?repeat=${i.repeat}" data-zoom="1" data-ann-fallback="/api/file/run/${encQ(runId)}/image/${enc(i.image)}">
                 <div class="u-mt-8">
                   <div class="muted u-fs-xs u-mb-4">人工标注图（审核时人工画的框）</div>
                   <img src="/api/file/review/${encQ(runId)}/annotated/${enc(i.image)}?repeat=${i.repeat}" data-zoom="1" data-hide-on-error="1">
                 </div>
               </div>
              <div>
                <div class="judge-meta-line">${statusTag(i.verdict)}${i.severity ? `<span class="tag red">严重度 ${esc(i.severity)}</span>` : ""}${i.root_cause ? `<span class="tag blue">根因：${esc(i.root_cause)}</span>` : ""}${i.llm_verdict && i.deterministic_verdict && i.llm_verdict !== i.deterministic_verdict ? `<span class="tag orange" title="裁判模型与确定性比较结论不一致">LLM ${esc(i.llm_verdict)} / 规则 ${esc(i.deterministic_verdict)}</span>` : ""}</div>
                <div class="fault-card u-bd-l-primary"><div class="fk">完整原因</div><div class="fv">${esc(i.reason || "-")}</div></div>
                ${(i.fault_location || []).map(f => `<div class="fault-card">
                  <div><span class="tag orange">${esc(f.module)}</span></div>
                  <div class="fk">问题</div><div class="fv">${esc(f.problem || "-")}</div>
                  <div class="fk">依据</div><div class="fv">${esc(f.evidence || "-")}</div>
                  <div class="fk">改进建议</div><div class="fv">${esc(f.suggestion || "-")}</div>
                </div>`).join("")}
                ${i.recommended_action ? `<div class="fault-card u-bd-l-green"><div class="fk">建议动作</div><div class="fv">${esc(i.recommended_action)}</div></div>` : ""}
                ${i.optimization_direction ? `<div class="fault-card u-bd-l-green"><div class="fk">优化方向</div><div class="fv">${esc(i.optimization_direction)}</div></div>` : ""}
              </div>
            </div></td></tr>` : "";
          return `<tr class="judge-row-head" data-key="${esc(key)}" data-idx="${idx}">
            <td>${isOpen ? "▾" : "▸"}</td>
            <td class="mono">${esc(i.image)} R${i.repeat}</td>
            <td>${statusTag(i.verdict)}</td>
            <td>${esc(i.severity || "-")}</td>
            <td>${modulesHtml}</td>
            <td>${esc(i.root_cause || "-")}</td>
            <td class="muted u-maxw-260 u-ellipsis">${esc((i.reason || "").slice(0, 60))}</td>
          </tr>` + detail;
        }).join("") || '<tr><td colspan="7" class="muted">无匹配记录</td></tr>'}</tbody></table></div>
        <div class="muted u-mt-6">共 ${shown.length} 条 · 点击行展开完整裁判详情（问题 / 依据 / 建议 / 推理图 / 人工标注图）</div>`;
        $$("#ji-list .judge-row-head").forEach(tr => tr.onclick = () => {
          const key = tr.dataset.key;
          if (expanded.has(key)) expanded.delete(key); else expanded.add(key);
          renderList();
        });
      };
      $("#ji-f-verdict").onchange = renderList;
      $("#ji-f-module").onchange = renderList;
      renderList();
      loadOptRecords(runId);
    } catch (e) {}
  };
  $("#ji-start").onclick = async () => {
    if ($("#ji-start").disabled) return;
    const runId = $("#ji-run").value;
    if (!runId) return toast("请选择运行", false);
    state._jiRun = runId;
    const sm = smParse($("#ji-model").value);
    try {
      $("#ji-start").disabled = true;
      await post(`/api/runs/${encodeURIComponent(runId)}/judge`, {
        model: sm.model, site: sm.site, concurrency: Number($("#ji-conc").value),
        coverage_threshold: Number($("#ji-cov").value),
        force: $("#ji-force").checked, profile_name: $("#ji-profile").value });
      toast("裁判已启动"); jiStatus();
    } catch (e) { toast(e.message, false); }
    finally { const b = $("#ji-start"); if (b) b.disabled = false; }
  };
  $("#ji-stop").onclick = async () => {
    const runId = $("#ji-run").value;
    try { await post(`/api/runs/${encodeURIComponent(runId)}/judge/stop`, {}); toast("已发送停止信号"); jiStatus(); }
    catch (e) { toast(e.message, false); }
  };
  $("#ji-run").onchange = () => {
    state._jiRun = $("#ji-run").value;
    $("#ji-status").innerHTML = "";
    setShown($("#ji-results"), false);
    jiStatus();
    loadJudgeResults(state._jiRun);
    loadOptRecords(state._jiRun);
  };

  // ---- 裁判 → 优化闭环：综合裁判结果生成修改建议，确认后存为新版本并验证
  // ---- 优化建议记录：生成在服务端后台执行并持久化，关弹窗/切页面/刷新都不丢
  const viewOptRecord = async (id) => {
    try {
      const rec = await get(`/api/prompt-ai/optimizations/${encodeURIComponent(id)}`);
      const run = doneRuns.find(r => r.id === rec.source_run) || null;
      const dlg = openDlg(`<h3>优化建议详情</h3>
        <div class="muted">「${esc(rec.prompt_name)}」V${rec.source_version} → 候选版本 · ${esc(rec.created || "")}</div>
        <div id="opd-body"></div>`, { wide: true });
      const body = dlg.box.querySelector("#opd-body");
      if (rec.status === "failed" || rec.status === "interrupted") {
        body.innerHTML = `<div class="msg err u-mt-12">${rec.status === "interrupted" ? "生成被中断（服务可能重启过），请重新生成。" : "生成失败"}：${esc(rec.error || "未知错误")}</div>`;
        return;
      }
      await renderOptRecord(body, rec, run, dlg.close);
    } catch (e) { toast(e.message, false); }
  };
  const loadOptRecords = async (runId) => {
    const box = $("#ji-opts");
    if (!box) return;
    try {
      const data = await get("/api/prompt-ai/optimizations");
      const items = (data.items || []).filter(i => i.source_run === runId);
      if (!$("#ji-opts") || $("#ji-run").value !== runId) return;
      if (!items.length) { box.innerHTML = ""; return; }
      const stTag = (i) => {
        if (i.status === "running") return `<span class="tag blue">生成中…</span>`;
        if (i.status === "interrupted") return `<span class="tag">已中断</span>`;
        if (i.status === "failed") return `<span class="tag red">失败</span>`;
        if (i.status === "saved") return `<span class="tag green">已保存 V${i.saved_version}</span>`;
        return `<span class="tag orange">待确认</span>`;
      };
      box.innerHTML = `<h4 class="u-m-0-0-6">优化建议记录</h4>
        <div class="tbl-scroll"><table class="tbl"><thead><tr><th>时间</th><th>改动模块</th><th>摘要</th><th>状态</th><th class="u-w-120">操作</th></tr></thead>
        <tbody>${items.map(i => `<tr>
          <td class="muted u-nowrap">${esc(i.created || "-")}</td>
          <td>${(i.changed_modules || []).map(m => `<span class="tag orange">${esc(m)}</span>`).join("") || "-"}</td>
          <td class="muted u-maxw-260 u-ellipsis">${esc(i.change_summary || i.error || "-")}</td>
          <td>${stTag(i)}</td>
          <td>${i.status !== "running" ? `<button class="btn small" data-opt-view="${esc(i.id)}">查看</button> <button class="btn small danger" data-opt-del="${esc(i.id)}">删除</button>` : '<span class="muted">-</span>'}</td>
        </tr>`).join("")}</tbody></table></div>`;
      $$("#ji-opts [data-opt-view]").forEach(btn => btn.onclick = () => viewOptRecord(btn.dataset.optView));
      $$("#ji-opts [data-opt-del]").forEach(btn => btn.onclick = async () => {
        if (!(await confirmDlg("删除这条优化建议记录？", { title: "删除优化建议" }))) return;
        try { await del(`/api/prompt-ai/optimizations/${encodeURIComponent(btn.dataset.optDel)}`); toast("已删除"); loadOptRecords(runId); }
        catch (e) { toast(e.message, false); }
      });
      if (items.some(i => i.status === "running")) schedulePagePoll(() => loadOptRecords(runId), 3000);
    } catch (e) {}
  };
  state._optRecordsReload = () => { const r = $("#ji-run") && $("#ji-run").value; if (r) loadOptRecords(r); };

  $("#ji-optimize").onclick = async () => {
    const runId = $("#ji-run").value;
    const run = doneRuns.find(r => r.id === runId);
    if (!run) return toast("请先选择运行", false);
    const dlg = openDlg(`
      <h3>生成优化建议</h3>
      <div class="muted u-mb-10">综合本次裁判的全部错误定位，由优化器模型给出提示词修改方案。output_format 模块锁定不变，只改前四个模块。生成在后台进行，关闭此窗口不影响结果。</div>
      <div class="row">
        <div><label class="f">提示词</label><input type="text" value="${esc(run.prompt_name)} V${run.prompt_version}" disabled></div>
        <div><label class="f">优化器站点 / 模型</label><select id="op-model">${smOptions(cfg)}</select></div>
      </div>
      <div class="row">
        <div><label class="f">优化器模板</label><select id="op-profile"><option value="">默认优化器</option>${optProfiles.map(p => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join("")}</select></div>
        <div><label class="f">最大证据条数</label><input type="number" id="op-max" value="50" min="5" max="200"></div>
      </div>
      <div class="dlg-actions">
        <button class="btn primary" id="op-go">开始生成</button>
        <button class="btn" id="op-cancel">取消</button>
        <span class="muted u-as-c" id="op-status"></span>
      </div>
      <div id="op-result"></div>`, { wide: true });
    dlg.box.querySelector("#op-cancel").onclick = dlg.close;
    dlg.box.querySelector("#op-go").onclick = async () => {
      const goBtn = dlg.box.querySelector("#op-go");
      const status = dlg.box.querySelector("#op-status");
      const sm = smParse(dlg.box.querySelector("#op-model").value);
      goBtn.disabled = true;
      status.innerHTML = `<span class="spin"></span>正在提交…`;
      try {
        const ack = await post("/api/prompt-ai/optimize", {
          prompt_name: run.prompt_name, version: run.prompt_version, run_id: runId,
          model: sm.model, site: sm.site,
          profile_name: dlg.box.querySelector("#op-profile").value,
          max_items: Number(dlg.box.querySelector("#op-max").value) || 50,
        });
        status.innerHTML = `<span class="spin"></span>优化器后台生成中，通常 30-90 秒。可关闭此窗口，完成后在下方「优化建议记录」查看。`;
        loadOptRecords(runId);
        const poll = async () => {
          if (!document.body.contains(dlg.mask)) return;  // 弹窗已关：生成继续，结果在记录列表更新
          let rec;
          try { rec = await get(`/api/prompt-ai/optimizations/${encodeURIComponent(ack.id)}`); }
          catch (e) { setTimeout(poll, 3000); return; }
          if (rec.status === "running") { setTimeout(poll, 3000); return; }
          status.innerHTML = "";
          setShown(goBtn, false);
          const out = dlg.box.querySelector("#op-result");
          if (rec.status === "failed" || rec.status === "interrupted") {
            out.innerHTML = `<div class="msg err u-mt-12">${rec.status === "interrupted" ? "生成被中断（服务可能重启过），请重新生成。" : "生成失败"}：${esc(rec.error || "未知错误")}</div>`;
          } else {
            await renderOptRecord(out, rec, run, dlg.close);
          }
          loadOptRecords(runId);
        };
        poll();
      } catch (e) {
        status.innerHTML = `<span class="tag red">提交失败</span> ${esc(e.message)}`;
        goBtn.disabled = false;
      }
    };
  };

  // ---- Tab 2: Error pool
  const loadErrorPool = async () => {
    const runId = $("#ep-run").value;
    if (!runId) return toast("请选择运行", false);
    try {
      const data = await get(`/api/runs/${encodeURIComponent(runId)}/errors`);
      const items = data.items || [];
      $("#ep-box").innerHTML = `
        <div class="grid grid-3">${distTable("结论分布", data.verdict_counts)}${distTable("错误模块分布", data.module_counts)}${distTable("严重度分布", data.severity_counts)}</div>
        <div class="muted u-my-8">共 ${data.total} 条错误记录</div>
        <div class="tbl-scroll"><table class="tbl"><thead><tr><th>图片</th><th>结论</th><th>严重度</th><th>错误模块</th><th>原因</th></tr></thead><tbody>
        ${items.map(i => `<tr><td class="mono">${esc(i.image)} R${i.repeat}</td><td>${statusTag(i.verdict)}</td><td>${esc(i.severity || "-")}</td><td>${(i.modules || []).map(m => `<span class="tag orange">${esc(m)}</span>`).join("") || "-"}</td><td class="muted u-maxw-300">${esc((i.reason || "").slice(0, 100))}</td></tr>`).join("") || '<tr><td colspan="5" class="muted">无错误记录（所有结果均判为正确）</td></tr>'}
        </tbody></table></div>`;
    } catch (e) { toast(e.message, false); }
  };
  $("#ep-load").onclick = loadErrorPool;
  $("#ep-regression").onclick = async () => {
    const runId = $("#ep-run").value;
    const proj = $("#ep-proj").value.trim();
    const name = $("#ep-name").value.trim();
    if (!runId || !proj || !name) return toast("请填写运行、项目和图片集名称", false);
    try {
      const r = await post(`/api/runs/${encodeURIComponent(runId)}/regression-dataset`, { project: proj, name });
      toast(`已创建回归集 ${r.count} 张`);
    } catch (e) { toast(e.message, false); }
  };

  // ---- Tab 3: Version diff
  $("#df-go").onclick = async () => {
    const r1 = $("#df-run1").value, r2 = $("#df-run2").value;
    if (!r1 || !r2) return toast("请选择两个运行", false);
    if (r1 === r2) return toast("请选择不同的运行", false);
    try {
      const d = await get(`/api/runs/${encodeURIComponent(r1)}/diff/${encodeURIComponent(r2)}`);
      const items = d.items || [];
      $("#df-box").innerHTML = `
        <div class="row u-mb-10">
          <div class="muted u-f2">运行 A：${esc(d.run1.prompt_name)} V${d.run1.prompt_version} · ${esc(d.run1.id)}<br>运行 B：${esc(d.run2.prompt_name)} V${d.run2.prompt_version} · ${esc(d.run2.id)}</div>
          <div class="u-f1"><span class="tag orange">变化 ${d.changed}</span> <span class="tag green">不变 ${d.unchanged}</span> <span class="tag blue">共 ${d.total_common}</span></div>
        </div>
        <div class="tbl-scroll"><table class="tbl"><thead><tr><th>图片</th><th>A 状态</th><th>B 状态</th><th>A 目标数</th><th>B 目标数</th><th>变化类型</th><th></th></tr></thead><tbody>
        ${items.map(i => `<tr class="u-pointer" data-rel="${esc(i.image)}"><td class="mono">${esc(i.image)}</td><td>${i.v1_status ? statusTag(i.v1_status) : '<span class="muted">-</span>'}</td><td>${i.v2_status ? statusTag(i.v2_status) : '<span class="muted">-</span>'}</td><td>${i.v1_object_count}</td><td>${i.v2_object_count}</td><td>${(i.change_types || []).map(c => `<span class="tag orange">${esc(c)}</span>`).join("") || '<span class="muted">无</span>'}</td><td>${i.changed ? '<span class="tag orange">查看</span>' : '<span class="muted">-</span>'}</td></tr>`).join("") || '<tr><td colspan="7" class="muted">无共同图片</td></tr>'}
        </tbody></table></div>
        ${d.only_in_run1.length ? `<div class="muted u-mt-8">仅运行 A 有：${d.only_in_run1.map(r => `<span class="tag">${esc(r)}</span>`).join("")}</div>` : ""}
        ${d.only_in_run2.length ? `<div class="muted u-mt-4">仅运行 B 有：${d.only_in_run2.map(r => `<span class="tag">${esc(r)}</span>`).join("")}</div>` : ""}
        <div class="u-mt-12" id="df-detail"></div>`;
      $$("#df-box [data-rel]").forEach(tr => tr.onclick = async () => {
        const rel = tr.dataset.rel;
        const detail = $("#df-detail");
        detail.innerHTML = `<div class="card"><h4>${esc(rel)} — 并排对比</h4><div class="panels">
          <div class="panel"><h4>运行 A 推理图</h4><img src="/api/file/run/${encQ(r1)}/annotated/${enc(rel)}?repeat=1" data-zoom="1" data-ann-fallback="/api/file/run/${encQ(r1)}/image/${enc(rel)}"></div>
          <div class="panel"><h4>运行 B 推理图</h4><img src="/api/file/run/${encQ(r2)}/annotated/${enc(rel)}?repeat=1" data-zoom="1" data-ann-fallback="/api/file/run/${encQ(r2)}/image/${enc(rel)}"></div>
        </div></div>`;
      });
    } catch (e) { toast(e.message, false); }
  };

  // ---- Tab 4: Auto iteration
  const refreshIter = async () => {
    const data = await get("/api/workflows");
    if (!$("#it-list")) return;
    // 迭代任务的 dataset 是 "项目::图片集" 的 ref，按当前项目收口。
    const items = (data.items || []).filter(job => inProject({ ref: job.dataset || "" }));
    // 只在数据变化时重建列表，避免闪烁
    const sig = JSON.stringify(items.map(j => `${j.id}:${j.status}:${j.phase}:${j.progress||""}:${j.optimizer_sub_phase||""}:${(j.rounds||[]).length}:${j.best_version}:${j.best_score}:${j.is_active}:${j.error||""}:${j.stop_reason||""}`));
    if (state._itLastSig === sig) {
      if (items.some(j => j.is_active)) schedulePagePoll(refreshIter, 2000);
      return;
    }
    state._itLastSig = sig;
    // 按 项目/提示词 分组
    const groups = {};
    items.forEach(job => {
      // dataset 存的是 "项目::图片集" 的 ref，分隔符是 :: 而不是 /
      const proj = refProject(job.dataset || "");
      const key = `${proj} / ${job.prompt_name}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(job);
    });
    const groupKeys = Object.keys(groups).sort();
    let html = "";
    groupKeys.forEach(key => {
      const jobs = groups[key];
      const activeCount = jobs.filter(j => j.is_active).length;
      html += `<div class="p-group u-mb-4">
        <div class="p-group-head p-group-head-row" data-grp="${esc(key)}">
          <span class="p-arrow u-trans-rot">${state._itCollapsed && state._itCollapsed[key] ? "▶" : "▼"}</span>
          <span>${esc(key)}</span>
          <span class="tag blue">${jobs.length}</span>
          ${activeCount ? `<span class="tag green">${activeCount} 运行中</span>` : ""}
        </div>
        <div class="p-group-body" data-grp-body="${esc(key)}" style="${state._itCollapsed && state._itCollapsed[key] ? "display:none" : ""}">
        <div class="tbl-scroll"><table class="tbl"><thead><tr><th>任务</th><th>提示词版本</th><th>阶段/进度</th><th>轮次</th><th>最优版本</th><th>质量/覆盖率</th><th>状态</th><th>操作</th></tr></thead><tbody>${jobs.map(job => `<tr><td class="mono u-fs-xs">${esc(job.id)}</td><td>V${job.source_version}</td><td>${esc(job.phase || "-")}${job.progress ? `<br><span class="tag blue">${esc(job.progress)}</span>` : ""}${job.optimizer_sub_phase ? `<br><span class="tag orange">${esc(job.optimizer_sub_phase)}</span>` : ""}<br><span class="muted">${esc(job.stop_reason || job.error || "")}</span></td><td>${(job.rounds || []).length}/${job.max_rounds}</td><td>V${job.best_version}${job.best_score == null ? "" : ` · ${(job.best_score*100).toFixed(1)}%`}</td><td>${job.best_metrics ? `准确率 ${job.best_metrics.accuracy == null ? "-" : (job.best_metrics.accuracy*100).toFixed(1)+"%"}<br>覆盖 ${job.best_metrics.judge_coverage == null ? "-" : (job.best_metrics.judge_coverage*100).toFixed(1)+"%"}` : "-"}</td><td>${statusTag(job.status)}</td><td><a class="btn small primary" href="#/workflow/${encodeURIComponent(job.id)}">查看迭代</a> ${job.is_active ? `<button class="btn small" data-pause="${job.id}">暂停</button>` : (["paused","waiting_for_review","waiting_for_judge","failed"].includes(job.status) ? `<button class="btn small" data-resume="${job.id}">继续</button>` : "")} <button class="btn small danger" data-del-wf="${job.id}" ${job.is_active ? "disabled title='运行中不可删除'" : ""}>删除</button></td></tr>`).join("")}</tbody></table></div>
        </div>
      </div>`;
    });
    $("#it-list").innerHTML = html || emptyState(currentProject()
      ? `「${currentProject()}」还没有迭代任务，先在运行测试里跑一轮，再回来做裁判与迭代`
      : "还没有迭代任务，先在运行测试里跑一轮，再回来做裁判与迭代", "去运行测试", "#/runs");
    // 分组折叠
    $$("#it-list .p-group-head").forEach(h => h.onclick = () => {
      const key = h.dataset.grp;
      if (!state._itCollapsed) state._itCollapsed = {};
      state._itCollapsed[key] = !state._itCollapsed[key];
      const body = $(`#it-list [data-grp-body="${CSS.escape(key)}"]`);
      const arrow = h.querySelector(".p-arrow");
      if (state._itCollapsed[key]) { setShown(body, false); arrow.textContent = "▶"; }
      else { setShown(body, true); arrow.textContent = "▼"; }
    });
    // 操作按钮
    $$("[data-pause]").forEach(b => b.onclick = async () => { await post(`/api/workflows/${b.dataset.pause}/pause`, {}); refreshIter(); });
    $$("[data-resume]").forEach(b => b.onclick = async () => { try { await post(`/api/workflows/${b.dataset.resume}/resume`, {}); refreshIter(); } catch (e) { toast(e.message, false); } });
    $$("[data-del-wf]").forEach(b => b.onclick = async () => {
      if (!(await confirmDlg(`确认删除迭代任务 ${b.dataset.delWf}？此操作不可恢复。`, { title: "删除迭代任务" }))) return;
      try { await del(`/api/workflows/${encodeURIComponent(b.dataset.delWf)}`); toast("已删除"); refreshIter(); }
      catch (e) { toast(e.message, false); }
    });
    if (items.some(j => j.is_active)) schedulePagePoll(refreshIter, 2000);
  };
  $("#it-start").onclick = async () => {
    if ($("#it-start").disabled) return;
    const runId = $("#it-run").value;
    if (!runId) return toast("请选择基线运行", false);
   const sm = smParse($("#it-model").value);
   const jsm = smParse($("#it-judge-model").value);
    const osm = smParse($("#it-opt-model").value);
   try {
      $("#it-start").disabled = true;
     const run = await get(`/api/runs/${encodeURIComponent(runId)}`);
     await post("/api/workflows", {
       baseline_run_id: runId,
       prompt_name: run.prompt_name, source_version: run.prompt_version,
       model: sm.model, site: sm.site,
       judge_model: jsm.model, judge_site: jsm.site,
        optimizer_model: osm.model, optimizer_site: osm.site,
       judge_profile: $("#it-judge-profile").value,
       optimizer_profile: $("#it-opt-profile").value,
        max_rounds: Number($("#it-maxrounds").value),
        patience: Number($("#it-patience").value),
        min_improvement: Number($("#it-min-improve").value),
        min_parse_rate: Number($("#it-min-parse").value),
        min_protocol_rate: Number($("#it-min-proto").value),
        min_accuracy: Number($("#it-min-acc").value),
        concurrency: Number($("#it-conc").value),
      analysis_concurrency: Number($("#it-analysis-conc").value),
         judge_concurrency: Number($("#it-judge-conc").value),
         judge_coverage_threshold: Number($("#it-judge-cov").value),
         candidates_per_round: Number($("#it-candidates").value),
         quick_test_size: Number($("#it-quick-test").value),
       });
      toast("迭代任务已启动");
      refreshIter();
    } catch (e) { toast(e.message, false); }
    finally { const b = $("#it-start"); if (b) b.disabled = false; }
  };
  if (initialJudgeRun) {
    state._jiRun = initialJudgeRun;
    jiStatus();
    loadJudgeResults(initialJudgeRun);
    loadOptRecords(initialJudgeRun);
  }
  refreshIter();
});

// ---------------------------------------------------------------- 自动迭代详情
route("workflow", async (jobId) => {
  if (!jobId) { location.hash = "#/judge-iter"; return; }
  jobId = decodeURIComponent(jobId);
  if (!state._wfSelected) state._wfSelected = {};

  const pct = (v) => v == null ? "-" : (Number(v) * 100).toFixed(1) + "%";
  const signedPct = (v) => v == null ? "-" : (v > 0 ? "+" : "") + (Number(v) * 100).toFixed(1) + "%";
  const metricText = (m) => m ? `准确率 ${pct(m.accuracy)} · 解析 ${pct(m.parse_rate)} · 协议 ${pct(m.protocol_valid_rate)} · 覆盖 ${pct(m.judge_coverage)} · 高严重度 ${m.high_severity_errors || 0}` : "-";
  const deltaText = (d) => d ? `准确率 ${signedPct(d.accuracy)} · 解析 ${signedPct(d.parse_rate)} · 协议 ${signedPct(d.protocol_valid_rate)} · 覆盖 ${signedPct(d.judge_coverage)}` : "-";
  const decisionTag = (item) => {
    if (item.pending) return '<span class="tag blue">进行中</span>';
    if (item.accepted === true) return '<span class="tag green">已接受</span>';
    if (item.accepted === false) return '<span class="tag orange">已拒绝</span>';
    return '<span class="tag">基线</span>';
  };
  const safeGet = (path) => get(path).catch(e => ({ __error: e.message }));

  const loadRoundDetail = async (item) => {
    const box = $("#wf-detail");
    if (!box) return;
    box.innerHTML = '<div class="card muted">正在加载本轮详情…</div>';
    const requests = [
      safeGet(`/api/workflows/${encodeURIComponent(jobId)}`),
      safeGet(`/api/runs/${encodeURIComponent(item.run_id)}`),
      safeGet(`/api/runs/${encodeURIComponent(item.run_id)}/judgments`),
      safeGet(`/api/runs/${encodeURIComponent(item.run_id)}/errors`),
    ];
    if (item.source_version && item.version && item.source_version !== item.version) {
      requests.push(safeGet(`/api/prompts/${encodeURIComponent(item.prompt_name)}/diff?v1=${item.source_version}&v2=${item.version}`));
    } else {
      requests.push(Promise.resolve(null));
    }
    const [wf, run, judgmentData, errorData, diff] = await Promise.all(requests);
    if (!$("#wf-detail")) return;
    // 迭代任务自带 dataset（项目::图片集）：打开详情就把项目上下文对齐，
    // 否则从历史链接进来，顶部条还停在上一个项目上。
    if (wf && wf.dataset) adoptProjectOf({ ref: wf.dataset });
    const judgments = judgmentData.items || [];
    const counts = {};
    judgments.forEach(j => { counts[j.verdict] = (counts[j.verdict] || 0) + 1; });
    const errors = errorData.items || [];
    const diffSummary = diff && diff.summary ? `新增 ${diff.summary.added || 0} 行 · 删除 ${diff.summary.deleted || 0} 行 · 修改 ${diff.summary.changed || 0} 行` : "无版本差异";
    const changedModules = diff && diff.sections ? Object.entries(diff.sections)
      .filter(([, v]) => v.changed)
      .map(([k]) => `<span class="tag blue">${esc(k)}</span>`).join(" ") : "";
    box.innerHTML = `<div class="card">
      <div class="row u-ai-c">
        <h3 class="u-f2 u-m0">${esc(item.title)}</h3>
        <a class="btn small" href="#/viewer/${encodeURIComponent(item.run_id)}">打开图片级结果</a>
      </div>
      <div class="grid grid-4 u-mt-10">
        <div class="kpi"><div class="v">${esc(run.status || "-")}</div><div class="k">运行状态</div></div>
        <div class="kpi"><div class="v">${pct(item.metrics && item.metrics.accuracy)}</div><div class="k">准确率</div></div>
        <div class="kpi"><div class="v">${pct(item.metrics && item.metrics.judge_coverage)}</div><div class="k">裁判覆盖率</div></div>
        <div class="kpi"><div class="v">${(item.metrics && item.metrics.high_severity_errors) || 0}</div><div class="k">高严重度错误</div></div>
      </div>
      <div class="muted u-mt-8">${esc(metricText(item.metrics))}</div>
      ${item.delta ? `<div class="muted u-mt-4">相对上一轮：${esc(deltaText(item.delta))}</div>` : ""}
      ${item.reason ? `<div class="msg ${item.accepted === false ? "err" : "info"} u-mt-8">${esc(item.reason)}</div>` : ""}
      ${run.__error ? `<div class="msg err u-mt-8">运行信息读取失败：${esc(run.__error)}</div>` : ""}
      <div class="grid grid-3 u-mt-12">
        ${distTable("裁判结论", counts)}
        ${distTable("错误模块", errorData.module_counts || {})}
        ${distTable("严重度", errorData.severity_counts || {})}
      </div>
      <div class="u-mt-12">
        <h4>提示词变更</h4>
        <div class="muted">${esc(diffSummary)}</div>
        <div class="u-mt-5">${changedModules || '<span class="muted">无模块变更</span>'}</div>
      </div>
      <div class="u-mt-12">
        <h4>本轮错误样本</h4>
        <div class="tbl-scroll"><table class="tbl"><thead><tr><th>图片</th><th>结论</th><th>严重度</th><th>模块</th><th>原因</th></tr></thead><tbody>
        ${errors.map(e => `<tr><td class="mono">${esc(e.image)} R${e.repeat}</td><td>${statusTag(e.verdict)}</td><td>${esc(e.severity || "-")}</td><td>${(e.modules || []).map(m => `<span class="tag orange">${esc(m)}</span>`).join("") || "-"}</td><td class="muted u-maxw-360">${esc((e.reason || "").slice(0, 140))}</td></tr>`).join("") || '<tr><td colspan="5" class="muted">本轮没有错误样本</td></tr>'}
        </tbody></table></div>
      </div>
    </div>`;
  };

  const render = async () => {
    const job = await get(`/api/workflows/${encodeURIComponent(jobId)}`);
    if (!location.hash.startsWith("#/workflow/")) return;
    const rounds = job.rounds || [];
    // 迭代任务本身不带项目名，从某一轮的运行里取（首轮即可）
    if (rounds[0] && rounds[0].dataset) adoptProjectOf({ ref: rounds[0].dataset });
    // 只在数据真正变化时重建页面，避免闪烁
    const jobSig = JSON.stringify({id: jobId, s: job.status, p: job.phase, pr: job.progress, e: job.error, sr: job.stop_reason,
      osp: job.optimizer_sub_phase, r: (job.rounds||[]).length, pr2: job.pending_round, ba: job.best_version,
      bs: job.best_score, is_active: job.is_active});
    if (state._wfLastSig === jobSig) {
      if (job.is_active) schedulePagePoll(render, 2500);
      return;
    }
    state._wfLastSig = jobSig;
    const pending = job.pending_round;
    const timeline = [{
      key: "baseline", title: `基线 V${job.source_version}`, version: job.source_version,
      source_version: null, run_id: job.baseline_run_id, metrics: job.baseline_metrics || (rounds.length ? null : job.best_metrics),
      accepted: null, reason: "基线运行", prompt_name: job.prompt_name,
    }].concat(rounds.map(r => ({
      key: `round-${r.round}`, title: `第 ${r.round} 轮 · V${r.source_version || job.source_version} → V${r.version}`,
      version: r.version, source_version: r.source_version, run_id: r.run_id,
      metrics: r.metrics, delta: r.delta, accepted: r.accepted, reason: r.reason,
      prompt_name: job.prompt_name,
    })));
    if (pending && !rounds.some(r => r.run_id === pending.run_id)) {
      timeline.push({
        key: "pending", title: `当前候选 · V${pending.source_version || job.source_version} → V${pending.version}`,
        version: pending.version, source_version: pending.source_version, run_id: pending.run_id,
        metrics: null, accepted: null, pending: true,
        reason: job.progress || job.stop_reason || "候选正在运行或等待裁判",
        prompt_name: job.prompt_name,
      });
    }
    const selectedKey = timeline.some(x => x.key === state._wfSelected[jobId])
      ? state._wfSelected[jobId]
      : (timeline.length > 1 ? timeline[timeline.length - 1].key : "baseline");
    state._wfSelected[jobId] = selectedKey;
    const selected = timeline.find(x => x.key === selectedKey) || timeline[0];
    const bestMetrics = job.best_metrics || {};
    $("#app").innerHTML = `
    <div class="page-title">迭代详情 <span class="muted mono u-fs-xs">${esc(job.id)}</span></div>
    <div class="card">
      <div class="row u-ai-c">
        <div class="u-f3">
          <h3 class="u-m-0-0-6">${esc(job.prompt_name)} · 源版本 V${job.source_version}</h3>
          <div class="muted">${esc(job.dataset || "")} · 分析模型 ${esc(job.model || "-")} · 裁判模型 ${esc(job.judge_model || "-")}</div>
          <div class="u-mt-6">${statusTag(job.status)} <span class="tag blue">${esc(job.phase || "-")}</span>${job.progress ? ` <span class="tag blue">${esc(job.progress)}</span>` : ""}${job.optimizer_sub_phase ? ` <span class="tag orange">${esc(job.optimizer_sub_phase)}</span>` : ""}</div>
          ${job.stop_reason || job.error ? `<div class="msg ${job.error ? "err" : "info"} u-mt-8">${esc(job.stop_reason || job.error)}</div>` : ""}
        </div>
        <div class="u-f1 u-ta-r">
          ${job.is_active ? `<button class="btn" id="wf-pause">暂停</button>` : (["paused","waiting_for_review","waiting_for_judge","failed"].includes(job.status) ? `<button class="btn primary" id="wf-resume">继续迭代</button>` : "")}
          <a class="btn small" href="#/judge-iter">返回列表</a>
        </div>
      </div>
    </div>
    <div class="grid grid-4">
      <div class="kpi"><div class="v">${rounds.length}/${job.max_rounds}</div><div class="k">已完成轮次</div></div>
      <div class="kpi"><div class="v">V${job.best_version}</div><div class="k">当前最优版本</div></div>
      <div class="kpi"><div class="v">${pct(bestMetrics.accuracy)}</div><div class="k">最优准确率</div></div>
      <div class="kpi"><div class="v">${pct(bestMetrics.judge_coverage)}</div><div class="k">最优裁判覆盖率</div></div>
    </div>
    <div class="card">
      <h3>每次迭代与结果</h3>
      <div class="tbl-scroll"><table class="tbl"><thead><tr><th>轮次</th><th>版本变化</th><th>运行</th><th>质量结果</th><th>相对变化</th><th>决策</th><th>原因</th></tr></thead><tbody>
      ${timeline.map(item => `<tr data-key="${esc(item.key)}" style="cursor:pointer;${item.key === selectedKey ? "background:#eef4ff" : ""}">
        <td>${esc(item.title.split(" · ")[0])}</td>
        <td>${item.source_version ? `V${item.source_version} → V${item.version}` : `V${item.version}`}</td>
        <td class="mono u-fs-xs">${esc(item.run_id || "-")}</td>
        <td class="muted">${esc(metricText(item.metrics))}</td>
        <td class="muted">${esc(deltaText(item.delta))}</td>
        <td>${decisionTag(item)}</td>
        <td class="muted u-maxw-260">${esc((item.reason || "").slice(0, 120))}</td>
      </tr>`).join("")}
      </tbody></table></div>
      <div class="muted u-mt-6">点击任意一轮查看该轮的裁判分布、错误样本和提示词变更。</div>
    </div>
    <div id="wf-detail"></div>`;
    $$(".tbl tbody tr[data-key]").forEach(row => row.onclick = () => {
      state._wfSelected[jobId] = row.dataset.key;
      $$(".tbl tbody tr[data-key]").forEach(r => r.style.background = r.dataset.key === row.dataset.key ? "#eef4ff" : "");
      const item = timeline.find(x => x.key === row.dataset.key);
      if (item) loadRoundDetail(item);
    });
    const pauseBtn = $("#wf-pause");
    if (pauseBtn) pauseBtn.onclick = async () => {
      try { await post(`/api/workflows/${encodeURIComponent(jobId)}/pause`, {}); toast("已发送暂停信号"); render(); }
      catch (e) { toast(e.message, false); }
    };
    const resumeBtn = $("#wf-resume");
    if (resumeBtn) resumeBtn.onclick = async () => {
      try { await post(`/api/workflows/${encodeURIComponent(jobId)}/resume`, {}); toast("迭代已继续"); render(); }
      catch (e) { toast(e.message, false); }
    };
    if (selected) loadRoundDetail(selected);
    if (job.is_active) schedulePagePoll(render, 2500);
  };

  try {
    await render();
  } catch (e) {
    $("#app").innerHTML = `<div class="page-title">迭代详情</div><div class="msg err">${esc(e.message)}</div><p><a class="btn" href="#/judge-iter">返回迭代列表</a></p>`;
  }
});

// ---------------------------------------------------------------- 模板管理
// 模板管理已并入「配置」页；保留旧路由做跳转，避免老书签失效
route("profiles", async () => {
  state._configTab = "profiles";
  if (location.hash === "#/config") navigate();
  else location.hash = "#/config";
});

async function renderProfilesPage(container) {
  const data = await get("/api/prompt-profiles");
  const profiles = data.items || [];
  const types = [
    ["generator", "提示词生成器"],
    ["optimizer", "提示词优化器"],
    ["judge", "裁判模板"],
  ];
  let selectedName = null;
  let filterType = "";

  const render = () => {
    const filtered = filterType ? profiles.filter(p => p.type === filterType) : profiles;
    const grouped = {};
    types.forEach(([t, label]) => { grouped[t] = filtered.filter(p => p.type === t); });
    container.innerHTML = `
    <div class="muted u-mb-10">管理生成器、优化器、裁判三类 system prompt 模板。内置模板不可修改或删除，可另存为自定义模板。</div>
    <div class="grid u-gtc-280">
      <div>
        <div class="card">
          <div class="row u-ai-c u-mb-8">
            <h3 class="u-f1 u-m0">模板</h3>
            <span class="tag blue">${profiles.length}</span>
          </div>
          <select class="u-mb-8" id="pf-filter">
            <option value="">全部类型</option>
            ${types.map(([t, label]) => `<option value="${t}" ${filterType === t ? "selected" : ""}>${label}</option>`).join("")}
          </select>
          <div id="pf-list">
            ${types.map(([t, label]) => {
              const items = grouped[t];
              if (!items.length) return "";
              return `<div class="p-group">
                <div class="p-group-head"><span class="p-group-arrow">▾</span><span class="u-f1">${label}</span><span class="tag">${items.length}</span></div>
                <div class="p-group-items">
                  ${items.map(p => `<div class="img-item ${p.name === selectedName ? "active" : ""}" data-p="${esc(p.name)}">
                    <div class="u-f1 u-minw-0">
                      <div class="u-ellipsis">${esc(p.name)}</div>
                      <div class="muted u-fs-xs">${p.builtin ? "内置" : "自定义"}${p.description ? " · " + esc(p.description) : ""}</div>
                    </div>
                    ${p.builtin ? '<span class="tag green">内置</span>' : '<span class="tag blue">自定义</span>'}
                  </div>`).join("")}
                </div></div>`;
            }).join("") || emptyState("还没有模板", "去填写名称", null, "pf-new-name")}
          </div>
        </div>
      </div>
      <div id="pf-detail"><div class="card muted">← 选择左侧模板查看与编辑，或创建新模板</div></div>
    </div>`;
    $("#pf-filter").onchange = () => { filterType = $("#pf-filter").value; render(); };
    $$("#pf-list .img-item").forEach(it => it.onclick = () => { selectedName = it.dataset.p; render(); showProfile(selectedName); });
    // 分组折叠
    $$("#pf-list .p-group-head").forEach(h => h.onclick = () => {
      const items = h.nextElementSibling;
      if (items) {
        setShown(items, items.classList.contains("u-hide"));
        h.querySelector(".p-group-arrow").textContent = items.classList.contains("u-hide") ? "▸" : "▾";
      }
    });
  };

  const showProfile = (name) => {
    const p = profiles.find(x => x.name === name);
    if (!p) return;
    const box = $("#pf-detail");
    box.innerHTML = `<div class="card">
      <div class="row u-ai-c">
        <h3 class="u-f2 u-m0">${esc(p.name)} ${p.builtin ? '<span class="tag green">内置</span>' : '<span class="tag blue">自定义</span>'}</h3>
      </div>
      <div class="muted u-my-6">类型：${p.type === "generator" ? "提示词生成器" : p.type === "optimizer" ? "提示词优化器" : "裁判模板"}${p.description ? " · " + esc(p.description) : ""}</div>
      ${p.builtin ? '<div class="msg info">内置模板不可修改或删除。可在下方复制为自定义模板后编辑。</div>' : ""}
      <label class="f">模板内容（system prompt）</label>
      <textarea id="pf-content" rows="14" ${p.builtin ? "readonly" : ""}>${esc(p.content)}</textarea>
      ${p.builtin ? `
        <div class="row u-mt-10">
          <div><label class="f">另存为名称</label><input type="text" id="pf-copy-name" placeholder="新模板名称"></div>
          <div><label class="f">说明</label><input type="text" id="pf-copy-desc" placeholder="可选"></div>
          <div class="u-f0 u-as-fe"><button class="btn primary" id="pf-copy">复制为自定义模板</button></div>
        </div>` : `
        <div class="row u-mt-10">
          <div><label class="f">说明</label><input type="text" id="pf-desc" value="${esc(p.description || "")}"></div>
          <div class="u-f0 u-as-fe"><button class="btn primary" id="pf-save">保存修改</button></div>
          <div class="u-f0 u-as-fe"><button class="btn small danger" id="pf-del">删除模板</button></div>
        </div>`}
    </div>`;
    if (!p.builtin) {
      $("#pf-save").onclick = async () => {
        try { await put(`/api/prompt-profiles/${encodeURIComponent(p.name)}`, { name: p.name, type: p.type, content: $("#pf-content").value, description: $("#pf-desc").value }); toast("模板已保存"); await refreshProfiles(); }
        catch (e) { toast(e.message, false); }
      };
      $("#pf-del").onclick = async () => {
        if (!(await confirmDlg(`确定删除模板「${p.name}」？`, { title: "删除模板" }))) return;
        try { await del(`/api/prompt-profiles/${encodeURIComponent(p.name)}`); toast("已删除"); selectedName = null; await refreshProfiles(); }
        catch (e) { toast(e.message, false); }
      };
    } else {
      $("#pf-copy").onclick = async () => {
        const newName = $("#pf-copy-name").value.trim();
        if (!newName) return toast("请填写新模板名称", false);
        try { await put(`/api/prompt-profiles/${encodeURIComponent(newName)}`, { name: newName, type: p.type, content: $("#pf-content").value, description: $("#pf-copy-desc").value }); toast("已复制为自定义模板"); selectedName = newName; await refreshProfiles(); }
        catch (e) { toast(e.message, false); }
      };
    }
  };

  const refreshProfiles = async () => {
    const fresh = await get("/api/prompt-profiles");
    profiles.length = 0;
    profiles.push(...(fresh.items || []));
    render();
    if (selectedName) showProfile(selectedName);
    else showNewForm();
  };

  const showNewForm = () => {
    $("#pf-detail").innerHTML = `<div class="card">
      <h3>创建新模板</h3>
      <div class="row">
        <div><label class="f">模板名称</label><input type="text" id="pf-new-name" placeholder="如：头盔检测裁判规则"></div>
        <div><label class="f">类型</label><select id="pf-new-type">${types.map(([t, label]) => `<option value="${t}">${label}</option>`).join("")}</select></div>
        <div><label class="f">说明</label><input type="text" id="pf-new-desc" placeholder="可选"></div>
      </div>
      <label class="f">模板内容（system prompt）</label>
      <textarea id="pf-new-content" rows="12" placeholder="填写模板内容…"></textarea>
      <div class="u-mt-10"><button class="btn primary" id="pf-new-save">创建模板</button></div>
    </div>`;
    $("#pf-new-save").onclick = async () => {
      const name = $("#pf-new-name").value.trim();
      if (!name) return toast("请填写名称", false);
      try { await put(`/api/prompt-profiles/${encodeURIComponent(name)}`, { name, type: $("#pf-new-type").value, content: $("#pf-new-content").value, description: $("#pf-new-desc").value }); toast("模板已创建"); selectedName = name; await refreshProfiles(); }
      catch (e) { toast(e.message, false); }
    };
  };

  render();
  if (!selectedName) showNewForm();
}

// ---------------------------------------------------------------- 结果查看器

// ---------------------------------------------------------------- 结果查看器
route("viewer", async (runId) => {
  if (!runId) { location.hash = "#/runs"; return; }
  runId = decodeURIComponent(runId);
  const run = await get(`/api/runs/${runId}`);
  adoptProjectOf(run);
  $("#app").innerHTML = `<div class="viewer-page">
  <div class="page-title">结果查看器 <span class="muted mono u-fs-xs">${esc(runId)}</span></div>
  <div class="card v-head">
    <div class="v-head-meta">
      <span class="v-chip" title="图片集"><span class="v-chip-k">图片集</span>${esc(run.dataset_project || "未归档项目")} / ${esc(run.dataset_name || run.dataset)}${run.dataset_split ? ` · ${esc(run.dataset_split)}` : ""}</span>
      <span class="v-chip" title="提示词（运行时快照）"><span class="v-chip-k">提示词</span>${esc(run.prompt_name)} V${run.prompt_version}</span>
      <span class="v-chip" title="模型"><span class="v-chip-k">模型</span>${esc(run.model)}</span>
      ${run.repeat > 1 ? `<span class="v-chip" title="每个样本重复调用次数"><span class="v-chip-k">重复</span>×${run.repeat}</span>` : ""}
      ${statusTag(run.status)}
      <span class="v-prog" id="v-prog">${run.done + run.failed}/${run.total}${run.parse_failed ? ` · 解析失败 ${run.parse_failed}` : ""}</span>
    </div>
    <div class="v-head-actions">
      <div class="v-togs" role="group" aria-label="显示内容">
        <label><input type="checkbox" class="v-tog" value="orig" checked><span>原图</span></label>
        <label><input type="checkbox" class="v-tog" value="ann" checked><span>推理图</span></label>
        <label><input type="checkbox" class="v-tog" value="json" checked><span>JSON</span></label>
        <label><input type="checkbox" class="v-tog" value="prompt"><span>提示词</span></label>
      </div>
      <span class="v-sep" aria-hidden="true"></span>
      <button class="btn small" id="v-batch">批量审核</button>
      <button class="btn small" id="v-stab">稳定性统计</button>
      <a class="btn small primary" href="#/judge-iter">裁判与迭代 →</a>
      <a class="btn small" href="/api/runs/${encQ(runId)}/export.csv">导出 CSV</a>
      <a class="btn small" href="#/runs">返回列表</a>
    </div>
  </div>
  <div id="v-stabbox"></div>
  <div class="viewer-layout">
    <div class="card u-viewer-col">
      <div class="v-list-tools">
        <input class="u-minw-0" type="text" id="v-search" placeholder="搜索文件名…" aria-label="搜索文件名">
        <select class="u-minw-0" id="v-filter" aria-label="按状态筛选">
          <option value="">全部</option>
          <option value="parsefail">解析失败</option>
          <option value="callfail">调用失败</option>
          <option value="none">未运行</option>
        </select>
      </div>
      <div class="v-list-meta" id="v-list-meta"></div>
      <div class="img-list" id="v-list"></div>
    </div>
    <div id="v-main"><div class="v-empty">
      <div class="v-empty-title">从左侧选择一张图片</div>
      <div class="v-empty-tip">选择后可对比原图与推理图、查看 JSON、并在同一页完成人工审核。</div>
      <div class="v-empty-keys">
        <span><kbd>←</kbd><kbd>→</kbd> 翻图</span>
        <span><kbd>1</kbd>–<kbd>5</kbd> 审核并跳到下一张</span>
      </div>
    </div></div>
  </div>
  </div>`;

  let images = [];
  let selectedRel = null;
  let currentSave = null;  // 当前图片面板的保存函数，快捷键保存时调用

  function matchFilter(im, f) {
    if (!f) return true;
    return im.repeats.some(r => {
      if (f === "none") return !r.exists;
      if (!r.exists) return false;
      if (f === "callfail") return !!r.error;
      if (f === "parsefail") return !r.error && !r.parse_ok;
      return !r.error && r.parse_ok && r.overall_status === f;
    });
  }

  function renderList() {
    const listEl = $("#v-list");
    const scroll = listEl.scrollTop;
    const q = ($("#v-search").value || "").trim().toLowerCase();
    const f = $("#v-filter").value;
    const shown = images.map((im, i) => ({ im, i }))
      .filter(x => (!q || x.im.rel.toLowerCase().includes(q)) && matchFilter(x.im, f));
    listEl.innerHTML = shown.map(({ im, i }) => {
      const dots = im.repeats.map(r => {
        let c = "gray";
        if (r.exists) c = r.error ? "red" : r.parse_ok ? statusDotClass(r.overall_status) : "orange";
        const tip = !r.exists ? "未运行" : r.error ? `调用失败：${r.error}` : (r.overall_status || "解析失败");
        return `<span class="dot ${c}" title="第${r.repeat}次：${esc(tip)}"></span>`;
      }).join("");
      const ok = im.repeats.filter(r => r.exists && !r.error && r.parse_ok).length;
      const done = im.repeats.filter(r => r.exists).length;
      const cls = im.rel === selectedRel ? "active" : "";
      return `<div class="img-item ${cls}" data-i="${i}" role="option" aria-selected="${im.rel === selectedRel}">
        <span class="img-name">${esc(im.rel)}</span>
        <span class="img-meta"><span class="img-dots">${dots}</span>${im.repeats.length > 1 ? `<span class="img-count">${ok}/${done}</span>` : ""}</span>
      </div>`;
    }).join("") || `<div class="empty"><div class="empty-text">没有匹配的图片</div></div>`;
    listEl.scrollTop = scroll;
    const meta = $("#v-list-meta");
    if (meta) meta.innerHTML = shown.length === images.length
      ? `<span>共 <b>${images.length}</b> 张</span>`
      : `<span>显示 <b>${shown.length}</b> / ${images.length} 张</span>`;
    $$("#v-list .img-item").forEach(it => it.onclick = () => {
      selectedRel = images[Number(it.dataset.i)].rel;
      $$("#v-list .img-item").forEach(x => { x.classList.remove("active"); x.setAttribute("aria-selected", "false"); });
      it.classList.add("active");
      it.setAttribute("aria-selected", "true");
      showImage(images[Number(it.dataset.i)]);
    });
  }

  async function loadList() {
    const data = await get(`/api/runs/${runId}/images`);
    images = data.items;
    const filter = $("#v-filter");
    const current = filter.value;
    const statuses = [...new Set(images.flatMap(im => im.repeats
      .filter(r => r.exists && !r.error && r.parse_ok && r.overall_status != null)
      .map(r => String(r.overall_status))))].sort();
    filter.innerHTML = `<option value="">全部</option>`
      + statuses.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join("")
      + `<option value="parsefail">解析失败</option><option value="callfail">调用失败</option><option value="none">未运行</option>`;
    if (statuses.includes(current) || ["parsefail", "callfail", "none", ""].includes(current)) filter.value = current;
    renderList();
  }
  await loadList();
  $("#v-search").oninput = renderList;
 $("#v-filter").onchange = renderList;

  // 审核快捷键：1-5 保存结论并自动跳下一张，←/→ 在筛选后的列表里翻图
  document.onkeydown = (e) => {
    const tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const items = $$("#v-list .img-item");
    if (!items.length) return;
    const cur = items.findIndex(x => x.classList.contains("active"));
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      // 未选中时先落在第一张，避免「按了没反应」
      if (cur < 0) { e.preventDefault(); items[e.key === "ArrowRight" ? 0 : items.length - 1].click(); return; }
      const next = items[cur + (e.key === "ArrowRight" ? 1 : -1)];
      // 到头不循环，但把列表滚到可见处，用户知道已经到底
      if (next) { e.preventDefault(); next.click(); next.scrollIntoView({ block: "nearest" }); }
      return;
    }
    const verdicts = { "1": "正确", "2": "误报", "3": "漏报", "4": "部分正确", "5": "无法判断" };
    if (verdicts[e.key] && $("#review-verdict") && currentSave) {
      e.preventDefault();
      $("#review-verdict").value = verdicts[e.key];
      currentSave(true);
    }
  };

  // 批量审核：把未审核的结果统一标记，期望状态/框自动取模型输出并沉淀真值
  $("#v-batch").onclick = async () => {
    let s;
    try { s = await get(`/api/runs/${runId}/reviews`); } catch (e) { return toast(e.message, false); }
    const dlg = openDlg(`<h3>批量审核</h3>
      <div class="muted u-mb-10">已审核 <b>${s.total}</b> 条 / 共 ${run.done} 条结果。批量标记会把<b>尚未审核</b>的结果统一标为所选结论；期望状态与期望框自动取模型输出，并同步沉淀到真值。</div>
      <div class="row u-ai-c"><label class="f u-m0">统一标记为</label>
        <select class="u-f1" id="b-verdict">${["正确","误报","漏报","部分正确","无法判断"].map(v => `<option>${v}</option>`).join("")}</select></div>
      <div class="muted u-mt-8 u-mb-12">调用失败的结果不会被标记；标记「正确」时解析失败的也会跳过。已有审核结论的条目不受影响。</div>
      <div class="row u-jc-fe"><button class="btn" id="b-cancel">取消</button><button class="btn primary" id="b-ok">开始标记</button></div>`);
    $("#b-cancel", dlg.box).onclick = dlg.close;
    $("#b-ok", dlg.box).onclick = async () => {
      const btn = $("#b-ok", dlg.box);
      btn.disabled = true; btn.textContent = "标记中…";
      try {
        const r = await post(`/api/runs/${runId}/reviews/batch`, { verdict: $("#b-verdict", dlg.box).value, scope: "unreviewed" });
        dlg.close();
        toast(`批量标记完成：新标记 ${r.saved} 条，跳过 ${r.skipped} 条`);
        await loadList();
        const cur = $("#v-list .img-item.active");
        if (cur) cur.click();
      } catch (e) {
        toast(e.message, false);
        btn.disabled = false; btn.textContent = "开始标记";
      }
    };
  };

 const pollViewer = async () => {
    pollTimer = null;
    if (!location.hash.startsWith("#/viewer/")) return;
    try {
      const r = await get(`/api/runs/${runId}`);
      const progress = $("#v-prog");
      if (progress) progress.textContent = `${r.done + r.failed}/${r.total}${r.parse_failed ? ` · 解析失败 ${r.parse_failed}` : ""}`;
      if (r.status === "running") await loadList();
      else await loadList();
      if (r.status === "running" && location.hash.startsWith("#/viewer/")) {
        pollTimer = schedulePagePoll(pollViewer, 3000);
      }
    } catch (e) {}
  };
  pollTimer = schedulePagePoll(pollViewer, 3000);

  $$(".v-tog").forEach(c => c.onchange = () => {
    const cur = $("#v-list .img-item.active");
    if (cur) cur.click();
  });

  $("#v-stab").onclick = async () => {
    try {
      const s = await get(`/api/runs/${runId}/stability`);
      const box = $("#v-stabbox");
      if (box.innerHTML) { box.innerHTML = ""; return; }
      box.innerHTML = `<div class="card">
        <h3>稳定性统计（×${s.repeat} 复现）</h3>
        <div class="grid grid-4">
          <div class="kpi"><div class="v">${s.parse_rate != null ? (s.parse_rate * 100).toFixed(1) + "%" : "-"}</div><div class="k">JSON 解析成功率</div></div>
          <div class="kpi"><div class="v">${s.protocol_valid_rate != null ? (s.protocol_valid_rate * 100).toFixed(1) + "%" : "-"}</div><div class="k">最小协议合规率</div></div>
          <div class="kpi"><div class="v">${s.status_agree_avg != null ? (s.status_agree_avg * 100).toFixed(1) + "%" : "-"}</div><div class="k">状态一致率（均值）</div></div>
          <div class="kpi"><div class="v">${s.cls_agree_avg != null ? (s.cls_agree_avg * 100).toFixed(1) + "%" : "-"}</div><div class="k">分类标签一致率</div></div>
          <div class="kpi"><div class="v">${s.nameset_agree_avg != null ? (s.nameset_agree_avg * 100).toFixed(1) + "%" : "-"}</div><div class="k">目标集合一致率（Jaccard）</div></div>
        </div>
        <div class="grid grid-3 u-mt-12">
          ${distTable("状态分布", s.status_dist)}
          ${distTable("分类标签分布", s.classification_dist)}
          ${distTable(`目标标签分布（共 ${s.object_total || 0} 个）`, s.object_label_dist)}
        </div>
        <div class="muted u-mt-6">状态/分类不稳定图片 <span class="tag orange">${s.flaky_images.length}</span> 张</div>
        ${s.flaky_images.length ? `<div class="muted u-mt-8">不稳定图片（点击跳转）：${s.flaky_images.map(f =>
          `<a href="#" data-flaky="${esc(f)}" class="link">${esc(f)}</a>`).join("、")}</div>` : ""}
      </div>`;
      $$("#v-stabbox [data-flaky]").forEach(a => a.onclick = () => {
        const idx = images.findIndex(im => im.rel === a.dataset.flaky);
        if (idx < 0) return;
        selectedRel = a.dataset.flaky;
        $("#v-search").value = "";
        $("#v-filter").value = "";
        renderList();
        const el = $$("#v-list .img-item").find(x => images[Number(x.dataset.i)].rel === a.dataset.flaky);
        if (el) el.scrollIntoView({ block: "center" });
        showImage(images[idx]);
      });
    } catch (e) { toast(e.message, false); }
  };

  async function showImage(im) {
    const togs = $$(".v-tog").filter(c => c.checked).map(c => c.value);
    const main = $("#v-main");
    const firstOk = im.repeats.find(r => r.exists);
    main.innerHTML = `<div class="card"><div class="row u-ai-c">
      <h3 class="u-f3 u-m0">${esc(im.rel)}</h3>
      <div class="u-f1"><select id="v-rep">${im.repeats.map(r =>
        `<option value="${r.repeat}" ${!r.exists ? "disabled" : ""} ${firstOk && r.repeat === firstOk.repeat ? "selected" : ""}>第 ${r.repeat} 次${r.exists ? "" : "（无）"}</option>`).join("")}
        ${run.repeat > 1 ? `<option value="all">全部对比</option>` : ""}</select></div>
    </div></div><div id="v-panels"></div>`;

    async function renderPanels() {
      const rep = $("#v-rep").value;
      const box = $("#v-panels");
      if (rep === "all") {
        const results = [];
        for (const r of im.repeats) {
          if (r.exists) {
            try { results.push({ rep: r.repeat, data: await get(`/api/runs/${runId}/result?rel=${encQ(im.rel)}&repeat=${r.repeat}`) }); }
            catch (e) {}
          }
        }
        box.innerHTML = `<div class="panels">${results.map(x => `
          <div class="panel"><h4>第 ${x.rep} 次 ${x.data._meta && x.data._meta.error ? '<span class="tag red">调用失败</span>' : statusTag(x.data.overall_status)}</h4>
          ${resultPanel(x.data)}</div>`).join("")}</div>`;
        return;
      }
      const r = Number(rep);
      let data = null;
      try { data = await get(`/api/runs/${runId}/result?rel=${encQ(im.rel)}&repeat=${r}`); } catch (e) {}
      const metaErr = data && data._meta && data._meta.error;
      let html = `<div class="panels">`;
      if (togs.includes("orig")) html += `<div class="panel"><h4>原图</h4>
        <img src="/api/file/run/${encQ(runId)}/image/${enc(im.rel)}" data-zoom="1"></div>`;
      if (togs.includes("ann")) {
        const hasObj = data && data.objects && data.objects.length;
        html += `<div class="panel"><h4>推理图</h4>${hasObj
          ? `<img src="/api/file/run/${runId}/annotated/${enc(im.rel)}?repeat=${r}" data-zoom="1">`
          : '<div class="muted">无目标 / 无推理图</div>'}</div>`;
      }
      if (togs.includes("json")) html += `<div class="panel"><h4>模型输出 ${data ? (metaErr ? '<span class="tag red">调用失败</span>' : statusTag(data.overall_status)) : ""}</h4>
        ${metaErr ? `<div class="msg err u-m-0-0-8">${esc(metaErr)}</div>` : ""}
        ${data ? resultPanel(data) : '<div class="json-view">结果不存在</div>'}</div>`;
      if (togs.includes("prompt")) html += `<div class="panel"><h4>提示词（运行时快照）</h4>
        <div class="json-view">${esc(run.user_prompt_snapshot)}</div></div>`;
      const review = await get(`/api/runs/${runId}/review?rel=${encQ(im.rel)}&repeat=${r}`).catch(() => ({}));
      const judgment = await get(`/api/runs/${runId}/judgment?rel=${encQ(im.rel)}&repeat=${r}`).catch(() => ({}));
      // 真值互通：该图若已在真值任务中标注，预填期望状态并提示来源
      const truthInfo = await get(`/api/truth/for-image?dataset=${encQ(run.dataset)}&rel=${encQ(im.rel)}`).catch(() => ({}));
      const truthPrefill = !review.expected_status && truthInfo && truthInfo.kind === "single" && (truthInfo.labels || []).length
        ? truthInfo.labels[0] : (review.expected_status || "");
      const truthHint = truthInfo && truthInfo.task ? `<div class="msg info u-m-0-0-8">真值任务「${esc(truthInfo.task_name)}」：${(truthInfo.labels || []).length ? `标签 <b>${truthInfo.labels.map(esc).join("、")}</b>` : "该图暂无标签"}${truthInfo.source === "review" ? ' <span class="tag blue">审核沉淀</span>' : truthInfo.source === "manual" ? ' <span class="tag orange">手动标注</span>' : ""}</div>` : "";
      html += `<div class="panel review-panel"><h4>人工审核（独立于模型结果）</h4>
        <div class="muted u-fs-xs u-mb-6">快捷键：<b>1</b> 正确 · <b>2</b> 误报 · <b>3</b> 漏报 · <b>4</b> 部分正确 · <b>5</b> 无法判断（自动保存并跳下一张）· <b>←/→</b> 翻图</div>
        ${truthHint}
        <div class="row"><select id="review-verdict"><option value="">未审核</option>${["正确","误报","漏报","部分正确","无法判断"].map(v => `<option ${review.verdict === v ? "selected" : ""}>${v}</option>`).join("")}</select>
        <input id="review-status" placeholder="人工期望状态" value="${esc(truthPrefill)}"></div>
        <div class="review-editor"><img id="review-img" src="/api/file/run/${encQ(runId)}/image/${enc(im.rel)}"><canvas id="review-canvas"></canvas></div>
        <div class="row review-tool"><input id="review-label" placeholder="框标签名称"><input id="review-value" placeholder="标签值"><input id="review-evidence" placeholder="人工证据"></div>
        <div class="muted">在图片上拖动绘制矩形框；可载入模型框后修订。</div>
        <div><button class="btn small" id="review-copy">载入模型框</button><button class="btn small" id="review-clear">清空人工框</button></div>
        <div id="review-objects"></div>
        <textarea id="review-reason" rows="2" placeholder="审核原因">${esc(review.reason || "")}</textarea>
        <button class="btn small primary" id="review-save">保存审核</button></div>`;
      if (judgment && judgment.verdict) html += `<div class="panel"><h4>裁判报告 ${statusTag(judgment.verdict)}</h4>
        <div class="muted">${esc(judgment.reason || "")}</div>
        ${(judgment.fault_location || []).map(f => `<div class="msg info u-my-6"><b>${esc(f.module)}</b>：${esc(f.problem)}<br><span class="muted">建议：${esc(f.suggestion)}</span></div>`).join("")}</div>`;
      box.innerHTML = html + "</div>";
      let reviewObjects = []; try { reviewObjects = JSON.parse(JSON.stringify(review.expected_objects || [])); } catch(e) { reviewObjects = []; } if (!Array.isArray(reviewObjects)) reviewObjects = [];
      const reviewImg = $("#review-img"), reviewCanvas = $("#review-canvas"); if (!reviewCanvas) return; const reviewCtx = reviewCanvas.getContext("2d"); if (!reviewCtx) return;
      let drawing = null;
      const drawReview = () => {
        if (!reviewCanvas.width) return;
        reviewCtx.clearRect(0, 0, reviewCanvas.width, reviewCanvas.height);
        reviewCtx.lineWidth = Math.max(2, reviewCanvas.width / 600); reviewCtx.font = `${Math.max(14, reviewCanvas.width / 55)}px Microsoft YaHei`;
        [...reviewObjects, ...(drawing ? [{ bbox: drawing, labelName: "新框" }] : [])].forEach((o, i) => {
          const b = o.bbox || []; if (b.length !== 4) return; const x=Math.min(b[0],b[2]), y=Math.min(b[1],b[3]), w=Math.abs(b[2]-b[0]), h=Math.abs(b[3]-b[1]);
          reviewCtx.strokeStyle = i === reviewObjects.length ? "#2e6de6" : "#18a058"; reviewCtx.fillStyle = reviewCtx.strokeStyle; reviewCtx.strokeRect(x,y,w,h); reviewCtx.fillText(o.labelName || `目标${i+1}`, x+3, Math.max(16,y-4));
        });
      };
      const renderReviewObjects = () => {
        $("#review-objects").innerHTML = reviewObjects.map((o,i) => `<div class="review-object" data-ri="${i}"><div class="row"><input data-k="labelName" value="${esc(o.labelName || "")}" placeholder="labelName"><input data-k="labelValue" value="${esc(o.labelValue || "")}" placeholder="labelValue"><button class="btn small danger" data-rdel="${i}">删除框</button></div><input data-k="evidence" value="${esc(o.evidence || "")}" placeholder="evidence"><div class="bbox-edit"><span class="muted">bbox</span>${[0,1,2,3].map((axis) => `<input type="number" data-bbox="${axis}" value="${Number((o.bbox || [0,0,0,0])[axis])}" aria-label="bbox ${axis}">`).join("")}</div></div>`).join("") || emptyState("还没有矩形框——在图片上拖动绘制，或载入模型输出后修订", "载入模型框", null, "review-copy");
        $$("#review-objects [data-k]").forEach(input => input.oninput = () => { reviewObjects[Number(input.closest("[data-ri]").dataset.ri)][input.dataset.k] = input.value; drawReview(); });
        $$("#review-objects [data-bbox]").forEach(input => input.oninput = () => { const object = reviewObjects[Number(input.closest("[data-ri]").dataset.ri)]; object.bbox[Number(input.dataset.bbox)] = Number(input.value); drawReview(); });
        $$("#review-objects [data-rdel]").forEach(b => b.onclick = () => { reviewObjects.splice(Number(b.dataset.rdel),1); renderReviewObjects(); drawReview(); });
      };
      reviewImg.onload = () => { if (reviewImg.naturalWidth) { reviewCanvas.width = reviewImg.naturalWidth; reviewCanvas.height = reviewImg.naturalHeight; } else { reviewCanvas.width = 800; reviewCanvas.height = 600; } drawReview(); };
      reviewImg.onerror = () => { reviewCanvas.width = 800; reviewCanvas.height = 600; drawReview(); };
      if (reviewImg.complete) reviewImg.onload();
      const point = e => { const rect=reviewCanvas.getBoundingClientRect(); const rw = rect.width || 1, rh = rect.height || 1, cw = reviewCanvas.width || 1, ch = reviewCanvas.height || 1; return [Math.round((e.clientX-rect.left)*cw/rw), Math.round((e.clientY-rect.top)*ch/rh)]; };
      reviewCanvas.onpointerdown = e => { const p=point(e); drawing=[p[0],p[1],p[0],p[1]]; reviewCanvas.setPointerCapture(e.pointerId); drawReview(); };
      reviewCanvas.onpointermove = e => { if (!drawing) return; const p=point(e); drawing[2]=p[0]; drawing[3]=p[1]; drawReview(); };
      reviewCanvas.onpointerup = e => { if (!drawing) return; const p=point(e); drawing[2]=p[0]; drawing[3]=p[1]; if (Math.abs(drawing[2]-drawing[0])>3 && Math.abs(drawing[3]-drawing[1])>3) reviewObjects.push({labelName:$("#review-label").value||"人工目标",labelValue:$("#review-value").value,evidence:$("#review-evidence").value,bbox:drawing.map(Number)}); drawing=null; renderReviewObjects(); drawReview(); };
      $("#review-copy").onclick = () => { reviewObjects = (data && data.objects || []).filter(o => o.bbox).map(o => ({labelName:o.name || "目标",labelValue:o.label_value || "",evidence:o.evidence || "",bbox:o.bbox.map(Number)})); renderReviewObjects(); drawReview(); };
      $("#review-clear").onclick = () => { reviewObjects=[]; renderReviewObjects(); drawReview(); };
      renderReviewObjects();
      const doSave = async (advance) => {
        const verdict = $("#review-verdict").value; if (!verdict) return toast("请选择审核结论", false);
        try {
          const resp = await post("/api/reviews", { run_id: runId, rel: im.rel, repeat: r, verdict, expected_status: $("#review-status").value, expected_objects: reviewObjects, reason: $("#review-reason").value });
          let msg = "审核已保存";
          if (resp && resp.truth_sync) {
            if (!resp.truth_sync.skipped) msg += `，已同步到真值任务「${resp.truth_sync.task_name}」`;
            else if (resp.truth_sync.skipped === "manual") msg += "（真值已手动标注，未覆盖）";
          }
          toast(msg);
          if (advance) {
            const items = $$("#v-list .img-item");
            const curIdx = items.findIndex(x => x.classList.contains("active"));
            if (items[curIdx + 1]) items[curIdx + 1].click();
          }
        }
        catch (e) { toast(e.message, false); }
      };
      currentSave = doSave;
      $("#review-save").onclick = () => doSave(false);
    }
    $("#v-rep").onchange = renderPanels;
    await renderPanels();
  }
});


// ---------------------------------------------------------------- 帮助页
// 操作指南是格式固定的纯文本：==== 包章节、--- 包小节、数字开头是步骤、
// "- " 是列表、Q:/A: 是排障问答、"术语 + 两个以上空格 + 说明" 是术语表。
// 这里先解析成结构化块，再渲染成语义化 HTML（步骤 / 列表 / 表格 / 代码 / 问答）。

const HELP_SEP_RE = /^={5,}\s*$/;
const HELP_SUB_RE = /^-{2,}\s*(.+?)\s*-{2,}$/;
const HELP_STEP_RE = /^(\d+[a-zA-Z]?)[.\u3001)]\s+(.*)$/;   // 1. / 2b.
const HELP_LETTER_RE = /^([a-zA-Z])[.\u3001)]\s+(.*)$/;     // a. / b)
const HELP_BULLET_RE = /^[-\u2022*\u00b7]\s+(.*)$/;
// 术语可以含一个内部空格（如 "bbox 坐标归一化"），但真正的分隔是 2 个以上空格
const HELP_TERM_RE = /^(\S(?:[^\s]| (?! )){0,23})\s{2,}(\S.*)$/;
// 正文里成对出现的标识符 / 文件名 / 路由，做等宽高亮
const HELP_IC_RE = /\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b|\b[A-Za-z0-9_-]+\.(?:py|exe|txt|json|md|yml|html|css|js)\b|\/[a-z][a-z0-9_]*(?:\/[a-z0-9_-]+)+/g;

function helpIndent(line) {
  return line.length - line.replace(/^ +/, "").length;
}

function helpDedent(lines) {
  const indents = lines.filter(l => l.trim()).map(helpIndent);
  if (!indents.length) return lines.slice();
  const base = Math.min.apply(null, indents);
  return lines.map(l => (l.trim() ? l.slice(Math.min(base, helpIndent(l))) : ""));
}

// 中文行不要空格，英文之间补一个；避免断行处出现 "汉字 汉字" 或 "word汉字"
function helpJoin(a, b) {
  if (!a) return b;
  if (!b) return a;
  const left = a[a.length - 1];
  const right = b[0];
  // \u4e2d\u6587/\u5168\u89d2\u6807\u70b9\u4e0d\u52a0\u7a7a\u683c\uff1b\u4e24\u8fb9\u90fd\u662f\u897f\u6587\u624d\u8865\u4e00\u4e2a\u7a7a\u683c\uff08"OUTPUT FORMAT" + "\u6bcf\u6b21..." \u8fd9\u79cd\u4e5f\u8981\u8865\uff09
  if (/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(left)) return a + b;
  if (/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(right)) {
    return /[A-Za-z0-9]$/.test(left) ? a + " " + b : a + b;
  }
  return a + " " + b;
}

function helpJoinAll(lines) {
  return lines.reduce((acc, l) => helpJoin(acc, String(l).trim()), "");
}

// 行内标识符用 span 而不是 code：code 沿用等宽不换行，窄屏下会把行撞幅
function helpInline(text) {
  return esc(text).replace(HELP_IC_RE, m => `<span class="help-ic">${m}</span>`);
}

// ---------------- 解析 ----------------

function helpCollectCode(src, i) {
  let depth = 0;
  const out = [];
  for (let j = i; j < src.length; j++) {
    const line = src[j].replace(/\s+$/, "");
    out.push(line);
    for (const ch of line) {
      if (ch === "{" || ch === "[") depth++;
      else if (ch === "}" || ch === "]") depth--;
    }
    if (depth <= 0 && j > i) return { text: out.join("\n"), next: j + 1 };
    if (depth <= 0 && j === i) return null;
  }
  return out.length ? { text: out.join("\n"), next: src.length } : null;
}

function helpCollectQA(src, i) {
  const indent = helpIndent(src[i]);
  const q = [src[i].trim().replace(/^Q[:：]\s*/, "")];
  let j = i + 1;
  while (j < src.length && src[j].trim() && helpIndent(src[j]) > indent) {
    q.push(src[j].trim());
    j++;
  }
  let k = j;
  while (k < src.length && !src[k].trim()) k++;
  if (k >= src.length || !/^A[:：]/.test(src[k].trim())) return null;
  const aIndent = helpIndent(src[k]);
  const a = [src[k].trim().replace(/^A[:：]\s*/, "")];
  j = k + 1;
  while (j < src.length && src[j].trim() && helpIndent(src[j]) > aIndent) {
    a.push(src[j].trim());
    j++;
  }
  return { block: { type: "qa", q: helpJoinAll(q), a: helpJoinAll(a) }, next: j };
}

// 步骤：数字/字母开头 + 更深缩进的续行（含嵌套的小节、列表、子步骤）
function helpCollectStep(src, i, label, title) {
  const indent = helpIndent(src[i]);
  const body = [];
  let j = i + 1;
  while (j < src.length) {
    if (!src[j].trim()) {
      let k = j;
      while (k < src.length && !src[k].trim()) k++;
      if (k >= src.length || helpIndent(src[k]) <= indent) break;
      body.push("");
      j++;
      continue;
    }
    if (helpIndent(src[j]) <= indent) break;
    body.push(src[j]);
    j++;
  }
  return {
    block: { type: "step", label, title, blocks: parseHelpBody(body, "") },
    next: j,
  };
}

function helpCollectBullets(src, i) {
  const indent = helpIndent(src[i]);
  const items = [];
  let j = i;
  while (j < src.length && src[j].trim()) {
    const raw = src[j];
    const t = raw.trim();
    const ind = helpIndent(raw);
    const bm = HELP_BULLET_RE.exec(t);
    if (bm && ind <= indent + 1) {
      items.push(bm[1]);
      j++;
      continue;
    }
    if (ind > indent && items.length) {
      items[items.length - 1] = helpJoin(items[items.length - 1], t);
      j++;
      continue;
    }
    break;
  }
  return { blocks: [{ type: "bullets", items }], next: j };
}

// ---------------- 术语表（按原始缩进识别，说明行里的 "- " 子项也归到该词条下）----------------

function helpTermRow(line) {
  const t = String(line).replace(/\s+$/, "");
  if (!t || /^\s/.test(t)) return null;                    // 只认顶格行
  if (HELP_STEP_RE.test(t) || HELP_LETTER_RE.test(t) ||
      HELP_BULLET_RE.test(t) || HELP_SUB_RE.test(t)) return null;
  const m = HELP_TERM_RE.exec(t);
  if (!m) return null;
  if (/[\u3002\uff0c\u3001\uff1b\uff1a\uff01\uff1f"\u201c\u201d]/.test(m[1])) return null;
  return { term: m[1], def: [m[2]] };
}

// 与术语混排的少量词条只隔一个空格（如 "output_format 输出格式有问题。"），
// 只要上下文已经是术语表，就按同样的规则收进来。
function helpLooseTermRow(line) {
  const t = String(line).replace(/\s+$/, "");
  if (!t || /^\s/.test(t)) return null;
  const m = /^([A-Za-z_][A-Za-z0-9_]*)\s+(\S.*)$/.exec(t);
  if (!m) return null;
  return { term: m[1], def: [m[2]] };
}

// 找出一段连续的术语表区域，返回 { rows, end }；不是术语表则返回 null。
function helpCollectTerms(src, i) {
  const rows = [];
  let j = i;
  while (j < src.length) {
    if (!src[j].trim()) {
      let k = j;
      while (k < src.length && !src[k].trim()) k++;
      if (k >= src.length) break;
      // 空行之后必须仍是顶格的词条，否则术语表到此为止
      if (!helpTermRow(src[k]) && !(rows.length && helpLooseTermRow(src[k]))) break;
      j = k;
      continue;
    }
    const row = helpTermRow(src[j]) || (rows.length ? helpLooseTermRow(src[j]) : null);
    if (!row) break;
    j++;
    // 该词条的说明：后续更深缩进的行（含 "- " 子项）
    while (j < src.length && src[j].trim() && helpIndent(src[j]) > 0) {
      row.def.push(src[j].trim());
      j++;
    }
    rows.push(row);
  }
  return rows.length ? { rows, end: j } : null;
}

// 不含术语表识别的基础分块（供术语表前后的片段复用）
function parseHelpChunks(src) {
  const blocks = [];
  const n = src.length;
  let i = 0;
  while (i < n) {
    const raw = src[i];
    if (!raw.trim()) { i++; continue; }
    const t = raw.trim();
    let m;
    if ((m = HELP_SUB_RE.exec(t))) { blocks.push({ type: "sub", text: m[1] }); i++; continue; }
    if (/^[{\[]\s*$/.test(t)) {
      const code = helpCollectCode(src, i);
      if (code) { blocks.push({ type: "code", text: code.text }); i = code.next; continue; }
    }
    if (/^[QA][:：]/.test(t)) {
      const qa = helpCollectQA(src, i);
      if (qa) { blocks.push(qa.block); i = qa.next; continue; }
    }
    if ((m = HELP_STEP_RE.exec(t))) {
      const r = helpCollectStep(src, i, m[1], m[2]);
      blocks.push(r.block); i = r.next; continue;
    }
    if ((m = HELP_LETTER_RE.exec(t))) {
      const r = helpCollectStep(src, i, m[1], m[2]);
      r.block.type = "step";
      r.block.label = m[1];
      blocks.push(r.block); i = r.next; continue;
    }
    if (HELP_BULLET_RE.test(t)) {
      const r = helpCollectBullets(src, i);
      blocks.push.apply(blocks, r.blocks); i = r.next; continue;
    }
    // 普通段落：连续同缩进的文本合并成一段
    const para = [t];
    i++;
    while (i < n && src[i].trim()) {
      const nt = src[i].trim();
      if (HELP_SUB_RE.test(nt) || HELP_STEP_RE.test(nt) || HELP_LETTER_RE.test(nt) ||
          HELP_BULLET_RE.test(nt) || /^[QA][:：]/.test(nt) || /^[{\[]\s*$/.test(nt)) break;
      para.push(nt);
      i++;
    }
    blocks.push({ type: "para", lines: para });
  }
  return blocks;
}

// 顶层：先按缩进识别术语表区域，其余片段再走常规分块
function parseHelpBody(lines, title) {
  const src = helpDedent(lines || []);
  const out = [];
  let i = 0;
  while (i < src.length) {
    while (i < src.length && !src[i].trim()) i++;
    if (i >= src.length) break;
    const terms = helpCollectTerms(src, i);
    if (terms) {
      out.push({ type: "glossary", rows: terms.rows });
      i = terms.end;
      continue;
    }
    // 常规片段：截到下一个术语表起点为止
    let j = i;
    while (j < src.length) {
      if (!src[j].trim()) { j++; continue; }
      if (j > i && helpCollectTerms(src, j)) break;
      j++;
    }
    out.push.apply(out, parseHelpChunks(src.slice(i, j)));
    i = j;
  }
  return out;
}

function parseHelpText(text) {
  const lines = String(text).split(/\r?\n/);
  const chunks = [];
  let cur = { title: "", lines: [] };
  for (let i = 0; i < lines.length; i++) {
    if (HELP_SEP_RE.test(lines[i]) && i + 2 < lines.length && lines[i + 1].trim() &&
        HELP_SEP_RE.test(lines[i + 2])) {
      chunks.push(cur);
      cur = { title: lines[i + 1].trim(), lines: [] };
      i += 2;
      continue;
    }
    if (HELP_SEP_RE.test(lines[i])) continue;
    cur.lines.push(lines[i]);
  }
  chunks.push(cur);

  const trimBlank = (ls) => {
    let a = 0;
    let b = ls.length;
    while (a < b && !ls[a].trim()) a++;
    while (b > a && !ls[b - 1].trim()) b--;
    return ls.slice(a, b);
  };

  let intro = [];
  const sections = [];
  chunks.forEach((chunk) => {
    const body = trimBlank(chunk.lines);
    if (!chunk.title) {
      if (body.length) intro = intro.concat(body);
      return;
    }
    // 原文自带的「目录」整块由左侧目录替代，不再重复渲染在正文里
    if (chunk.title === "目录") return;
    if (!body.length) return;
    sections.push({
      title: chunk.title,
      text: body.join("\n"),
      blocks: parseHelpBody(body, chunk.title),
    });
  });
  sections.forEach((s, i) => { s.id = "help-sec-" + (i + 1); });
  const introLines = trimBlank(intro);
  return { intro: introLines.join("\n"), introBlocks: parseHelpBody(introLines, ""), sections };
}

// ---------------- 渲染 ----------------

// JSON 片段按 token 着色：字符串分键/值，数字、布尔、null 各自上色
function helpCodeHtml(text) {
  return String(text).split("\n").map((line) => {
    let out = "";
    let i = 0;
    while (i < line.length) {
      const ch = line[i];
      if (ch === "\"") {
        let j = i + 1;
        while (j < line.length) {
          if (line[j] === "\\") { j += 2; continue; }
          if (line[j] === "\"") { j++; break; }
          j++;
        }
        const lit = line.slice(i, j);
        const isKey = /^\s*:/.test(line.slice(j));
        out += `<span class="${isKey ? "hc-k" : "hc-s"}">${esc(lit)}</span>`;
        i = j;
        continue;
      }
      const prevOk = i === 0 || /[\s:,[]/.test(line[i - 1]);
      if (prevOk && (ch === "-" || (ch >= "0" && ch <= "9"))) {
        const m = /^-?\d+(?:\.\d+)?/.exec(line.slice(i));
        if (m) { out += `<span class="hc-n">${m[0]}</span>`; i += m[0].length; continue; }
      }
      if (prevOk) {
        const w = /^(true|false|null)\b/.exec(line.slice(i));
        if (w) { out += `<span class="hc-b">${w[0]}</span>`; i += w[0].length; continue; }
      }
      out += esc(ch);
      i++;
    }
    return out;
  }).join("\n");
}

// 一段文本（可含 "- " 列表行）→ 段落 + 列表
function helpMiniHtml(lines) {
  const out = [];
  let buf = [];
  let ul = null;
  const flush = () => {
    if (buf.length) {
      out.push(`<p class="help-p">${helpInline(helpJoinAll(buf))}</p>`);
      buf = [];
    }
  };
  const closeUl = () => {
    if (ul) {
      out.push(`<ul class="help-ul">${ul.map(x => `<li>${helpInline(x)}</li>`).join("")}</ul>`);
      ul = null;
    }
  };
  lines.forEach((ln) => {
    const t = String(ln).trim();
    if (!t) { flush(); closeUl(); return; }
    const bm = HELP_BULLET_RE.exec(t);
    if (bm) { flush(); if (!ul) ul = []; ul.push(bm[1]); return; }
    if (ul) closeUl();
    buf.push(t);
  });
  flush();
  closeUl();
  return out.join("");
}

function helpBlocksHtml(blocks) {
  const out = [];
  let k = 0;
  while (k < blocks.length) {
    const b = blocks[k];
    if (b.type === "sub") {
      out.push(`<h4 class="help-sub">${helpInline(b.text)}</h4>`);
      k++;
      continue;
    }
    if (b.type === "code") {
      out.push(`<pre class="help-code"><code>${helpCodeHtml(b.text)}</code></pre>`);
      k++;
      continue;
    }
    if (b.type === "qa") {
      out.push(`<div class="help-faq">
        <div class="help-q"><span class="help-tag">Q</span>${helpInline(b.q)}</div>
        <div class="help-row"><span class="help-tag a">A</span><div class="help-a">${helpMiniHtml([b.a])}</div></div>
      </div>`);
      k++;
      continue;
    }
    if (b.type === "step") {
      const items = [];
      while (k < blocks.length && blocks[k].type === "step") items.push(blocks[k++]);
      out.push(`<ol class="help-steps">` + items.map(s =>
        `<li class="help-step"><span class="help-step-n">${esc(s.label)}</span>` +
        `<div class="help-step-b"><div class="help-step-t">${helpInline(s.title)}</div>` +
        `${helpBlocksHtml(s.blocks)}</div></li>`).join("") + `</ol>`);
      continue;
    }
    if (b.type === "bullets") {
      const items = [];
      while (k < blocks.length && blocks[k].type === "bullets") items.push.apply(items, blocks[k++].items);
      out.push(`<ul class="help-ul">${items.map(x => `<li>${helpInline(x)}</li>`).join("")}</ul>`);
      continue;
    }
    if (b.type === "glossary") {
      out.push(`<div class="help-tablewrap"><table class="help-table">
        <thead><tr><th scope="col">术语</th><th scope="col">说明</th></tr></thead><tbody>` +
        b.rows.map(r => `<tr><th scope="row" class="help-term">${helpInline(r.term)}</th>` +
          `<td>${helpMiniHtml(r.def)}</td></tr>`).join("") +
        `</tbody></table></div>`);
      k++;
      continue;
    }
    if (b.type === "para") {
      out.push(helpMiniHtml(b.lines));
      k++;
      continue;
    }
    k++;
  }
  return out.join("");
}

// 兼容旧调用：保持原有的串联输出行为
function renderHelpText(text) {
  const parsed = parseHelpText(text);
  return helpBlocksHtml(parsed.introBlocks) +
    parsed.sections.map(s => `<h3 class="help-h">${esc(s.title)}</h3>${helpBlocksHtml(s.blocks)}`).join("");
}

function renderHelpPage(parsed) {
  const links = parsed.sections.map(s =>
    `<a href="#" class="help-toc-link" data-target="${s.id}">${esc(s.title)}</a>`).join("");
  const body = (parsed.introBlocks.length
      ? `<div class="help-lede">${helpBlocksHtml(parsed.introBlocks)}</div>` : "") +
    parsed.sections.map(s =>
      `<section class="help-sec" id="${s.id}"><h3 class="help-h">${esc(s.title)}</h3>` +
      `${helpBlocksHtml(s.blocks)}</section>`).join("");
  return {
    toc: `<aside class="card help-toc" aria-label="章节目录">
      <h3>目录</h3>
      <nav class="help-toc-nav">${links}</nav>
    </aside>`,
    body: `<div class="card help-body">${body}</div>`,
  };
}


// 目录固定不动、正文单独滚动：滚动时高亮当前章节，点击目录平滑跳转。
// 注意不能改 location.hash —— 这个 SPA 用 hash 做路由，改它会触发页面重渲染。
function bindHelpToc(root, sections) {
  const links = Array.from(root.querySelectorAll(".help-toc-link"));
  if (!links.length) return;
  const tocEl = root.querySelector(".help-toc");
  const bodyEl = root.querySelector(".help-body");
  const targetOf = (a) => root.querySelector("#" + a.dataset.target);

  // 目录自身可能因窗口矮/窄而内部滚动，高亮项要自己滚回可见区
  const reveal = (a) => {
    if (!tocEl) return;
    const ar = a.getBoundingClientRect();
    const tr = tocEl.getBoundingClientRect();
    if (ar.top < tr.top) tocEl.scrollTop -= tr.top - ar.top + 6;
    else if (ar.bottom > tr.bottom) tocEl.scrollTop += ar.bottom - tr.bottom + 6;
    if (ar.left < tr.left) tocEl.scrollLeft -= tr.left - ar.left + 8;
    else if (ar.right > tr.right) tocEl.scrollLeft += ar.right - tr.right + 8;
  };
  const setActive = (id) => links.forEach((a) => {
    const on = a.dataset.target === id;
    a.classList.toggle("active", on);
    if (on) reveal(a);
  });

  // 顶栏和（窄屏时）横排目录都是 sticky 的：留白要按实测高度算，
  // 否则目标标题会被目录栏盖住。
  const stickyPad = () => {
    const bar = document.querySelector(".topbar");
    let pad = (bar ? bar.getBoundingClientRect().height : 52) + 20;
    // 窄屏单列时目录横排在正文上方且常驻，要额外让出它的高度
    if (tocEl && window.matchMedia("(max-width: 860px)").matches) {
      pad += tocEl.getBoundingClientRect().height;
    }
    return pad;
  };
  const scrollToSection = (el) => {
    const top = window.scrollY + el.getBoundingClientRect().top - stickyPad();
    const max = document.documentElement.scrollHeight - window.innerHeight;
    window.scrollTo({ top: Math.max(0, Math.min(top, max)), behavior: "smooth" });
  };
  const jump = (a) => {
    const el = targetOf(a);
    if (!el) return;
    setActive(a.dataset.target);
    scrollToSection(el);
    a.blur();
  };
  const onClick = (e) => {
    const a = e.target.closest(".help-toc-link");
    if (!a) return;
    e.preventDefault();
    jump(a);
  };
  root.addEventListener("click", onClick);
  onPageLeave(() => root.removeEventListener("click", onClick));

  // 滚动高亮：取最后一个已经滚过顶部的章节
  let ticking = false;
  const sync = () => {
    ticking = false;
    // 判定线与跳转留白保持一致：否则窄屏下目标刚进入可视区时高亮不跟随
    const line = stickyPad() + 12;
    let current = sections[0] && sections[0].id;
    sections.forEach((s) => {
      const el = root.querySelector("#" + s.id);
      if (el && el.getBoundingClientRect().top <= line) current = s.id;
    });
    if (current) setActive(current);
  };
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(sync);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onPageLeave(() => window.removeEventListener("scroll", onScroll));
  sync();
}

route("help", async () => {
  $("#app").innerHTML = `
  <div class="page-title">帮助与操作指南</div>
  <div class="card">
    <div class="row u-ai-c">
      <div class="muted u-f2">完整操作指南如下。想快速回顾核心流程，可以重新观看新手引导。</div>
      <button class="btn small primary" id="help-guide">重新观看新手引导</button>
    </div>
  </div>
  <div id="help-layout" class="help-layout">${skeleton(6)}</div>
  <p class="muted" id="help-version"></p>`;
  $("#help-guide").onclick = () => startGuide();
  get("/api/version").then((v) => {
    const el = $("#help-version");
    if (!el) return;
    el.textContent =
      `版本 ${v.version}` + (v.build_time ? ` · 构建于 ${v.build_time}` : "") +
      (v.git_commit ? ` · ${v.git_commit}${v.git_dirty ? "+" : ""}` : "");
  }).catch(() => {});
  try {
    const d = await get("/api/help");
    const layout = $("#help-layout");
    // 用户可能在文档加载期间已经切走
    if (!layout) return;
    const parsed = parseHelpText(d.text || "");
    const html = renderHelpPage(parsed);
    layout.innerHTML = html.toc + `<div class="help-main">${html.body}</div>`;
    bindHelpToc(layout, parsed.sections);
  } catch (e) {
    const layout = $("#help-layout");
    if (layout) layout.innerHTML = `<div class="card"><span class="muted">操作指南加载失败：${esc(e.message)}</span></div>`;
  }
});

// ---------------------------------------------------------------- 提示词生成对话
const paiCollapsed = new Set();  // 对话分组折叠状态
route("prompt-ai", async () => {
  const [cfg, profileData, sessionData, dsData] = await Promise.all([
    get("/api/config"), get("/api/prompt-profiles"), get("/api/prompt-ai/sessions"), get("/api/datasets")]);
  const paiNewModelValue = storedSmValue(cfg, PAI_NEW_MODEL_KEY);
  const paiNewProfileName = storedPaiProfileName(profileData.items || []);
  let profiles = profileData.items || [];
  const allSessions = sessionData.items || [];
  // 会话不属于任何项目，但如果某个会话的图片附件来自当前项目的图片集，
  // 它大概率就是为这个项目准备的。项目视图下把它排到前面并加标记，
  // 而不是硬过滤——否则换个项目就看不到自己刚聊过的对话。
  let sessionProjects = {};
  const curProj = currentProject();
  if (curProj) {
    // 只在项目视图下探测附件归属；全部项目视图不需要，别白跑请求。
    try {
      const detail = await Promise.all(allSessions.slice(0, 40).map(s =>
        get(`/api/prompt-ai/sessions/${encodeURIComponent(s.id)}`).catch(() => null)));
      detail.forEach((s) => {
        if (!s) return;
        const projs = new Set();
        (s.attachments || []).forEach(a => {
          if (a && a.dataset) projs.add(refProject(a.dataset));
        });
        sessionProjects[s.id] = projs;
      });
    } catch (e) {}
  }
  const sessionMatches = (s) => !curProj ||
    (sessionProjects[s.id] && sessionProjects[s.id].has(curProj));
  let sessions = allSessions.slice().sort((a, b) => {
    if (!curProj) return 0;
    const ma = sessionMatches(a) ? 0 : 1, mb = sessionMatches(b) ? 0 : 1;
    return ma - mb || String(b.updated || "").localeCompare(String(a.updated || ""));
  });
  const dsItems = dsData.items || [];
  const profileOptions = (selectedName = "") => `<option value="" ${selectedName ? "" : "selected"}>默认模板</option>` +
    profiles.filter(p => p.type === "generator").map(p =>
      `<option value="${esc(p.name)}" ${p.name === selectedName ? "selected" : ""}>${esc(p.name)}${p.builtin ? "（内置）" : ""}</option>`).join("");
  let sid = null;
  let lastAnswer = "";
  let pending = [];  // 已上传待发送的附件

  $("#app").innerHTML = `<div class="pai-page">
  <div class="page-title">提示词生成</div>
  ${sharedScopeBar("对话与生成的提示词属于全站资源；项目只影响附件可选的图片集。")}
  <dialog class="pai-dialog" id="pai-new-dialog">
    <h3>新建对话</h3>
    <div>
      <label class="f" for="pai-profile">生成器模板</label>
      <select id="pai-profile">${profileOptions(paiNewProfileName)}</select>
    </div>
    <div>
      <label class="f" for="pai-model">站点 / 模型</label>
      <select id="pai-model">${smOptionsFromValue(cfg, paiNewModelValue)}</select>
    </div>
      <div class="row u-jc-fe">
      <div class="u-f0"><button class="btn" id="pai-cancel" type="button">取消</button></div>
      <div class="u-f0"><button class="btn primary" id="pai-create" type="button">创建并开始</button></div>
    </div>
  </dialog>
  <div class="pai-layout">
    <div class="pai-sidebar">
      <div class="pai-sidebar-head">
        <button class="btn primary u-w-full"  id="pai-new">新建对话</button>
      </div>
      <div class="pai-sidebar-list" id="pai-sessions"></div>
    </div>
    <div class="pai-empty-hint" id="pai-empty">选择左侧会话或点击「新建对话」开始</div>
    <div class="pai-chat-wrap u-hide" id="pai-chat">
      <div class="pai-chat-header">
        <h3 id="pai-title">对话</h3>
        <div class="pai-session-meta">
          <span class="tag blue" id="pai-profile-tag" title="会话创建时的模板快照">模板：默认模板</span>
          <span class="muted u-nowrap">当前对话模型</span>
          <select id="pai-chat-model">${smOptions(cfg)}</select>
        </div>
        <button class="btn small primary" id="pai-save">保存为提示词</button>
      </div>
      <div class="pai-chat-body">
        <div id="pai-msgs" class="chat-box"></div>
        <div class="pai-input-bar">
          <div id="pai-pending" class="att-chips"></div>
          <textarea id="pai-input" rows="3" placeholder="描述要识别的任务、异常定义、样例和边界；可附图说明…" aria-label="消息内容"></textarea>
          <div class="row u-mt-8 u-ai-c">
            <div class="u-f0"><button class="btn" id="pai-upload">上传图片</button><input class="u-hide" type="file" id="pai-file" accept="image/*" multiple></div>
            <div class="u-f0"><button class="btn" id="pai-fromds">从图片集选择</button></div>
            <div class="u-f1"></div>
            <div class="u-f0"><button class="btn primary" id="pai-send">发送</button></div>
          </div>
          <div class="u-hide u-mt-8" id="pai-dspick">
            <div class="row">
              <div><label class="f">图片集</label><select id="pai-ds">${projectDatasets(dsItems).map(d =>
                `<option value="${esc(d.ref || d.name)}">${esc(d.project || "未归档项目")} / ${esc(d.name)}</option>`).join("")}</select></div>
              <div><label class="f">图片</label><select id="pai-ds-images" multiple size="5"></select></div>
              <div class="u-f0"><button class="btn small primary" id="pai-ds-add">添加为附件</button></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>`;

  const renderSidebar = () => {
    const groups = {};
    sessions.forEach(s => { const g = s.group || ""; (groups[g] = groups[g] || []).push(s); });
    const names = Object.keys(groups).sort((a, b) => (a === "" ? 1 : 0) - (b === "" ? 1 : 0) || a.localeCompare(b, "zh"));
    $("#pai-sessions").innerHTML = names.map(g => {
      const collapsed = paiCollapsed.has(g || "\0");
      return `<div class="p-group">
        <div class="p-group-head" data-g="${esc(g)}"><span class="p-group-arrow">${collapsed ? "▸" : "▾"}</span><span class="u-f1">${g ? esc(g) : "未分组"}</span><span class="tag">${groups[g].length}</span></div>
        <div class="p-group-items" style="display:${collapsed ? "none" : ""}">
          ${groups[g].map(s => `<div class="sess-item ${s.id === sid ? "active" : ""}" data-sid="${s.id}">
            <div class="u-f1 u-minw-0">
              <div class="sess-title">${esc(s.title)}${state._paiGenerating === s.id ? ' <span class="tag green u-fs-xs">生成中</span>' : ''}${currentProject() && sessionMatches(s) ? ' <span class="tag blue u-fs-xs">当前项目</span>' : ''}</div>
              <div class="muted u-fs-xs">${esc(s.profile_name || "默认模板")} · ${s.message_count} 条 · ${esc((s.updated || "").slice(5, 16))}</div>
            </div>
            <button class="sess-op" data-act="rename" title="重命名">✎</button>
            <button class="sess-op" data-act="group" title="移动分组">▤</button>
            <button class="sess-op" data-act="del" title="删除">×</button>
          </div>`).join("")}
        </div></div>`;
    }).join("") || emptyState("还没有历史对话", "新建对话", null, "pai-new");
    $$("#pai-sessions .p-group-head").forEach(h => h.onclick = () => {
      const key = h.dataset.g || "\0";
      if (paiCollapsed.has(key)) paiCollapsed.delete(key); else paiCollapsed.add(key);
      renderSidebar();
    });
    $$("#pai-sessions .sess-item").forEach(it => {
      it.onclick = () => loadSession(it.dataset.sid);
      $$(".sess-op", it).forEach(b => b.onclick = async (e) => {
        e.stopPropagation();
        const s = sessions.find(x => x.id === it.dataset.sid);
        if (!s) return;
        try {
          if (b.dataset.act === "rename") {
            const t = await promptDlg("重命名对话", s.title, { label: "对话名称" });
            if (t && t.trim()) await put(`/api/prompt-ai/sessions/${s.id}`, { title: t.trim() });
          } else if (b.dataset.act === "group") {
            const g = await promptDlg("设置分组", s.group || "", { label: "分组名称（留空为未分组）" });
            if (g !== null) await put(`/api/prompt-ai/sessions/${s.id}`, { group: g.trim() });
          } else if (b.dataset.act === "del") {
            if (!(await confirmDlg(`确定删除对话「${s.title}」？其中的图片附件会一并删除。`, { title: "删除对话" }))) return;
            await del(`/api/prompt-ai/sessions/${s.id}`);
            try { localStorage.removeItem(paiChatModelKey(s.id)); } catch (e) {}
            if (sid === s.id) {
              sid = null;
              try { localStorage.removeItem(PAI_LAST_SESSION_KEY); } catch (e) {}
              showChatPane(false);
           }
          }
          await refreshSessions();
        } catch (err) { toast(err.message, false); }
      });
    });
  };
  // 空态提示与对话面板共用右侧同一格：必须互斥显示。
  // 只显示 #pai-chat 而不隐藏 #pai-empty 时，网格自动排布会把对话挤到
  // 第二行第一列（左侧栏下方，300px 宽），看起来像「先在左边再跳右边」。
  const showChatPane = (show) => {
    setShown($("#pai-chat"), show);
    const empty = $("#pai-empty");
    if (empty) setShown(empty, !show);
  };
  const refreshSessions = async () => {
    sessions = (await get("/api/prompt-ai/sessions")).items || [];
    renderSidebar();
  };

  const render = (s) => {
    $("#pai-title").textContent = s.title || "对话";
    const box = $("#pai-msgs");
    box.innerHTML = (s.messages || []).map(m => `
      <div class="chat-msg ${m.role === "user" ? "chat-user" : "chat-ai"}">
        <div class="chat-bubble">
          ${(m.images || []).length ? `<div class="chat-imgs">${m.images.map(n =>
            `<a href="/api/file/prompt-session/${s.id}/${encodeURIComponent(n)}" target="_blank"><img src="/api/file/prompt-session/${s.id}/${encodeURIComponent(n)}" alt=""></a>`).join("")}</div>` : ""}
          <pre>${esc(m.content)}</pre>
        </div>
      </div>`).join("") || '<div class="muted">描述你的识别任务开始对话；首条消息会自动作为对话名称。</div>';
    box.scrollTop = box.scrollHeight;
  };
  const renderSessionMeta = (s) => {
    const name = s.profile_name || "";
    const exists = !name || profiles.some(p => p.name === name);
    const label = name ? (exists ? name : `${name}（已删除）`) : "默认模板";
    const tag = $("#pai-profile-tag");
    if (tag) {
      tag.textContent = `模板：${label}`;
      tag.title = s.system_prompt || "会话创建时的模板快照";
    }
  };
  const renderPending = () => {
    $("#pai-pending").innerHTML = pending.map(a =>
      `<span class="att-chip"><img src="/api/file/prompt-session/${sid}/${encodeURIComponent(a.file || a.name)}" alt="">${esc(a.name)}<button data-aid="${a.id}" title="移除">×</button></span>`).join("");
    $$("#pai-pending button").forEach(b => b.onclick = () => {
      pending = pending.filter(x => x.id !== b.dataset.aid);
      renderPending();
    });
  };
  // 轮询等待生成完成（需在 loadSession 之前定义，避免 const 提升问题）
  const pollChatResult = async (sessionId) => {
    if (!sessionId) return;
    try {
      const st = await get(`/api/prompt-ai/sessions/${sessionId}/chat-status`);
      if (st.status === "generating") {
        setTimeout(() => pollChatResult(sessionId), 2000);
        return;
      }
      state._paiGenerating = null;
      const s = await get(`/api/prompt-ai/sessions/${sessionId}`);
      if ($("#pai-msgs") && sid === sessionId) {
        lastAnswer = [...(s.messages || [])].reverse().find(m => m.role === "assistant")?.content || "";
        render(s); renderPending();
        const btn = $("#pai-send"); if (btn) { btn.disabled = false; btn.textContent = "发送"; }
        const ld = $("#pai-loading"); if (ld) ld.remove();
      }
      await refreshSessions();
      if (st.status && st.status !== "idle" && st.status !== "generating") {
        if ($("#pai-msgs") && sid === sessionId) {
          const btn = $("#pai-send"); if (btn) { btn.disabled = false; btn.textContent = "发送"; }
          const ld = $("#pai-loading"); if (ld) ld.remove();
        }
      }
    } catch (e) {
      state._paiGenerating = null;
      if ($("#pai-msgs") && sid === sessionId) {
        const btn = $("#pai-send"); if (btn) { btn.disabled = false; btn.textContent = "发送"; }
        const ld = $("#pai-loading"); if (ld) ld.remove();
      }
    }
  };
  const loadSession = async (id) => {
    try {
      const s = await get(`/api/prompt-ai/sessions/${id}`);
      sid = s.id;
      saveSmValue(PAI_LAST_SESSION_KEY, sid);
      pending = [];
      lastAnswer = [...(s.messages || [])].reverse().find(m => m.role === "assistant")?.content || "";
      showChatPane(true);
      const chatModelValue = paiChatModelValue(cfg, s, sid);
      $("#pai-chat-model").innerHTML = smOptionsFromValue(cfg, chatModelValue);
      renderSessionMeta(s);
      render(s); renderPending(); renderSidebar();
      // 检查是否在生成中，恢复 loading 状态
      try {
        const st = await get(`/api/prompt-ai/sessions/${id}/chat-status`);
        state._paiGenerating = st.status === "generating" ? id : null;
        if (st.status === "generating") {
          state._paiGenerating = id;
          $("#pai-send").disabled = true;
          $("#pai-send").textContent = "生成中…";
          const box = $("#pai-msgs");
          if (box && !$("#pai-loading")) {
            const loadingDiv = document.createElement("div");
            loadingDiv.className = "chat-msg chat-ai";
            loadingDiv.id = "pai-loading";
            loadingDiv.innerHTML = `<div class="chat-bubble"><pre class="u-c-muted">正在生成，请稍候…（可切换到其他页面，生成会在后台继续）</pre></div>`;
            box.appendChild(loadingDiv);
            box.scrollTop = box.scrollHeight;
          }
          pollChatResult(id);
        }
      } catch (e) {}
    } catch (e) { toast(e.message, false); }
  };

  $("#pai-profile").onchange = () => saveSmValue(PAI_NEW_PROFILE_KEY, $("#pai-profile").value);
  $("#pai-model").onchange = () => saveSmValue(PAI_NEW_MODEL_KEY, $("#pai-model").value);
  $("#pai-chat-model").onchange = () => {
    if (sid) saveSmValue(paiChatModelKey(sid), $("#pai-chat-model").value);
  };
  renderSidebar();

  $("#pai-new").onclick = () => {
    const dialog = $("#pai-new-dialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };
  $("#pai-cancel").onclick = () => {
    const dialog = $("#pai-new-dialog");
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };
  $("#pai-create").onclick = async () => {
    try {
      const profileName = $("#pai-profile").value;
      const sm = smParse($("#pai-model").value);
      saveSmValue(PAI_NEW_PROFILE_KEY, profileName);
      saveSmValue(PAI_NEW_MODEL_KEY, $("#pai-model").value);
      const s = await post("/api/prompt-ai/sessions", { model: sm.model, site: sm.site, profile_name: profileName });
      sid = s.id; pending = []; lastAnswer = "";
      saveSmValue(PAI_LAST_SESSION_KEY, sid);
      const chatModelValue = paiChatModelValue(cfg, s, sid);
      saveSmValue(paiChatModelKey(sid), chatModelValue);
      showChatPane(true);
      $("#pai-chat-model").innerHTML = smOptionsFromValue(cfg, chatModelValue);
      renderSessionMeta(s);
      render(s); renderPending();
      await refreshSessions();
      const dialog = $("#pai-new-dialog");
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    } catch (e) { toast(e.message, false); }
  };

  const lastSessionId = (() => {
    try { return localStorage.getItem(PAI_LAST_SESSION_KEY) || ""; } catch (e) { return ""; }
  })();
  if (lastSessionId && sessions.some(s => s.id === lastSessionId)) {
    await loadSession(lastSessionId);
  }

  $("#pai-send").onclick = async () => {
    if (!sid) return toast("请先新建或选择对话", false);
    const input = $("#pai-input");
    if (!input.value.trim() && !pending.length) return;
    if (pending.length) {
      const modelVal = $("#pai-chat-model").value || "";
      const modelLower = modelVal.toLowerCase();
      const visionKeywords = ["vl", "vision", "4o", "gemini", "multimodal", "qwen-vl", "qwen2-vl", "qwen3-vl", "llava", "internvl", "minicpm", "cogvlm", "glm-4v"];
      const likelyVision = visionKeywords.some(k => modelLower.includes(k));
      if (!likelyVision && !(await confirmDlg(`当前模型 "${modelVal}" 可能不支持图片输入，发送带图片的消息可能报错。\n\n确定继续发送吗？（建议切换到名称含 VL/Vision/4o 等的多模态模型）`, { title: "模型可能不支持图片", danger: false, okText: "继续发送" }))) return;
    }
    $("#pai-send").disabled = true;
    $("#pai-send").textContent = "生成中…";
    try {
      const sm = smParse($("#pai-chat-model").value);
      const r = await post(`/api/prompt-ai/sessions/${sid}/messages`, { message: input.value, model: sm.model, site: sm.site, attachment_ids: pending.map(a => a.id) });
      input.value = ""; pending = [];
      // 标记此 session 正在生成
      state._paiGenerating = sid;
      // 显示用户消息和 loading
      render(r.session); renderPending();
      const box = $("#pai-msgs");
      const loadingDiv = document.createElement("div");
      loadingDiv.className = "chat-msg chat-ai";
      loadingDiv.id = "pai-loading";
      loadingDiv.innerHTML = `<div class="chat-bubble"><pre class="u-c-muted">正在生成，请稍候…（可切换到其他页面，生成会在后台继续）</pre></div>`;
      box.appendChild(loadingDiv);
      box.scrollTop = box.scrollHeight;
      await refreshSessions();
      // 开始轮询
      pollChatResult(sid);
    } catch (e) {
      toast(e.message, false);
      state._paiGenerating = null;
      $("#pai-send").textContent = "发送";
      $("#pai-send").disabled = false;
    }
  };
  $("#pai-upload").onclick = () => {
    if (!sid) return toast("请先新建或选择对话", false);
    $("#pai-file").click();
  };
  $("#pai-file").onchange = async (e) => {
    const inp = e.target;
    if (!inp.files.length || !sid) { inp.value = ""; return; }
    const fd = new FormData();
    for (const f of inp.files) fd.append("files", f);
    try {
      const r = await api(`/api/prompt-ai/sessions/${sid}/attachments`, { method: "POST", body: fd });
      pending.push(...(r.items || []));
      renderPending();
    } catch (err) { toast(err.message, false); }
    inp.value = "";
  };
  const loadDsImages = async () => {
    const sel = $("#pai-ds-images");
    if (!$("#pai-ds").value) return;
    try {
      const d = await get(`/api/datasets/${encodeURIComponent($("#pai-ds").value)}/images`);
      sel.innerHTML = d.items.map(i => `<option value="${esc(i.rel)}">${esc(i.rel)}</option>`).join("") || `<option disabled>图片集为空</option>`;
    } catch (e) { sel.innerHTML = `<option disabled>${esc(e.message)}</option>`; }
  };
  $("#pai-fromds").onclick = () => {
    if (!sid) return toast("请先新建或选择对话", false);
    const box = $("#pai-dspick");
    setShown(box, box.classList.contains("u-hide"));
    if (!box.classList.contains("u-hide") && !$("#pai-ds-images").options.length) loadDsImages();
  };
  $("#pai-ds").onchange = loadDsImages;
  $("#pai-ds-add").onclick = async () => {
    const rels = $$("#pai-ds-images option:checked").map(o => o.value).slice(0, 8);
    if (!rels.length) return toast("请选择图片", false);
    for (const rel of rels) {
      try {
        const att = await post(`/api/prompt-ai/sessions/${sid}/attachments/from-dataset`, { dataset: $("#pai-ds").value, rel });
        pending.push(att);
      } catch (e) { toast(e.message, false); }
    }
    renderPending();
  };
  $("#pai-save").onclick = async () => {
    if (!lastAnswer.trim()) return toast("请先生成一版提示词", false);
    const name = await promptDlg("保存提示词", "", { label: "提示词名称" });
    if (!name) return;
    try { await post(`/api/prompt-ai/sessions/${sid}/save`, { name, content: lastAnswer, note: "提示词生成对话保存" }); toast("已保存到提示词库"); }
    catch (e) { toast(e.message, false); }
  };
});

// ---------------------------------------------------------------- 字段提取
route("extract", async () => {
  const runs = await get("/api/runs");
  // 字段提取是"从某次运行里捞结果"，运行本身就属于某项目：
  // 不按当前项目收口，下拉里会混进其他项目的运行，选错了还很难发现。
  const done = projectRuns(runs.items).filter(r => r.done + r.failed > 0);
  $("#app").innerHTML = `
  <div class="page-title">字段提取归档</div>
  ${currentProject() ? projectScopeBar("只列出当前项目的已完成运行。") : ""}
  <div class="card">
    <h3>提取设置</h3>
    <div class="row">
      <div><label class="f">选择运行</label><select id="e-run">${done.map(r =>
        `<option value="${r.id}">${esc(r.id)}</option>`).join("")
        || `<option value="">当前项目下没有已完成运行</option>`}</select></div>
      <div><label class="f">模式</label><select id="e-mode">
        <option value="filter">条件筛选 → 一个文件夹</option>
        <option value="group">按字段值分组 → 每个值一个文件夹</option></select></div>
      <div><label class="f">输出文件夹名</label><input type="text" id="e-out" placeholder="如：异常结果"></div>
    </div>
    <div id="e-condbox">
      <label class="f">条件组（字段来自运行结果）</label>
      <div id="e-conds"></div>
      <div class="row u-mt-6">
        <button class="btn small" id="e-addcond">+ 添加条件</button>
        <div class="u-f0"  id="e-logicbox">
          <label class="f u-m0">条件关系</label>
          <select class="u-w-90" id="e-logic"><option value="and">且 AND</option><option value="or">或 OR</option></select>
        </div>
      </div>
    </div>
    <div class="u-hide" id="e-groupbox">
      <label class="f">分组字段（如 overall_status 或 objects[].name）</label>
      <select id="e-groupfield"></select>
    </div>
    <label class="f">复制内容（可多选）</label>
    <div class="checks">
      <label><input type="checkbox" class="e-src" value="json" checked> 结果 JSON</label>
      <label><input type="checkbox" class="e-src" value="annotated"> 推理图</label>
      <label><input type="checkbox" class="e-src" value="image"> 原图</label>
    </div>
    <div class="u-mt-10"><button class="btn primary" id="e-go">执行提取</button></div>
    <div id="e-result"></div>
  </div>`;

  let fields = [];
  async function loadFields() {
    if (!$("#e-run").value) return;
    const d = await get(`/api/extract/fields?run_id=${encodeURIComponent($("#e-run").value)}`);
    fields = d.fields;
    renderConds();
    $("#e-groupfield").innerHTML = fields.map(f => `<option>${esc(f)}</option>`).join("");
  }
  function renderConds() {
    const box = $("#e-conds");
    box.innerHTML = "";
    box.appendChild(condRow());
  }
  function condRow() {
    const div = document.createElement("div");
    div.className = "row";
    div.style.marginTop = "6px";
    div.innerHTML = `
      <div class="u-f2"><select class="e-c-field">${fields.map(f => `<option>${esc(f)}</option>`).join("")}</select></div>
      <div><select class="e-c-mt">
        <option value="exact">精确等于</option><option value="contains">包含</option>
        <option value="regex">正则</option><option value="range">数值区间(如0-3)</option>
        <option value="in_list">在列表中(逗号分隔)</option>
        <option value="not_empty">非空</option><option value="empty">为空</option></select></div>
      <div class="u-f2"><input type="text" class="e-c-val" placeholder="匹配值"></div>
      <div class="u-f0"><button class="btn small danger e-c-del">删除</button></div>`;
    $(".e-c-del", div).onclick = () => { if ($$("#e-conds .row").length > 1) div.remove(); };
    return div;
  }
  $("#e-addcond").onclick = () => $("#e-conds").appendChild(condRow());
  $("#e-run").onchange = loadFields;
  $("#e-mode").onchange = () => {
    const g = $("#e-mode").value === "group";
    setShown($("#e-condbox"), !g);
    setShown($("#e-groupbox"), g);
  };
  await loadFields();

  $("#e-go").onclick = async () => {
    const body = {
      run_id: $("#e-run").value, output_name: $("#e-out").value.trim(),
      mode: $("#e-mode").value, logic: $("#e-logic").value,
      group_field: $("#e-groupfield").value,
      sources: $$(".e-src").filter(c => c.checked).map(c => c.value),
      conditions: $$("#e-conds .row").map(r => ({
        field: $(".e-c-field", r).value, match_type: $(".e-c-mt", r).value,
        value: $(".e-c-val", r).value,
      })),
    };
    if (!body.run_id) return toast("请先选择运行", false);
    if (!body.output_name) return toast("请填写输出文件夹名", false);
    if (!body.sources.length) return toast("请至少选择一种复制内容", false);
    try {
      const r = await post("/api/extract", body);
      $("#e-result").innerHTML = `<div class="msg ok">完成：扫描 ${r.scanned} 条，提取 ${r.matched} 条 →
        <span class="mono">${esc(r.output_dir)}</span>
        ${r.groups ? "<br>" + Object.entries(r.groups).map(([k, v]) => `<span class="tag blue">${esc(k)}: ${v}</span>`).join("") : ""}</div>`;
    } catch (e) { toast(e.message, false); }
  };
});

// ---------------------------------------------------------------- 真值标注（任务列表）
route("truth", async () => {
  const [tsAll, ds, runs, es] = await Promise.all([
    get("/api/truth"), get("/api/datasets"), get("/api/runs"), get("/api/evals")]);
  // 真值任务只认 dataset 里的「项目::图片集」，按当前项目收口
  const ts = { items: (tsAll.items || []).filter(inProject) };
  const evalsOf = (taskId) => (es.items || []).filter(e => e.truth_task === taskId)
    .sort((a, b) => a.prompt_name.localeCompare(b.prompt_name) || a.prompt_version - b.prompt_version);
  const metricOf = (e) => e.kind === "single"
    ? `准确率 ${(e.metrics.accuracy * 100).toFixed(1)}%`
    : `微F1 ${(e.metrics.micro.f1 * 100).toFixed(1)}%`;
  const scoreOf = (e) => e.kind === "single" ? e.metrics.accuracy : e.metrics.micro.f1;
  $("#app").innerHTML = `
  <div class="page-title">真值标注任务</div>
  ${projectScopeBar("标注任务按当前项目收口；切换项目只显示该项目的任务。")}
  <div class="msg info">真值是量化对比提示词效果的基础。审核运行结果时填写的「期望状态/期望框」会自动沉淀到这里；也可以在这里单独标注。手动标注的内容不会被自动沉淀覆盖。</div>
  <div class="card">
    <h3>新建标注任务</h3>
    <div class="row">
      <div><label class="f">任务名称</label><input type="text" id="t-name" placeholder="如：吊车下方站人-真值"></div>
      <div><label class="f">类型</label><select id="t-kind">
        <option value="single">单分类（每张图只属于一个类别）</option>
        <option value="multi">多标签（每张图可属多个类别，适合目标集合）</option></select></div>
      <div><label class="f">标签（逗号分隔）</label><input type="text" id="t-labels" placeholder="如：abnormal,normal"></div>
      <div><label class="f">图片集</label><select id="t-ds">${projectDatasets(ds.items).map(d =>
        `<option value="${esc(d.ref || d.name)}">${esc(d.project || "未归档项目")} / ${esc(d.name)}</option>`).join("")
        || `<option value="">当前项目下没有图片集</option>`}</select></div>
      <div class="u-f0"><button class="btn primary" id="t-create">创建任务</button></div>
    </div>
  </div>
  <div class="grid grid-3">
    ${ts.items.map(t => {
      const taskEvals = evalsOf(t.id);
      const best = taskEvals.length >= 2 ? taskEvals.reduce((a, b) => scoreOf(a) >= scoreOf(b) ? a : b) : null;
      const ss = t.source_stats || { manual: 0, review: 0 };
      return `
    <div class="card">
      <h3><a href="#/truthEdit/${t.id}">${esc(t.name)}</a>
        <span class="tag ${t.kind === "single" ? "blue" : "orange"}">${t.kind === "single" ? "单分类" : "多标签"}</span>
        ${t.auto_sync ? '<span class="tag green">审核自动沉淀</span>' : ""}</h3>
      <div class="muted">${esc(t.dataset)} · 标签：${t.labels.map(esc).join(" / ")}</div>
      <div class="progress u-my-8"><i style="width:${t.progress.percent}%"></i></div>
      <div class="muted">${t.progress.labeled}/${t.progress.total}（${t.progress.percent}%）${ss.manual || ss.review ? ` · 手动 ${ss.manual} · 沉淀 ${ss.review}` : ""}</div>
      <div class="u-mt-8">
        <a class="btn small" href="#/truthEdit/${t.id}">开始标注</a>
        <button class="btn small" data-syncrun="${t.id}">导入审核结果</button>
        <button class="btn small" data-goeval="${t.id}">去评估</button>
        <button class="btn small danger" data-del="${t.id}">删除</button>
      </div>
      ${taskEvals.length ? `<div class="tbl-scroll"><table class="tbl u-mt-10"><thead><tr><th>提示词版本</th><th>效果</th><th>时间</th></tr></thead><tbody>
        ${taskEvals.map(e => `<tr>
          <td>${esc(e.prompt_name)} <span class="tag blue">V${e.prompt_version}</span>${e === best ? ' <span class="tag green">最佳</span>' : ""}</td>
          <td><b>${metricOf(e)}</b><br><span class="muted u-fs-xs">${esc(e.model)}</span></td>
          <td class="muted u-fs-xs">${esc(e.created)}</td></tr>`).join("")}
      </tbody></table></div>` : emptyState("还没有评估记录——标注积累后跑一次量化对比", "去评估", "#/evals")}
    </div>`;
    }).join("") || `<div class="card">${emptyState("还没有真值任务，用上方表单建第一个", "去填写名称", null, "t-name")}</div>`}
  </div>`;
  $("#t-create").onclick = async () => {
    try {
      await post("/api/truth", {
        name: $("#t-name").value.trim(), kind: $("#t-kind").value,
        labels: $("#t-labels").value.split(/[,，]/).map(s => s.trim()).filter(Boolean),
        dataset: $("#t-ds").value,
      });
      toast("已创建"); navigate();
    } catch (e) { toast(e.message, false); }
  };
  $$("[data-del]").forEach(b => b.onclick = async () => {
    if (!(await confirmDlg("确定删除该真值任务及全部标注？", { title: "删除真值任务" }))) return;
    await del(`/api/truth/${b.dataset.del}`); navigate();
  });
  $$("[data-goeval]").forEach(b => b.onclick = () => {
    state._evalPreselect = { task: b.dataset.goeval };
    location.hash = "#/evals";
  });
  $$("[data-syncrun]").forEach(b => b.onclick = () => {
    const task = ts.items.find(x => x.id === b.dataset.syncrun);
    const dsRuns = (runs.items || []).filter(r => r.dataset === task.dataset && (r.done || 0) > 0);
    if (!dsRuns.length) return toast("该图片集还没有已完成的运行，先在运行测试里跑一轮并审核", false);
    const dlg = openDlg(`<h3>从审核结果沉淀真值</h3>
      <div class="muted u-mb-10">把所选运行中人工审核填写的期望状态/期望框批量沉淀到「${esc(task.name)}」。已手动标注的图片不会被覆盖。</div>
      <label class="f">选择运行</label>
      <select class="u-w-full" id="sync-run-sel">${dsRuns.map(r =>
        `<option value="${r.id}">${esc(r.prompt_name)} V${r.prompt_version} · ${esc(r.id)}</option>`).join("")}</select>
      <div class="u-mt-14 u-ta-r"><button class="btn primary" id="sync-run-go">开始沉淀</button></div>`);
    dlg.box.querySelector("#sync-run-go").onclick = async () => {
      try {
        const s = await post(`/api/truth/sync-run/${dlg.box.querySelector("#sync-run-sel").value}`, {});
        dlg.close();
        toast(`沉淀完成：新增 ${s.synced} 张${s.skipped_manual ? `，跳过手动标注 ${s.skipped_manual} 张` : ""}${s.empty ? `，${s.empty} 张无期望内容` : ""}`);
        navigate();
      } catch (e) { toast(e.message, false); }
    };
  });
});

// ---------------------------------------------------------------- 真值标注（标注界面）
route("truthEdit", async (taskId) => {
  if (!taskId) { location.hash = "#/truth"; return; }
  taskId = decodeURIComponent(taskId);
  const t = await get(`/api/truth/${taskId}`);
  adoptProjectOf(t);
  $("#app").innerHTML = `
  <div class="page-title">标注：${esc(t.name)}
    <span class="tag ${t.kind === "single" ? "blue" : "orange"}">${t.kind === "single" ? "单分类" : "多标签"}</span></div>
  <div class="card">
    <div class="row u-ai-c">
      <div class="progress u-f3"><i id="a-prog" style="width:${t.progress.percent}%"></i></div>
      <div class="muted u-f1"  id="a-progtxt">${t.progress.labeled}/${t.progress.total}</div>
      <div class="u-f1">
        <select id="a-filter">
          <option value="all">全部图片</option>
          <option value="unlabeled" selected>未标注</option>
          <option value="labeled">已标注</option>
        </select>
      </div>
      <div class="u-f0"><a class="btn small" href="#/truth">返回</a></div>
    </div>
  </div>
  <div class="annot-layout">
    <div class="annot-img-box"><img id="a-img"></div>
    <div class="card">
      <h3 id="a-name"></h3>
      <div class="muted u-mb-10">快捷键 1-9 选择，←/→ 切换图片${t.kind === "multi" ? "，回车确认并下一张" : ""}</div>
      <div id="a-btns">
        ${t.labels.map((l, i) => `<button class="label-btn" data-l="${esc(l)}">
          <span class="key">${i + 1}</span>${esc(l)}</button>`).join("")}
      </div>
      ${t.kind === "multi" ? `<button class="btn primary u-w-full"  id="a-confirm">确认并下一张 ⏎</button>` : ""}
      <button class="btn u-w-full u-mt-8"  id="a-clear">清除标注</button>
      <div class="row u-mt-10">
        <button class="btn" id="a-prev">← 上一张</button>
        <button class="btn" id="a-next">下一张 →</button>
      </div>
      <div class="muted u-mt-8"  id="a-pos"></div>
    </div>
  </div>`;

  let items = [], idx = 0;
  async function load(keepRel) {
    const d = await get(`/api/truth/${taskId}/images?filter=${$("#a-filter").value}&limit=10000`);
    items = d.items;
    if (keepRel) {
      const i = items.findIndex(x => x.rel === keepRel);
      idx = i >= 0 ? i : Math.min(idx, items.length - 1);
    } else idx = 0;
    render();
    const p = await get(`/api/truth/${taskId}`);
    $("#a-prog").style.width = p.progress.percent + "%";
    $("#a-progtxt").textContent = `${p.progress.labeled}/${p.progress.total}`;
  }
  function render() {
    if (!items.length) {
      $("#a-img").src = ""; $("#a-name").textContent = "没有符合条件的图片";
      $("#a-pos").textContent = ""; return;
    }
    idx = Math.max(0, Math.min(idx, items.length - 1));
    const it = items[idx];
    $("#a-img").src = `/api/file/truth/${taskId}/${enc(it.rel)}`;
    $("#a-name").textContent = it.rel;
    const srcText = it.source === "review" ? " · 审核沉淀" : it.source === "manual" ? " · 手动标注" : "";
    $("#a-pos").textContent = `第 ${idx + 1} / ${items.length} 张 · 当前：${it.labels.join("、") || "未标注"}${srcText}`;
    $$("#a-btns .label-btn").forEach(b =>
      b.classList.toggle("on", it.labels.includes(b.dataset.l)));
  }
  async function setLabels(labels, advance) {
    const it = items[idx];
    if (!it) return;
    try {
      await post(`/api/truth/${taskId}/label`, { rel: it.rel, labels });
      it.labels = labels;
      render();
      if (advance) { idx++; render(); }
      const p = await get(`/api/truth/${taskId}`);
      $("#a-prog").style.width = p.progress.percent + "%";
      $("#a-progtxt").textContent = `${p.progress.labeled}/${p.progress.total}`;
    } catch (e) { toast(e.message, false); }
  }
  $$("#a-btns .label-btn").forEach((b, i) => b.onclick = () => {
    const it = items[idx];
    if (!it) return;
    if (t.kind === "single") {
      setLabels([b.dataset.l], true);
    } else {
      const cur = new Set(it.labels);
      cur.has(b.dataset.l) ? cur.delete(b.dataset.l) : cur.add(b.dataset.l);
      setLabels([...cur], false);
    }
  });
  if (t.kind === "multi") $("#a-confirm").onclick = () => { idx++; render(); };
  $("#a-clear").onclick = () => setLabels([], false);
  $("#a-prev").onclick = () => { idx--; render(); };
  $("#a-next").onclick = () => { idx++; render(); };
  $("#a-filter").onchange = () => load(items[idx] && items[idx].rel);
  document.onkeydown = (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    if (e.key >= "1" && e.key <= "9") {
      const b = $$("#a-btns .label-btn")[Number(e.key) - 1];
      if (b) b.click();
    } else if (e.key === "ArrowLeft") $("#a-prev").click();
    else if (e.key === "ArrowRight") $("#a-next").click();
    else if (e.key === "Enter" && t.kind === "multi") $("#a-confirm").click();
  };
  await load();
});

// ---------------------------------------------------------------- 评估对比
route("evals", async () => {
  const [esAll, runsAll, tsAll] = await Promise.all([
    get("/api/evals"), get("/api/runs"), get("/api/truth")]);
  // 评估自身只存 dataset，按其中的项目前缀收口；真值任务同理
  const es = { items: (esAll.items || []).filter(inProject) };
  const runs = { items: projectRuns(runsAll.items) };
  const ts = { items: (tsAll.items || []).filter(inProject) };
  const doneRuns = runs.items.filter(r => r.status === "done" || r.done > 0);
  const preselectTask = (state._evalPreselect || {}).task || "";
  state._evalPreselect = null;
  $("#app").innerHTML = `
  <div class="page-title">效果评估与提示词对比</div>
  ${projectScopeBar("只列出当前项目的运行、真值任务与评估记录。")}
  <div class="card">
    <h3>新建评估（运行结果 × 真值任务）</h3>
    <div class="row">
      <div class="u-f2"><label class="f">选择运行（自动带入提示词版本）</label>
        <select id="v-run">${doneRuns.map(r =>
          `<option value="${r.id}">${esc(r.id)}</option>`).join("")}</select></div>
      <div><label class="f">真值任务</label><select id="v-task">${ts.items.map(t =>
        `<option value="${t.id}" ${t.id === preselectTask ? "selected" : ""}>${esc(t.name)}（${t.kind === "single" ? "单分类" : "多标签"}）</option>`).join("")}</select></div>
      <div><label class="f">对比字段（单分类用，默认 overall_status）</label>
        <input type="text" id="v-field" placeholder="overall_status"></div>
      <div><label class="f">集合字段（多标签用，默认 objects[].name）</label>
        <input type="text" id="v-setfield" placeholder="objects[].name"></div>
      <div class="u-f0"><button class="btn primary" id="v-create">运行评估</button></div>
    </div>
    <div class="muted">自定义输出格式时，可填 custom.xxx 路径（如 custom.缺陷列表[].类型）。多标签任务按预测集合与真值标签集合对比。多次复现自动多数投票。</div>
  </div>
  <div class="card">
    <div class="row u-ai-c">
      <h3 class="u-f2 u-m0">评估记录</h3>
      <div class="u-f0"><button class="btn" id="v-compare">对比选中记录</button></div>
    </div>
    <div class="tbl-scroll"><table class="tbl u-mt-10"><thead><tr>
      <th></th><th>评估</th><th>提示词</th><th>模型</th><th>真值任务</th><th>核心指标</th><th>时间</th><th></th>
    </tr></thead><tbody>
    ${es.items.map(e => {
      const m = e.kind === "single"
        ? `准确率 ${(e.metrics.accuracy * 100).toFixed(1)}%`
        : `完全匹配 ${(e.metrics.exact_match * 100).toFixed(1)}% · 微F1 ${(e.metrics.micro.f1 * 100).toFixed(1)}%`;
      return `<tr>
      <td><input type="checkbox" class="v-chk" value="${e.id}"></td>
      <td><a href="#" data-view="${e.id}" class="link">${esc(e.name)}</a><br>
        <span class="muted mono u-fs-xs">${esc(e.run_id)}</span></td>
      <td>${esc(e.prompt_name)} <span class="tag blue">V${e.prompt_version}</span></td>
      <td class="muted">${esc(e.model)}</td>
      <td class="muted">${esc(e.truth_task)}</td>
      <td>${m}</td>
      <td class="muted">${esc(e.created)}</td>
      <td><button class="btn small danger" data-del="${e.id}">删除</button></td></tr>`;
    }).join("") || `<tr><td colspan="8">${emptyState("还没有评估记录", "去运行测试", "#/runs")}</td></tr>`}
    </tbody></table></div>
  </div>
  <div id="v-out"></div>`;

  $("#v-create").onclick = async () => {
    try {
      const r = await post("/api/evals", {
        run_id: $("#v-run").value, truth_task: $("#v-task").value,
        field: $("#v-field").value.trim() || null,
        set_field: $("#v-setfield").value.trim() || null,
      });
      toast("评估完成"); showEvalDetail(r.id);
    } catch (e) { toast(e.message, false); }
  };
  $$("[data-del]").forEach(b => b.onclick = async () => {
    if (!(await confirmDlg("确定删除该评估记录？", { title: "删除评估记录" }))) return;
    await del(`/api/evals/${b.dataset.del}`); navigate();
  });
  $$("[data-view]").forEach(a => a.onclick = () => showEvalDetail(a.dataset.view));
  $("#v-compare").onclick = async () => {
    const ids = $$(".v-chk").filter(c => c.checked).map(c => c.value);
    if (ids.length < 2) return toast("请至少勾选两条记录", false);
    try {
      const d = await get(`/api/evals/compare?ids=${ids.join(",")}`);
      renderCompare(d.items);
    } catch (e) { toast(e.message, false); }
  };
});

async function showEvalDetail(evalId) {
  const e = await get(`/api/evals/${evalId}`);
  const box = $("#v-out");
  let metricHtml = "";
  if (e.kind === "single") {
    const m = e.metrics;
    metricHtml = `
    <div class="grid grid-4">
      <div class="kpi"><div class="v">${(m.accuracy * 100).toFixed(1)}%</div><div class="k">准确率</div></div>
      ${Object.entries(m.per_class).map(([l, p]) =>
        `<div class="kpi"><div class="v">${(p.f1 * 100).toFixed(1)}%</div><div class="k">${esc(l)} F1（P ${(p.precision * 100).toFixed(0)}% / R ${(p.recall * 100).toFixed(0)}%）</div></div>`).join("")}
    </div>
    <h3 class="section-gap">混淆矩阵（行=真值，列=预测）</h3>
    <div class="tbl-scroll"><table class="tbl"><thead><tr><th></th>${Object.keys(m.confusion_matrix[Object.keys(m.confusion_matrix)[0]] || {}).map(c =>
      `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${Object.entries(m.confusion_matrix).map(([t, row]) =>
      `<tr><th>${esc(t)}</th>${Object.values(row).map(v => `<td>${v || ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  } else {
    const m = e.metrics;
    metricHtml = `
    <div class="grid grid-4">
      <div class="kpi"><div class="v">${(m.exact_match * 100).toFixed(1)}%</div><div class="k">完全匹配率</div></div>
      <div class="kpi"><div class="v">${(m.micro.precision * 100).toFixed(1)}%</div><div class="k">微平均精确率</div></div>
      <div class="kpi"><div class="v">${(m.micro.recall * 100).toFixed(1)}%</div><div class="k">微平均召回率</div></div>
      <div class="kpi"><div class="v">${(m.micro.f1 * 100).toFixed(1)}%</div><div class="k">微平均 F1</div></div>
    </div>
    <h3 class="section-gap">按标签统计</h3>
    <div class="tbl-scroll"><table class="tbl"><thead><tr><th>标签</th><th>P</th><th>R</th><th>F1</th><th>TP/FP/FN</th><th>真值数</th></tr></thead>
    <tbody>${Object.entries(m.per_label).map(([l, p]) =>
      `<tr><td>${esc(l)}</td><td>${(p.precision * 100).toFixed(1)}%</td><td>${(p.recall * 100).toFixed(1)}%</td>
      <td>${(p.f1 * 100).toFixed(1)}%</td><td>${p.tp}/${p.fp}/${p.fn}</td>
      <td>${m.support[l] || 0}</td></tr>`).join("")}</tbody></table></div>`;
  }
  const wrong = e.details.filter(d => !d.correct);
  box.innerHTML = `
  <div class="card">
    <h3>${esc(e.name)} <span class="muted">${esc(e.prompt_name)} V${e.prompt_version} · ${esc(e.model)} · ${e.image_count} 张</span></h3>
    ${metricHtml}
    <h3 class="section-gap">错误明细（${wrong.length} 条）</h3>
    <div class="tbl-scroll"><table class="tbl"><thead><tr><th>图片</th><th>真值</th><th>预测</th></tr></thead>
    <tbody>${wrong.slice(0, 100).map(d => `<tr>
      <td class="mono u-fs-xs">${esc(d.image)}</td>
      <td>${(d.truth || []).map(x => `<span class="tag green">${esc(x)}</span>`).join("")}</td>
      <td>${(Array.isArray(d.pred) ? d.pred : [d.pred]).filter(Boolean).map(x => `<span class="tag red">${esc(x)}</span>`).join("") || '<span class="tag">无</span>'}</td>
    </tr>`).join("") || `<tr><td colspan="3" class="muted">全部正确</td></tr>`}</tbody></table></div>
  </div>`;
  box.scrollIntoView({ behavior: "smooth" });
}

function renderCompare(items) {
  const box = $("#v-out");
  const single = items[0].kind === "single";
  // 收集所有类别
  const cats = new Set();
  items.forEach(it => {
    const src = single ? it.metrics.per_class : it.metrics.per_label;
    Object.keys(src || {}).forEach(k => cats.add(k));
  });
  const catArr = [...cats];
  box.innerHTML = `
  <div class="card">
    <h3>评估横评（${items.length} 条）</h3>
    <div class="tbl-scroll"><table class="tbl"><thead><tr>
      <th>指标</th>${items.map(it => `<th>${esc(it.prompt)}<br><span class="muted">${esc(it.name)}</span></th>`).join("")}
    </tr></thead><tbody>
      <tr><td>${single ? "准确率" : "完全匹配率"}</td>${items.map(it =>
        `<td>${((single ? it.metrics.accuracy : it.metrics.exact_match) * 100).toFixed(1)}%</td>`).join("")}</tr>
      ${!single ? `<tr><td>微平均 F1</td>${items.map(it => `<td>${(it.metrics.micro.f1 * 100).toFixed(1)}%</td>`).join("")}</tr>` : ""}
      ${catArr.map(c => `<tr><td>${esc(c)} F1</td>${items.map(it => {
        const src = single ? it.metrics.per_class : it.metrics.per_label;
        const p = (src || {})[c];
        return `<td>${p ? (p.f1 * 100).toFixed(1) + "%" : "-"}</td>`;
      }).join("")}</tr>`).join("")}
      <tr><td>样本数</td>${items.map(it => `<td>${it.image_count}</td>`).join("")}</tr>
    </tbody></table></div>
  </div>`;
  box.scrollIntoView({ behavior: "smooth" });
}

// ---------------------------------------------------------------- 启动

// ---------------------------------------------------------------- JSON 工具（格式化 / 校验 / 树形查看）
route("jsontool", () => {
  const sample = JSON.stringify({
    overall_status: "abnormal",
    summary: "画面中发现 1 处异常目标",
    classification: { label: "施工场景", confidence: 0.92 },
    objects: [
      { label: "挖掘机", category: "工程机械", confidence: 0.95,
        bbox: [120, 80, 340, 260], value: "1台", description: "正在作业", evidence: "位于画面中央" },
    ],
    scene: "白天，室外工地",
  }, null, 2);
  $("#app").innerHTML = `
  <div class="page-title">JSON 工具</div>
  <div class="grid u-gtc-2 u-ai-start">
    <div class="card">
      <div class="row u-mb-8">
        <button class="btn primary" id="jt-fmt">格式化</button>
        <button class="btn" id="jt-min">压缩</button>
        <button class="btn" id="jt-check">校验</button>
        <button class="btn" id="jt-copy">复制</button>
        <button class="btn" id="jt-sample">示例</button>
        <button class="btn" id="jt-clear">清空</button>
      </div>
      <textarea id="jt-in" rows="22" placeholder="粘贴 JSON 到这里…" spellcheck="false"></textarea>
      <div class="u-mt-8" id="jt-msg"></div>
    </div>
    <div class="card">
      <div class="row u-ai-c u-mb-8">
        <h3 class="u-f1 u-m0">结构预览</h3>
        <span class="muted" id="jt-stats"></span>
      </div>
      <div id="jt-out" class="json-view u-minh-200"><span class="muted">左侧输入合法 JSON 后自动展示树形结构</span></div>
    </div>
  </div>`;
  const inp = $("#jt-in"), out = $("#jt-out"), msg = $("#jt-msg"), stats = $("#jt-stats");

  const showErr = (r) => {
    msg.innerHTML = `<div class="msg err u-m0">格式错误${r.line ? `：第 ${r.line} 行第 ${r.col} 列` : ""}（${esc(r.message)}）</div>`;
  };
  const renderTree = () => {
    const text = inp.value.trim();
    if (!text) { out.innerHTML = '<span class="muted">左侧输入合法 JSON 后自动展示树形结构</span>'; stats.textContent = ""; msg.innerHTML = ""; return; }
    const r = parseJsonEx(text);
    if (!r.ok) { showErr(r); stats.textContent = ""; return; }
    msg.innerHTML = "";
    let keys = 0, depth = 0;
    const walk = (v, d) => {
      depth = Math.max(depth, d);
      if (v && typeof v === "object") Object.values(v).forEach(x => { keys++; walk(x, d + 1); });
    };
    walk(r.data, 1);
    stats.textContent = `${text.length} 字符 · ${keys} 个字段 · ${depth} 层`;
    out.innerHTML = jsonTreeHtml(r.data);
  };
  let deb = null;
  inp.oninput = () => { clearTimeout(deb); deb = setTimeout(renderTree, 300); };
  $("#jt-fmt").onclick = () => {
    const r = parseJsonEx(inp.value.trim());
    if (!r.ok) return showErr(r);
    inp.value = JSON.stringify(r.data, null, 2);
    renderTree();
    toast("已格式化");
  };
  $("#jt-min").onclick = () => {
    const r = parseJsonEx(inp.value.trim());
    if (!r.ok) return showErr(r);
    inp.value = JSON.stringify(r.data);
    renderTree();
    toast("已压缩");
  };
  $("#jt-check").onclick = () => {
    const r = parseJsonEx(inp.value.trim());
    if (!r.ok) return showErr(r);
    msg.innerHTML = `<div class="msg ok u-m0">JSON 格式正确</div>`;
    renderTree();
  };
  $("#jt-copy").onclick = async () => {
    try { await navigator.clipboard.writeText(inp.value); toast("已复制"); }
    catch (e) { toast("复制失败，请手动选择复制", false); }
  };
  $("#jt-sample").onclick = () => { inp.value = sample; renderTree(); };
  $("#jt-clear").onclick = () => { inp.value = ""; renderTree(); inp.focus(); };
});

navigate();
