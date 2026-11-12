# -*- coding: utf-8 -*-
"""
T-003 epub 端到端冒烟测试（Developer 自验 + Tester 独立复验可复用）：
  1. 合法 epub 上传 → 期待 code 00000 + chapterCount=3
  2. 缺 container.xml 的 epub → 期待 A0704
  3. 伪 zip epub → 期待 A0704
  4. 读取详情/章节列表/正文，验证：纯文本无 HTML 残留、章节顺序与 spine 一致、wordCount/lastChapter* 已更新
用法: python epub-smoke-test.py [--mode upload|read]
"""
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8888/api"
SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
BOOK_NAME = "冒烟测试 epub 电子书"

def upload(filepath, book_name):
    boundary = "----sdd-test-boundary-7c3b1e21"
    line = []
    def field(name, value):
        # 每个 part 以 --boundary CRLF 起行
        line.append(("--" + boundary + "\r\n").encode())
        line.append(('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode())
        line.append((str(value) + "\r\n").encode())
    field("bookName", book_name)
    field("authorName", "冒烟测试")
    field("workDirection", "0")
    field("categoryId", "3")
    field("categoryName", "武侠")
    line.append(("--" + boundary + "\r\n").encode())
    line.append(('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % os.path.basename(filepath)).encode())
    line.append(b"Content-Type: application/octet-stream\r\n\r\n")
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    line.append(file_bytes)
    line.append(("\r\n--" + boundary + "--\r\n").encode())
    body = b"".join(line)
    req = urllib.request.Request(
        BASE + "/front/resource/book/upload",
        data=body,
        headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "upload"

    if mode == "upload":
        # ---------- 1. 合法 epub ----------
        valid = os.path.join(SAMPLES, "valid-book.epub")
        status, data = upload(valid, BOOK_NAME)
        print("[1] valid epub upload -> HTTP %d" % status)
        print("    code=%s message=%s" % (data.get("code"), data.get("message")))
        print("    data=%s" % json.dumps(data.get("data"), ensure_ascii=False))
        # ---------- 2. 缺 container.xml ----------
        status, data = upload(os.path.join(SAMPLES, "corrupt-nocontainer.epub"), "损坏1")
        print("[2] corrupt no-container upload -> HTTP %d code=%s message=%s" % (status, data.get("code"), data.get("message")))
        # ---------- 3. 伪 zip ----------
        status, data = upload(os.path.join(SAMPLES, "corrupt-notzip.epub"), "损坏2")
        print("[3] corrupt notzip upload -> HTTP %d code=%s message=%s" % (status, data.get("code"), data.get("message")))

    elif mode == "read":
        # 上传成功后读回验证（需要先跑 upload 模式拿到 bookId）
        book_id = sys.argv[2]
        st, d = get("/front/book/%s" % book_id)
        book = (d.get("data") or {})
        print("[detail] id=%s name=%s wordCount=%s lastChapter=%s" % (
            book.get("id"), book.get("bookName"), book.get("wordCount"), book.get("lastChapterName")))
        st, d = get("/front/book/chapter/list?bookId=%s" % book_id)
        items = (d.get("data") or [])
        print("[chapters] count=%d" % len(items))
        for it in items:
            cid = it.get("id")
            st, c = get("/front/book/content/%s" % cid)
            content = (c.get("data") or {}).get("bookContent") or ""
            # 检查 HTML 残留
            has_html = any(tag in content.lower() for tag in ["<p>", "</p>", "<div>", "<span>", "class=", "<em>", "<b>", "<i>"])
            print("   #%-3s %-14s len=%-5d html_residual=%s" % (
                it.get("chapterNum"), it.get("chapterName")[:14], len(content), has_html))

if __name__ == "__main__":
    main()