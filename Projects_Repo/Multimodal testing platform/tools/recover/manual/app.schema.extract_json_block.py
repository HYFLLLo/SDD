_MISSING = object()


def _loads_any(text):
    """json.loads 的安全包装：失败返回 _MISSING 哨兵，便于区分 None/null。"""
    try:
        return json.loads(text)
    except Exception:
        return _MISSING


def _loads_object(text):
    """能解析成 JSON 对象就返回对象，否则 None。"""
    data = _loads_any(text)
    return data if isinstance(data, dict) else None


def _manual_unescape(text):
    """整体被引号包裹、转义又不完整的载荷 → 还原成 JSON 文本。

    真实坏样本：模型输出 "{\"a\": 1}"，但结尾内部引号漏了反斜杠，
    json.loads 直接失败。这里只解反斜杠转义的双引号、反斜杠与斜杠三种，避免破坏 JSON 语义。
    """
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt in ('"', "\\", "/"):
                out.append(nxt)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _unwrap_string_payload(value, depth=3):
    """模型偶尔把整个 JSON 再序列化成字符串（外层多一层引号 + 转义）。

    逐层解包，最多 depth 层，避免异常数据无限递归。转义残缺时退化为手动
    反转义，再交给 JSON 解析器判断。
    """
    for _ in range(depth):
        if not isinstance(value, str):
            break
        stripped = value.strip()
        if not stripped or stripped[0] not in "{\"":
            break
        inner = _loads_any(stripped)
        if inner is _MISSING:
            if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
                repaired = _manual_unescape(stripped[1:-1])
                if _loads_any(repaired) is not _MISSING:
                    value = repaired
                    continue
            break
        if isinstance(inner, str) and inner.strip() == stripped:
            break
        if not isinstance(inner, (dict, str)):
            break
        value = inner
    return value


_BRACKET_PAIRS = {"}": "{", "]": "["}


def _drop_stray_closers(text):
    """扫描并删除「栈里没有对应开括号」或「类型不匹配」的右括号。

    模型常见坏样本：bbox 写成 [213,341,232,386]]，多一个 ]。这里按括号栈
    定位真正多余的字符，避免按总数误删到列表内部的合法括号。
    """
    stack = []
    stray = []
    in_string = False
    escaped = False
    for index, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack and stack[-1] == _BRACKET_PAIRS[ch]:
                stack.pop()
            else:
                stray.append(index)
    if not stray:
        return text, stack
    drop = set(stray)
    return "".join(ch for i, ch in enumerate(text) if i not in drop), stack


def _repair_trailing_closers(text):
    """修正括号问题：先删多余右括号，再补齐缺失的右括号。

    每一步都用 json.loads 验证，命中即返回；全部失败时返回最接近的候选，
    由调用方决定是否放弃解析。
    """
    cleaned, stack = _drop_stray_closers(text)
    candidates = [cleaned]
    if stack:
        candidates.append(cleaned + "".join("}" if c == "{" else "]" for c in reversed(stack)))
    for candidate in candidates:
        if _loads_object(candidate) is not None:
            return candidate
    return cleaned


def extract_json_block(text):
    """从模型输出中提取 JSON 文本（剥离代码块围栏，截取首个完整对象）"""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    if not t:
        return None
    if _loads_object(t) is not None:
        return t
    # 整体是被序列化的字符串（二次编码）：解包后重新判断
    unwrapped = _unwrap_string_payload(t)
    if isinstance(unwrapped, dict):
        return json.dumps(unwrapped, ensure_ascii=False)
    if isinstance(unwrapped, str) and _loads_object(unwrapped.strip()) is not None:
        return unwrapped.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end > start:
        candidate = t[start:end + 1]
        if _loads_object(candidate) is not None:
            return candidate
        inner = _unwrap_string_payload(candidate)
        if isinstance(inner, dict):
            return json.dumps(inner, ensure_ascii=False)
        fixed = _repair_trailing_closers(candidate)
        if _loads_object(fixed) is not None:
            return fixed
        return candidate
    return None
