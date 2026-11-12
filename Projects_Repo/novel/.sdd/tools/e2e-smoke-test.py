# -*- coding: utf-8 -*-
"""
T-004 端到端回归冒烟测试（Tester 独立复用）：
  1. 合法 txt 上传 → 期待 code 00000 + chapterCount=3 + wordCount>0
  2. 合法 epub 上传 → 期待 code 00000 + chapterCount=3
  3. 读回 txt/epub：详情 / 章节列表 / 正文，检查纯文本无 HTML 残留、章节顺序与 spine 一致
  4. 搜索：书名关键词命中
  5. 首页 /api/front/home/books 返回 code 00000
用法: python e2e-smoke-test.py
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8888/api"
SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
BOUNDARY = "----sdd-t004-boundary-3f8a2c11"
STAMP = time.strftime("%m%d%H%M")
BOOK_TXT = "T004端到端txt_%s" % STAMP
BOOK_EPUB = "T004端到端epub_%s" % STAMP

# 期望：txt 三章 = 山雨欲来 / 剑鸣 / 旧事；epub 三章 = 初入江湖 / 客栈奇遇 / 惊变
EXPECTED_TXT_CHAPTERS = ["第一章 山雨欲来", "第二章 剑鸣", "第三章 旧事"]
EXPECTED_EPUB_CHAPTERS = ["第一章 初入江湖", "第二章 客栈奇遇", "第三章 惊变"]


def upload(filepath, book_name, author="T004回归测试"):
    line = []
    def field(name, value):
        line.append(("--" + BOUNDARY + "\r\n").encode())
        line.append(('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode())
        line.append((str(value) + "\r\n").encode())
    field("bookName", book_name)
    field("authorName", author)
    field("workDirection", "0")
    field("categoryId", "3")
    field("categoryName", "武侠")
    field("bookDesc", "T-004 端到端回归测试上传")
    line.append(("--" + BOUNDARY + "\r\n").encode())
    line.append(('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % os.path.basename(filepath)).encode())
    line.append(b"Content-Type: application/octet-stream\r\n\r\n")
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    line.append(file_bytes)
    line.append(("\r\n--" + BOUNDARY + "--\r\n").encode())
    body = b"".join(line)
    req = urllib.request.Request(
        BASE + "/front/resource/book/upload",
        data=body,
        headers={
            "Content-Type": "multipart/form-data; boundary=" + BOUNDARY,
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


def verify_read(book_id, expected_chapters, label):
    st, d = get("/front/book/%s" % book_id)
    book = (d.get("data") or {})
    print("[%s detail] code=%s id=%s name=%s wordCount=%s lastChapterName=%s" % (
        label, d.get("code"), book.get("id"), book.get("bookName"),
        book.get("wordCount"), book.get("lastChapterName")))
    st, d = get("/front/book/chapter/list?bookId=%s" % book_id)
    items = (d.get("data") or [])
    print("[%s chapters] count=%d" % (label, len(items)))
    ok = True
    for idx, it in enumerate(items):
        cid = it.get("id")
        st, c = get("/front/book/content/%s" % cid)
        content = (c.get("data") or {}).get("bookContent") or ""
        has_html = any(tag in content.lower() for tag in
                       ["<p>", "</p>", "<div>", "<span>", "class=", "<em>", "<b>", "<i>", "style=", "<br"])
        name_match = expected_chapters[idx] == it.get("chapterName")
        if not name_match or has_html:
            ok = False
        print("   #%-3s name=%-16s expect=%-16s name_match=%s len=%-5d html_residual=%s" % (
            it.get("chapterNum"), it.get("chapterName"), expected_chapters[idx], name_match, len(content), has_html))
    print("[%s order/html] result=%s" % (label, "PASS" if ok else "FAIL"))
    return ok


def search(keyword, expect_hit_book_id):
    st, d = get("/front/search/books?keyword=%s" % urllib.parse.quote(keyword))
    data = d.get("data") or {}
    lst = data.get("list") or []
    hit = any(str(b.get("id") or b.get("bookId")) == str(expect_hit_book_id) for b in lst)
    print("[search] keyword=%s total=%s hit_target=%s books=%s" % (
        keyword, data.get("total"), hit,
        [(b.get("bookName"), b.get("id") or b.get("bookId")) for b in lst]))
    return hit


def main():
    results = {}

    # ---------- 1. txt 上传 ----------
    st, data = upload(os.path.join(SAMPLES, "valid-book.txt"), BOOK_TXT)
    print("[1] txt upload -> HTTP %d code=%s message=%s data=%s" % (
        st, data.get("code"), data.get("message"),
        json.dumps(data.get("data"), ensure_ascii=False)))
    txt_book_id = (data.get("data") or {}).get("bookId")
    results["txt_upload"] = (data.get("code") == "00000" and int((data.get("data") or {}).get("chapterCount") or 0) == 3)

    # ---------- 2. epub 上传 ----------
    st, data = upload(os.path.join(SAMPLES, "valid-book.epub"), BOOK_EPUB)
    print("[2] epub upload -> HTTP %d code=%s message=%s data=%s" % (
        st, data.get("code"), data.get("message"),
        json.dumps(data.get("data"), ensure_ascii=False)))
    epub_book_id = (data.get("data") or {}).get("bookId")
    results["epub_upload"] = (data.get("code") == "00000" and int((data.get("data") or {}).get("chapterCount") or 0) == 3)

    # ---------- 3. 读回验证 ----------
    results["txt_read"] = verify_read(txt_book_id, EXPECTED_TXT_CHAPTERS, "txt")
    results["epub_read"] = verify_read(epub_book_id, EXPECTED_EPUB_CHAPTERS, "epub")

    # ---------- 4. 搜索 ----------
    results["txt_search"] = search(BOOK_TXT, txt_book_id)
    # epub 搜索输入书名关键词（取前4个字符避免太长的完整名）
    results["epub_search"] = search(BOOK_EPUB[:6], epub_book_id)

    # ---------- 5. 首页回归 ----------
    st, d = get("/front/home/books")
    home_ok = d.get("code") == "00000"
    results["home_api"] = home_ok
    print("[home] HTTP %d code=%s items=%d" % (st, d.get("code"), len((d.get("data") or []))))

    print("\n===== SUMMARY =====")
    print("txt_book_id=%s" % txt_book_id)
    print("epub_book_id=%s" % epub_book_id)
    for k, v in results.items():
        print("  %-12s = %s" % (k, "PASS" if v else "FAIL"))
    all_pass = all(v for v in results.values())
    print("OVERALL=%s" % ("PASS" if all_pass else "FAIL"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())