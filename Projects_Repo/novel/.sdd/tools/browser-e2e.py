# -*- coding: utf-8 -*-
"""T-004 浏览器端到端验证：上传页真实交互 → 成功 → 状态恢复 → 搜索 → 详情 → 阅读。"""
import sys, time
from playwright.sync_api import sync_playwright

STAMP = time.strftime("%H%M%S")
BOOK_TXT = "浏览器e2e_txt_%s" % STAMP
AUTHOR = "T004浏览器回归"
TXT_PATH = r"E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\novel\.sdd\tools\samples\valid-book.txt"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        req_log = []
        page.on('request', lambda r: req_log.append(r.url) if 'upload' in r.url.lower() else None)

        # ---- 上传页 ----
        page.goto("http://localhost:1024/#/book_upload", timeout=40000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3500)  # 等 listCategorys 完成，分类自动选中
        print("[1] 分类已自动选中:", page.locator('.el-select').first.inner_text().strip() or "(无)")
        print("[2a] 上传前按钮 loading(expect False):",
              "is-loading" in (page.get_by_role("button", name="上传").first.get_attribute("class") or ""))

        # 选择文件 + 填表单（分类已自动选中，不再操作下拉）
        page.locator('input[type="file"]').first.set_input_files(TXT_PATH)
        page.wait_for_timeout(500)
        page.get_by_placeholder("请输入书名").fill(BOOK_TXT)
        page.get_by_placeholder("作者名（选填）").fill(AUTHOR)
        page.get_by_placeholder("书籍简介（选填）").fill("浏览器驱动上传 T-004 E2E")
        page.wait_for_timeout(800)

        upload_btn = page.get_by_role("button", name="上传").first
        # 点击上传
        upload_btn.click()
        page.wait_for_timeout(1500)  # 上传请求进行中
        # 上传中加载态
        try:
            loading_cls = upload_btn.get_attribute("class") or ""
            print("[3] 上传中按钮 is-loading:", "is-loading" in loading_cls)
        except Exception as e:
            print("[3] 上传中读取失败:", e)

        # 等成功结果
        page.wait_for_selector(".el-result", timeout=30000)
        page.wait_for_timeout(1000)
        result_text = page.locator(".el-result").first.text_content() or ""
        print("[4] 上传结果区:", result_text.strip())
        print("[5] 命中的上传请求:", [u for u in req_log if 'upload' in u.lower()][:3])
        print("[6] 上传完成按钮 loading(expect False):",
              "is-loading" in (upload_btn.get_attribute("class") or ""))

        # 立即阅读按钮
        read_btn = page.get_by_role("button", name="立即阅读")
        if read_btn.count():
            print("[6b] 出现「立即阅读」按钮:", True)

        # ---- 搜索验证 ----
        page.goto("http://localhost:1024/#/bookclass?key=%s" % BOOK_TXT, timeout=30000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2500)
        body = page.inner_text("body")
        print("[7] 搜索页命中书名:", BOOK_TXT in body, "| 出现'第三章 旧事':", "第三章 旧事" in body)

        # ---- 点击书名进入详情 ----
        page.locator("text=%s" % BOOK_TXT).first.click(timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2500)
        print("[8] 详情页 url:", page.url)
        body2 = page.inner_text("body")
        print("[9] 详情页含 作者/总字数/点击阅读:",
              all(x in body2 for x in [AUTHOR, "总字数", "点击阅读"]))

        # ---- 点击阅读 ----
        page.get_by_text("点击阅读").first.click(timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2500)
        print("[10] 阅读页 url:", page.url)
        body3 = page.inner_text("body")
        rendered = ("山雨欲来" in body3 and "沈砚" in body3 and "下一章" in body3 and "目录" in body3)
        print("[11] 阅读页正文渲染(第一章内容/翻页):", rendered)
        page.screenshot(path=r"E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\novel\.sdd\tmp\e2e_read.png")

        # ---- 上一章/下一章按钮交互（next 到第二章）----
        page.get_by_text("下一章").last.click(timeout=10000)
        page.wait_for_timeout(2000)
        body4 = page.inner_text("body")
        print("[12] 阅读页「下一章」跳转后含'第二章 剑鸣':", "第二章 剑鸣" in body4 and "剑鸣" in body4)

        print("[13] 页面 JS 错误:", errors if errors else "None")
        browser.close()

if __name__ == "__main__":
    sys.exit(main())